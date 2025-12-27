"""
WebSocket Routes for Real-time KOT System
Handles WebSocket connections, events, and real-time order management
"""

from flask import Blueprint, request, session, jsonify, current_app
from flask_login import login_required, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms, disconnect
from models import db, Order, OrderItem, KitchenDisplay, KOTEvent, OrderStatusHistory, RealTimeMetrics
from models.realtime_kot import enhance_order_model
from utils.analytics_pipeline import analytics_pipeline
from datetime import datetime, timedelta
import json
import uuid
import time

# Initialize SocketIO
socketio = SocketIO()

# WebSocket Blueprint
websocket_bp = Blueprint('websocket', __name__)

# Global connection tracking
connected_displays = {}  # session_id -> display_info
active_connections = {}  # socket_id -> session_id
order_subscribers = {}  # order_id -> set of socket_ids
kitchen_rooms = ['kitchen_general', 'kitchen_grill', 'kitchen_fry', 'kitchen_salad', 'kitchen_dessert']

def authenticate_socket_connection():
    """Authenticate WebSocket connection"""
    try:
        # Get authentication token from request
        auth_token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not auth_token:
            return False, {'error': 'No authentication token provided'}
        
        # Validate token (implement your token validation logic here)
        # For now, we'll use session-based authentication
        if not current_user.is_authenticated:
            return False, {'error': 'User not authenticated'}
        
        return True, {'user_id': current_user.id, 'role': current_user.role}
        
    except Exception as e:
        return False, {'error': f'Authentication failed: {str(e)}'}

def validate_kitchen_access(user_role, station_type=None):
    """Validate user access to kitchen functionality"""
    allowed_roles = ['admin', 'manager', 'kitchen_staff', 'chef', 'head_chef']
    
    if user_role not in allowed_roles:
        return False, {'error': 'Insufficient permissions for kitchen access'}
    
    # Additional validation for specific stations
    if station_type and user_role == 'kitchen_staff':
        # Kitchen staff might have station-specific access
        pass
    
    return True, {'message': 'Access granted'}

def broadcast_order_event(event_type, order_data, target_rooms=None):
    """Broadcast order-related events to connected displays"""
    try:
        # Default target rooms
        if not target_rooms:
            target_rooms = ['kitchen_general'] + kitchen_rooms
        
        # Prepare event payload
        event_payload = {
            'type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': order_data
        }
        
        # Broadcast to all relevant rooms
        for room in target_rooms:
            socketio.emit('order_event', event_payload, room=room)
        
        # Broadcast to individual order subscribers
        if order_data.get('order_id'):
            order_id = str(order_data['order_id'])
            if order_id in order_subscribers:
                for socket_id in order_subscribers[order_id]:
                    socketio.emit('order_event', event_payload, room=socket_id)
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to broadcast order event: {str(e)}")
        return False

def broadcast_analytics_update(data):
    """Broadcast analytics updates to connected clients"""
    try:
        # Get real-time analytics data
        realtime_data = analytics_pipeline.get_real_time_dashboard_data()
        
        # Merge with real-time metrics
        analytics_data = {
            **realtime_data,
            **data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Broadcast to all connected clients
        socketio.emit('analytics_update', analytics_data)
        
        # Also broadcast to analytics dashboard room if it exists
        socketio.emit('analytics_update', analytics_data, room='analytics_dashboard')
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to broadcast analytics update: {str(e)}")
        return False

def calculate_order_priority(order):
    """Calculate order priority score for real-time display"""
    try:
        score = 0
        factors = []
        
        # Time-based priority
        age_minutes = (datetime.utcnow() - order.created_at).total_seconds() / 60
        if age_minutes > 30:
            score += 50
            factors.append('urgent_age')
        elif age_minutes > 15:
            score += 25
            factors.append('medium_age')
        elif age_minutes > 5:
            score += 10
            factors.append('normal_age')
        
        # Order type priority
        if order.order_type == 'Dine-in':
            score += 20
            factors.append('dine_in')
        elif order.order_type == 'Delivery':
            score += 15
            factors.append('delivery')
        
        # Status-based priority
        if order.status == 'New':
            score += 30
            factors.append('new_order')
        elif order.status == 'In Progress':
            score += 20
            factors.append('in_progress')
        
        # Table-based priority
        if order.table_id:
            score += 15
            factors.append('table_order')
        
        return {
            'score': score,
            'factors': factors,
            'age_minutes': int(age_minutes),
            'level': 'critical' if score >= 60 else 'high' if score >= 40 else 'medium' if score >= 20 else 'normal'
        }
        
    except Exception as e:
        current_app.logger.error(f"Failed to calculate order priority: {str(e)}")
        return {'score': 0, 'factors': [], 'age_minutes': 0, 'level': 'normal'}

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    try:
        # Authenticate connection
        auth_success, auth_data = authenticate_socket_connection()
        if not auth_success:
            emit('error', {'message': auth_data['error']})
            disconnect()
            return
        
        user_id = auth_data['user_id']
        user_role = auth_data['role']
        
        # Get display configuration from request
        display_name = request.args.get('display_name', f'Kitchen Display {user_id}')
        station_type = request.args.get('station_type', 'general')
        kitchen_role = request.args.get('kitchen_role', user_role)
        
        # Validate kitchen access
        access_valid, access_data = validate_kitchen_access(user_role, station_type)
        if not access_valid:
            emit('error', {'message': access_data['error']})
            disconnect()
            return
        
        # Create or get kitchen display session
        session_id = str(uuid.uuid4())
        display = KitchenDisplay(
            session_id=session_id,
            display_name=display_name,
            station_type=station_type,
            kitchen_role=kitchen_role,
            created_by=user_id
        )
        
        # Connect display
        display.connect(request.sid)
        
        # Track connection
        connected_displays[session_id] = {
            'display': display,
            'user_id': user_id,
            'user_role': user_role,
            'socket_id': request.sid,
            'connected_at': datetime.utcnow()
        }
        active_connections[request.sid] = session_id
        
        # Join appropriate rooms
        room_name = f'kitchen_{station_type}'
        join_room(room_name)
        join_room('kitchen_general')  # Always join general kitchen room
        
        # Send connection confirmation
        emit('connected', {
            'session_id': session_id,
            'display_name': display_name,
            'station_type': station_type,
            'kitchen_role': kitchen_role,
            'message': 'Successfully connected to kitchen display system'
        })
        
        # Send current orders if needed
        emit('sync_request', {'message': 'Send current orders for synchronization'})
        
        current_app.logger.info(f"Kitchen display connected: {display_name} ({session_id})")
        
    except Exception as e:
        current_app.logger.error(f"WebSocket connection error: {str(e)}")
        emit('error', {'message': f'Connection failed: {str(e)}'})
        disconnect()

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    try:
        socket_id = request.sid
        if socket_id in active_connections:
            session_id = active_connections[socket_id]
            
            if session_id in connected_displays:
                display_info = connected_displays[session_id]
                display = display_info['display']
                
                # Disconnect display
                display.disconnect()
                
                # Remove from tracking
                del connected_displays[session_id]
                del active_connections[socket_id]
                
                current_app.logger.info(f"Kitchen display disconnected: {display.display_name} ({session_id})")
        
        # Clean up order subscriptions
        for order_id, subscribers in order_subscribers.items():
            if socket_id in subscribers:
                subscribers.remove(socket_id)
                if not subscribers:  # Remove empty subscriptions
                    del order_subscribers[order_id]
    
    except Exception as e:
        current_app.logger.error(f"WebSocket disconnection error: {str(e)}")

@socketio.on('join_order')
def handle_join_order(data):
    """Join order-specific room for real-time updates"""
    try:
        order_id = str(data.get('order_id'))
        if not order_id:
            emit('error', {'message': 'Order ID required'})
            return
        
        # Add to order subscribers
        if order_id not in order_subscribers:
            order_subscribers[order_id] = set()
        order_subscribers[order_id].add(request.sid)
        
        emit('order_joined', {
            'order_id': order_id,
            'message': f'Subscribed to order {order_id} updates'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error joining order: {str(e)}")
        emit('error', {'message': f'Failed to join order: {str(e)}'})

@socketio.on('leave_order')
def handle_leave_order(data):
    """Leave order-specific room"""
    try:
        order_id = str(data.get('order_id'))
        if order_id in order_subscribers and request.sid in order_subscribers[order_id]:
            order_subscribers[order_id].remove(request.sid)
            if not order_subscribers[order_id]:
                del order_subscribers[order_id]
        
        emit('order_left', {
            'order_id': order_id,
            'message': f'Unsubscribed from order {order_id} updates'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error leaving order: {str(e)}")

@socketio.on('heartbeat')
def handle_heartbeat(data):
    """Handle heartbeat for connection health monitoring"""
    try:
        socket_id = request.sid
        if socket_id in active_connections:
            session_id = active_connections[socket_id]
            if session_id in connected_displays:
                display = connected_displays[session_id]['display']
                display.update_heartbeat()
                
                emit('heartbeat_ack', {
                    'timestamp': datetime.utcnow().isoformat(),
                    'server_time': time.time()
                })
        
    except Exception as e:
        current_app.logger.error(f"Error handling heartbeat: {str(e)}")

@socketio.on('request_orders')
def handle_request_orders(data):
    """Handle request for current orders"""
    try:
        # Get filters
        status_filter = data.get('status_filter', 'active')
        station_type = data.get('station_type', 'general')
        urgency_filter = data.get('urgency_filter', 'all')
        
        # Build query
        query = Order.query
        if status_filter == 'active':
            query = query.filter(Order.status.in_(['New', 'In Progress', 'Ready']))
        elif status_filter == 'new':
            query = query.filter_by(status='New')
        elif status_filter == 'progress':
            query = query.filter_by(status='In Progress')
        elif status_filter == 'ready':
            query = query.filter_by(status='Ready')
        
        orders = query.order_by(Order.created_at.asc()).all()
        
        # Enhance orders with real-time data
        enhanced_orders = []
        for order in orders:
            order_dict = order.to_dict()
            
            # Calculate priority
            priority_info = calculate_order_priority(order)
            order_dict['priority'] = priority_info
            
            # Get order items with enhanced data
            items = OrderItem.query.filter_by(order_id=order.id).all()
            order_dict['items'] = [item.to_dict() for item in items]
            
            # Add real-time metadata
            order_dict['subscriber_count'] = len(order_subscribers.get(str(order.id), set()))
            order_dict['last_update'] = datetime.utcnow().isoformat()
            
            enhanced_orders.append(order_dict)
        
        emit('orders_sync', {
            'orders': enhanced_orders,
            'filters': {
                'status_filter': status_filter,
                'station_type': station_type,
                'urgency_filter': urgency_filter
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error sending orders: {str(e)}")
        emit('error', {'message': f'Failed to get orders: {str(e)}'})

@socketio.on('update_order_status')
def handle_update_order_status(data):
    """Handle real-time order status updates"""
    try:
        order_id = data.get('order_id')
        new_status = data.get('status')
        reason = data.get('reason', '')
        
        if not order_id or not new_status:
            emit('error', {'message': 'Order ID and status required'})
            return
        
        # Get user info
        if request.sid not in active_connections:
            emit('error', {'message': 'Invalid session'})
            return
        
        session_id = active_connections[request.sid]
        user_info = connected_displays[session_id]
        user_id = user_info['user_id']
        user_role = user_info['user_role']
        
        # Update order status
        order = Order.query.get(order_id)
        if not order:
            emit('error', {'message': 'Order not found'})
            return
        
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        # Create status history
        history = OrderStatusHistory(
            order_id=order.id,
            previous_status=old_status,
            new_status=new_status,
            changed_by_user_id=user_id,
            changed_by_username=current_user.username if current_user.is_authenticated else 'Unknown',
            changed_by_role=user_role,
            reason=reason
        )
        
        db.session.add(history)
        db.session.commit()
        
        # Broadcast status change
        event_data = {
            'order_id': order.id,
            'order_number': order.order_number,
            'old_status': old_status,
            'new_status': new_status,
            'changed_by': user_id,
            'changed_by_role': user_role,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        broadcast_order_event('order_update', event_data)
        
        # Send success response
        emit('status_updated', {
            'order_id': order_id,
            'new_status': new_status,
            'message': f'Order {order.order_number} status updated to {new_status}'
        })
        
        current_app.logger.info(f"Order {order.order_number} status updated: {old_status} -> {new_status} by user {user_id}")
        
        # Trigger analytics processing for completed orders
        if new_status == 'Completed':
            try:
                analytics_pipeline.process_real_time_order(order.id)
                current_app.logger.info(f"Analytics processed for completed order {order.order_number}")
            except Exception as analytics_error:
                current_app.logger.error(f"Analytics processing failed for order {order.order_number}: {str(analytics_error)}")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating order status: {str(e)}")
        emit('error', {'message': f'Failed to update order status: {str(e)}'})

@socketio.on('update_item_status')
def handle_update_item_status(data):
    """Handle real-time item status updates"""
    try:
        item_id = data.get('item_id')
        new_status = data.get('status')
        
        if not item_id or not new_status:
            emit('error', {'message': 'Item ID and status required'})
            return
        
        # Get user info
        if request.sid not in active_connections:
            emit('error', {'message': 'Invalid session'})
            return
        
        session_id = active_connections[request.sid]
        user_info = connected_displays[session_id]
        user_id = user_info['user_id']
        user_role = user_info['user_role']
        
        # Update item status
        item = OrderItem.query.get(item_id)
        if not item:
            emit('error', {'message': 'Order item not found'})
            return
        
        old_status = item.status
        item.status = new_status
        item.updated_at = datetime.utcnow()
        
        # Create status history
        history = OrderStatusHistory(
            order_id=item.order_id,
            previous_status=old_status,
            new_status=new_status,
            changed_by_user_id=user_id,
            changed_by_username=current_user.username if current_user.is_authenticated else 'Unknown',
            changed_by_role=user_role,
            order_item_id=item.id
        )
        
        db.session.add(history)
        db.session.commit()
        
        # Broadcast item status change
        event_data = {
            'order_id': item.order_id,
            'order_item_id': item.id,
            'item_name': item.item_name,
            'old_status': old_status,
            'new_status': new_status,
            'changed_by': user_id,
            'changed_by_role': user_role,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        broadcast_order_event('item_update', event_data)
        
        # Send success response
        emit('item_updated', {
            'item_id': item_id,
            'order_id': item.order_id,
            'new_status': new_status,
            'message': f'Item {item.item_name} status updated to {new_status}'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating item status: {str(e)}")
        emit('error', {'message': f'Failed to update item status: {str(e)}'})

@socketio.on('kitchen_alert')
def handle_kitchen_alert(data):
    """Handle kitchen alerts and notifications"""
    try:
        alert_type = data.get('type', 'info')  # info, warning, error, urgent
        message = data.get('message')
        order_id = data.get('order_id')
        target_stations = data.get('target_stations', ['general'])
        
        if not message:
            emit('error', {'message': 'Alert message required'})
            return
        
        # Get user info
        if request.sid not in active_connections:
            emit('error', {'message': 'Invalid session'})
            return
        
        session_id = active_connections[request.sid]
        user_info = connected_displays[session_id]
        user_id = user_info['user_id']
        
        # Prepare alert data
        alert_data = {
            'alert_id': str(uuid.uuid4()),
            'type': alert_type,
            'message': message,
            'order_id': order_id,
            'from_user': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Broadcast to target stations
        target_rooms = [f'kitchen_{station}' for station in target_stations]
        for room in target_rooms:
            socketio.emit('kitchen_alert', alert_data, room=room)
        
        # Also broadcast to general kitchen room
        socketio.emit('kitchen_alert', alert_data, room='kitchen_general')
        
        emit('alert_sent', {
            'alert_id': alert_data['alert_id'],
            'message': 'Alert sent successfully'
        })
        
        current_app.logger.info(f"Kitchen alert sent: {alert_type} - {message}")
        
    except Exception as e:
        current_app.logger.error(f"Error sending kitchen alert: {str(e)}")
        emit('error', {'message': f'Failed to send alert: {str(e)}'})

@socketio.on('get_display_status')
def handle_get_display_status():
    """Get current display connection status"""
    try:
        if request.sid not in active_connections:
            emit('error', {'message': 'Invalid session'})
            return
        
        session_id = active_connections[request.sid]
        if session_id not in connected_displays:
            emit('error', {'message': 'Display not found'})
            return
        
        display_info = connected_displays[session_id]
        display = display_info['display']
        
        # Get active orders count
        active_orders_count = Order.query.filter(
            Order.status.in_(['New', 'In Progress', 'Ready'])
        ).count()
        
        # Get connected displays count
        connected_count = len([d for d in connected_displays.values() if d['display'].is_active])
        
        emit('display_status', {
            'session_id': session_id,
            'display_name': display.display_name,
            'station_type': display.station_type,
            'kitchen_role': display.kitchen_role,
            'is_connected': display.is_connected,
            'last_heartbeat': display.last_heartbeat.isoformat() if display.last_heartbeat else None,
            'connected_displays': connected_count,
            'active_orders': active_orders_count,
            'connection_duration': display.connection_duration
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting display status: {str(e)}")
        emit('error', {'message': f'Failed to get display status: {str(e)}'})

# Background tasks for real-time updates
def start_background_tasks():
    """Start background tasks for real-time system"""
    def cleanup_inactive_displays():
        """Clean up inactive display connections"""
        while True:
            try:
                current_time = datetime.utcnow()
                inactive_sessions = []
                
                for session_id, display_info in connected_displays.items():
                    display = display_info['display']
                    if not display.is_active:
                        inactive_sessions.append(session_id)
                
                for session_id in inactive_sessions:
                    display_info = connected_displays[session_id]
                    display = display_info['display']
                    display.disconnect()
                    del connected_displays[session_id]
                    
                    # Clean up socket tracking
                    socket_id = display_info.get('socket_id')
                    if socket_id and socket_id in active_connections:
                        del active_connections[socket_id]
                
                if inactive_sessions:
                    current_app.logger.info(f"Cleaned up {len(inactive_sessions)} inactive display connections")
                
                time.sleep(60)  # Run every minute
                
            except Exception as e:
                current_app.logger.error(f"Error in cleanup task: {str(e)}")
                time.sleep(60)
    
    def update_real_time_metrics():
        """Update real-time performance metrics"""
        while True:
            try:
                # Calculate current metrics
                current_time = datetime.utcnow()
                
                # Active orders count
                active_orders = Order.query.filter(
                    Order.status.in_(['New', 'In Progress', 'Ready'])
                ).count()
                
                # Connected displays count
                connected_displays_count = len([d for d in connected_displays.values() if d['display'].is_active])
                
                # Average order age
                recent_orders = Order.query.filter(
                    Order.created_at >= current_time - timedelta(hours=1)
                ).all()
                
                if recent_orders:
                    total_age = sum([(current_time - order.created_at).total_seconds() / 60 
                                   for order in recent_orders])
                    avg_order_age = total_age / len(recent_orders)
                else:
                    avg_order_age = 0
                
                        # Store metrics
                metrics_data = [
                    ('active_orders', active_orders, 'count'),
                    ('connected_displays', connected_displays_count, 'count'),
                    ('average_order_age', avg_order_age, 'minutes')
                ]
                
                for metric_name, metric_value, unit in metrics_data:
                    metric = RealTimeMetrics(
                        metric_type='kitchen_performance',
                        metric_name=metric_name,
                        metric_value=metric_value,
                        metric_unit=unit,
                        data_source='websocket_system'
                    )
                    db.session.add(metric)
                
                db.session.commit()
                
                # Broadcast analytics updates to connected clients
                broadcast_analytics_update({
                    'active_orders': active_orders,
                    'connected_displays': connected_displays_count,
                    'average_order_age': avg_order_age,
                    'timestamp': current_time.isoformat()
                })
                
                time.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                current_app.logger.error(f"Error updating metrics: {str(e)}")
                time.sleep(30)
    
    # Start background threads (in production, use proper task queue)
    import threading
    
    cleanup_thread = threading.Thread(target=cleanup_inactive_displays, daemon=True)
    cleanup_thread.start()
    
    metrics_thread = threading.Thread(target=update_real_time_metrics, daemon=True)
    metrics_thread.start()

def init_websocket(app, socketio):
    """Initialize WebSocket with Flask app"""
    global socketio as global_socketio
    global_socketio = socketio
    
    # Initialize real-time models
    enhance_order_model()
    
    # Start background tasks
    start_background_tasks()
    
    # Register SocketIO event handlers
    socketio.init_app(app)
    
    return socketio

# Export WebSocket blueprint and initialization function
__all__ = ['websocket_bp', 'socketio', 'init_websocket']