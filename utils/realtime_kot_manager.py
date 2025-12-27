"""
Real-time KOT Manager
Handles real-time order workflow integration and WebSocket broadcasting
"""

from datetime import datetime, timedelta
from flask import current_app
from flask_socketio import SocketIO
from models import db, Order, OrderItem, KOTEvent, OrderStatusHistory, KitchenDisplay
from models.realtime_kot import broadcast_order_event
import json
import uuid

class RealTimeKOTManager:
    """Manager for real-time KOT operations"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio or current_app.socketio if hasattr(current_app, 'socketio') else None
        
    def create_order_with_realtime(self, order_data, user_id, user_role):
        """Create new order and broadcast via WebSocket"""
        try:
            # Create order in database
            order = Order(
                order_number=order_data.get('order_number'),
                table_id=order_data.get('table_id'),
                customer_name=order_data.get('customer_name'),
                customer_mobile=order_data.get('customer_mobile'),
                order_type=order_data.get('order_type', 'Dine-in'),
                special_instructions=order_data.get('special_instructions'),
                created_by=user_id
            )
            
            # Add items to order
            items = order_data.get('items', [])
            for item_data in items:
                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=item_data['menu_item_id'],
                    quantity=item_data['quantity'],
                    price=item_data['price']
                )
                order_item.special_instructions = item_data.get('special_instructions')
                db.session.add(order_item)
            
            # Calculate totals
            order.calculate_totals()
            
            # Set initial status
            order.status = 'New'
            order.updated_at = datetime.utcnow()
            
            db.session.add(order)
            db.session.commit()
            
            # Create KOT event for new order
            event = self.create_kot_event(
                event_type='new_order',
                order_id=order.id,
                user_id=user_id,
                user_role=user_role,
                event_data={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'table_number': order.table.table_number if order.table else None,
                    'customer_name': order.customer_name_decrypted,
                    'order_type': order.order_type,
                    'grand_total': float(order.grand_total),
                    'items_count': len(order.order_items),
                    'priority_score': self.calculate_order_priority(order)['score'],
                    'estimated_prep_time': self.estimate_preparation_time(order)
                }
            )
            
            # Broadcast new order to kitchen displays
            self.broadcast_new_order(order, event)
            
            return {
                'success': True,
                'order': order,
                'event': event,
                'message': 'Order created and broadcast to kitchen displays'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to create order with real-time: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create order'
            }
    
    def update_order_status_realtime(self, order_id, new_status, user_id, user_role, reason=None):
        """Update order status with real-time broadcasting"""
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'error': 'Order not found'}
            
            old_status = order.status
            if old_status == new_status:
                return {'success': True, 'message': 'Status unchanged'}
            
            # Update order status
            order.status = new_status
            order.updated_at = datetime.utcnow()
            
            # Handle status-specific updates
            if new_status == 'Completed':
                order.completed_at = datetime.utcnow()
                self.update_order_metrics(order, user_id, user_role)
            elif new_status == 'In Progress':
                order.started_at = datetime.utcnow()
            elif new_status == 'Ready':
                order.ready_at = datetime.utcnow()
            
            # Create status history entry
            history = OrderStatusHistory(
                order_id=order.id,
                previous_status=old_status,
                new_status=new_status,
                changed_by_user_id=user_id,
                changed_by_role=user_role,
                reason=reason,
                changed_by_username=self.get_user_username(user_id)
            )
            
            # Create KOT event
            event = self.create_kot_event(
                event_type='order_update',
                order_id=order.id,
                user_id=user_id,
                user_role=user_role,
                event_data={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'old_status': old_status,
                    'new_status': new_status,
                    'reason': reason,
                    'timestamp': datetime.utcnow().isoformat(),
                    'changed_by': user_id,
                    'changed_by_role': user_role
                }
            )
            
            db.session.add(history)
            db.session.commit()
            
            # Broadcast status update
            self.broadcast_order_status_update(order, old_status, new_status, event)
            
            return {
                'success': True,
                'order': order,
                'event': event,
                'message': f'Order {order.order_number} status updated to {new_status}'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update order status with real-time: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to update order status'
            }
    
    def update_item_status_realtime(self, item_id, new_status, user_id, user_role):
        """Update item status with real-time broadcasting"""
        try:
            item = OrderItem.query.get(item_id)
            if not item:
                return {'success': False, 'error': 'Order item not found'}
            
            old_status = item.status
            if old_status == new_status:
                return {'success': True, 'message': 'Status unchanged'}
            
            # Update item status
            item.status = new_status
            item.updated_at = datetime.utcnow()
            
            # Check if all items are ready and update order status
            order = item.order
            if new_status == 'Ready':
                self.check_and_update_order_based_on_items(order)
            
            # Create status history entry
            history = OrderStatusHistory(
                order_id=order.id,
                previous_status=old_status,
                new_status=new_status,
                changed_by_user_id=user_id,
                changed_by_role=user_role,
                order_item_id=item.id,
                changed_by_username=self.get_user_username(user_id)
            )
            
            # Create KOT event
            event = self.create_kot_event(
                event_type='item_update',
                order_id=order.id,
                order_item_id=item.id,
                user_id=user_id,
                user_role=user_role,
                event_data={
                    'order_id': order.id,
                    'order_item_id': item.id,
                    'item_name': item.item_name,
                    'old_status': old_status,
                    'new_status': new_status,
                    'quantity': item.quantity,
                    'timestamp': datetime.utcnow().isoformat(),
                    'changed_by': user_id,
                    'changed_by_role': user_role
                }
            )
            
            db.session.add(history)
            db.session.commit()
            
            # Broadcast item status update
            self.broadcast_item_status_update(order, item, old_status, new_status, event)
            
            return {
                'success': True,
                'item': item,
                'event': event,
                'message': f'Item {item.item_name} status updated to {new_status}'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update item status with real-time: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to update item status'
            }
    
    def send_kitchen_alert(self, alert_type, message, target_stations=None, order_id=None, user_id=None):
        """Send kitchen alert via WebSocket"""
        try:
            if not target_stations:
                target_stations = ['general']
            
            alert_data = {
                'alert_id': str(uuid.uuid4()),
                'type': alert_type,
                'message': message,
                'order_id': order_id,
                'from_user': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'priority': 'high' if alert_type == 'urgent' else 'normal'
            }
            
            # Broadcast to target stations
            target_rooms = [f'kitchen_{station}' for station in target_stations]
            
            if self.socketio:
                for room in target_rooms:
                    self.socketio.emit('kitchen_alert', alert_data, room=room)
                
                # Also broadcast to general kitchen room
                self.socketio.emit('kitchen_alert', alert_data, room='kitchen_general')
            
            current_app.logger.info(f"Kitchen alert sent: {alert_type} - {message}")
            return {'success': True, 'alert_data': alert_data}
            
        except Exception as e:
            current_app.logger.error(f"Failed to send kitchen alert: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_kot_event(self, event_type, order_id=None, order_item_id=None, user_id=None, user_role=None, event_data=None):
        """Create KOT event record"""
        event = KOTEvent(
            event_type=event_type,
            user_id=user_id,
            user_role=user_role,
            order_id=order_id,
            order_item_id=order_item_id
        )
        
        if event_data:
            event.set_event_data(event_data)
        
        # Set priority based on event type
        if event_type in ['new_order', 'urgent_order']:
            event.priority = 'high'
            event.is_urgent = True
        elif event_type in ['order_cancelled', 'kitchen_alert']:
            event.priority = 'medium'
        else:
            event.priority = 'normal'
        
        db.session.add(event)
        return event
    
    def broadcast_new_order(self, order, event):
        """Broadcast new order to kitchen displays"""
        try:
            # Prepare order data for broadcasting
            order_data = {
                'order_id': order.id,
                'order_number': order.order_number,
                'table_number': order.table.table_number if order.table else None,
                'customer_name': order.customer_name_decrypted,
                'order_type': order.order_type,
                'status': order.status,
                'grand_total': float(order.grand_total),
                'special_instructions': order.special_instructions,
                'created_at': order.created_at.isoformat(),
                'priority': self.calculate_order_priority(order),
                'items': [item.to_dict() for item in order.order_items],
                'estimated_prep_time': self.estimate_preparation_time(order),
                'event_id': event.event_id
            }
            
            # Broadcast to all kitchen displays
            if self.socketio:
                self.socketio.emit('order_event', {
                    'type': 'new_order',
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': order_data
                }, room='kitchen_general')
                
                # Also broadcast to specific station rooms
                station_rooms = self.get_order_station_rooms(order)
                for room in station_rooms:
                    self.socketio.emit('order_event', {
                        'type': 'new_order',
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': order_data
                    }, room=room)
            
            current_app.logger.info(f"Broadcasted new order {order.order_number} to kitchen displays")
            
        except Exception as e:
            current_app.logger.error(f"Failed to broadcast new order: {str(e)}")
    
    def broadcast_order_status_update(self, order, old_status, new_status, event):
        """Broadcast order status update"""
        try:
            event_data = {
                'order_id': order.id,
                'order_number': order.order_number,
                'old_status': old_status,
                'new_status': new_status,
                'timestamp': datetime.utcnow().isoformat(),
                'changed_by': event.user_id,
                'changed_by_role': event.user_role,
                'event_id': event.event_id
            }
            
            # Broadcast to all kitchen displays
            if self.socketio:
                self.socketio.emit('order_event', {
                    'type': 'order_update',
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': event_data
                }, room='kitchen_general')
                
                # Broadcast to order subscribers
                self.socketio.emit('order_event', {
                    'type': 'order_update',
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': event_data
                }, room=f'order_{order.id}')
            
            current_app.logger.info(f"Broadcasted order {order.order_number} status update: {old_status} -> {new_status}")
            
        except Exception as e:
            current_app.logger.error(f"Failed to broadcast order status update: {str(e)}")
    
    def broadcast_item_status_update(self, order, item, old_status, new_status, event):
        """Broadcast item status update"""
        try:
            event_data = {
                'order_id': order.id,
                'order_item_id': item.id,
                'item_name': item.item_name,
                'old_status': old_status,
                'new_status': new_status,
                'quantity': item.quantity,
                'timestamp': datetime.utcnow().isoformat(),
                'changed_by': event.user_id,
                'changed_by_role': event.user_role,
                'event_id': event.event_id
            }
            
            # Broadcast to kitchen displays
            if self.socketio:
                self.socketio.emit('order_event', {
                    'type': 'item_update',
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': event_data
                }, room='kitchen_general')
                
                # Broadcast to order subscribers
                self.socketio.emit('order_event', {
                    'type': 'item_update',
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': event_data
                }, room=f'order_{order.id}')
            
            current_app.logger.info(f"Broadcasted item {item.item_name} status update: {old_status} -> {new_status}")
            
        except Exception as e:
            current_app.logger.error(f"Failed to broadcast item status update: {str(e)}")
    
    def calculate_order_priority(self, order):
        """Calculate order priority for real-time display"""
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
            
            # Complexity-based priority
            item_count = len(order.order_items)
            if item_count > 5:
                score += 20
                factors.append('complex_order')
            elif item_count > 3:
                score += 10
                factors.append('medium_complexity')
            
            return {
                'score': score,
                'factors': factors,
                'age_minutes': int(age_minutes),
                'level': 'critical' if score >= 60 else 'high' if score >= 40 else 'medium' if score >= 20 else 'normal'
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to calculate order priority: {str(e)}")
            return {'score': 0, 'factors': [], 'age_minutes': 0, 'level': 'normal'}
    
    def estimate_preparation_time(self, order):
        """Estimate preparation time for order"""
        try:
            # Base time calculation
            base_time = 10  # minutes
            
            # Add time based on item count
            item_count = len(order.order_items)
            item_time = item_count * 3  # 3 minutes per item
            
            # Add time based on complexity
            complex_items = [item for item in order.order_items if item.special_instructions]
            complex_time = len(complex_items) * 5  # 5 minutes per special item
            
            total_estimate = base_time + item_time + complex_time
            
            # Adjust based on kitchen load
            active_orders = Order.query.filter(
                Order.status.in_(['New', 'In Progress'])
            ).count()
            
            if active_orders > 5:
                total_estimate *= 1.5  # 50% increase for high load
            
            return int(total_estimate)
            
        except Exception as e:
            current_app.logger.error(f"Failed to estimate preparation time: {str(e)}")
            return 15  # Default estimate
    
    def get_order_station_rooms(self, order):
        """Get appropriate station rooms for order"""
        rooms = []
        
        # Determine stations based on items
        for item in order.order_items:
            if item.menu_item:
                # This would be enhanced based on menu categorization
                category = item.menu_item.category.name.lower() if item.menu_item.category else 'general'
                
                if 'grill' in category:
                    rooms.append('kitchen_grill')
                elif 'fry' in category:
                    rooms.append('kitchen_fry')
                elif 'salad' in category:
                    rooms.append('kitchen_salad')
                elif 'dessert' in category:
                    rooms.append('kitchen_dessert')
                else:
                    rooms.append('kitchen_general')
        
        # Remove duplicates and return
        return list(set(rooms))
    
    def check_and_update_order_based_on_items(self, order):
        """Check if all items are ready and update order status accordingly"""
        try:
            items = order.order_items
            
            # Check if all items are ready or completed
            all_ready = all(item.status in ['Ready', 'Completed'] for item in items)
            any_in_progress = any(item.status == 'In Progress' for item in items)
            
            if all_ready and not any_in_progress and order.status == 'In Progress':
                # All items ready, mark order as ready
                order.status = 'Ready'
                order.ready_at = datetime.utcnow()
                order.updated_at = datetime.utcnow()
                
                # Create event for auto-status update
                event = self.create_kot_event(
                    event_type='order_auto_ready',
                    order_id=order.id,
                    user_id=0,  # System user
                    user_role='system',
                    event_data={
                        'reason': 'All items marked as ready',
                        'auto_generated': True
                    }
                )
                
                db.session.add(event)
                db.session.commit()
                
                # Broadcast auto-update
                self.broadcast_order_status_update(order, 'In Progress', 'Ready', event)
            
        except Exception as e:
            current_app.logger.error(f"Failed to check and update order based on items: {str(e)}")
    
    def update_order_metrics(self, order, user_id, user_role):
        """Update order performance metrics"""
        try:
            if order.created_at and order.completed_at:
                prep_time = (order.completed_at - order.created_at).total_seconds() / 60
                
                # Store metrics (you might want to create a separate metrics model)
                # For now, just log the metrics
                current_app.logger.info(f"Order {order.order_number} completed in {prep_time:.1f} minutes")
                
                # Send metrics to connected displays
                if self.socketio:
                    self.socketio.emit('order_metrics', {
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'preparation_time': prep_time,
                        'completion_time': datetime.utcnow().isoformat()
                    }, room='kitchen_general')
            
        except Exception as e:
            current_app.logger.error(f"Failed to update order metrics: {str(e)}")
    
    def get_user_username(self, user_id):
        """Get username for user ID"""
        try:
            from models.user import User
            user = User.query.get(user_id)
            return user.username if user else 'Unknown'
        except:
            return 'Unknown'
    
    def get_real_time_order_data(self, order_id):
        """Get enhanced order data for real-time display"""
        try:
            order = Order.query.get(order_id)
            if not order:
                return None
            
            order_data = order.to_dict()
            
            # Add real-time specific data
            order_data['priority'] = self.calculate_order_priority(order)
            order_data['estimated_prep_time'] = self.estimate_preparation_time(order)
            order_data['current_kitchen_load'] = Order.query.filter(
                Order.status.in_(['New', 'In Progress'])
            ).count()
            
            # Add item-level data
            items = OrderItem.query.filter_by(order_id=order.id).all()
            order_data['items'] = [item.to_dict() for item in items]
            
            # Add timeline data
            order_data['timeline'] = self.get_order_timeline(order)
            
            return order_data
            
        except Exception as e:
            current_app.logger.error(f"Failed to get real-time order data: {str(e)}")
            return None
    
    def get_order_timeline(self, order):
        """Get order timeline for display"""
        try:
            timeline = []
            
            # Order creation
            timeline.append({
                'event': 'Order Created',
                'timestamp': order.created_at.isoformat() if order.created_at else None,
                'status': 'completed'
            })
            
            # Order status changes
            status_changes = OrderStatusHistory.query.filter_by(order_id=order.id).order_by(OrderStatusHistory.status_changed_at).all()
            for change in status_changes:
                timeline.append({
                    'event': f'Status: {change.previous_status} → {change.new_status}',
                    'timestamp': change.status_changed_at.isoformat(),
                    'status': 'completed',
                    'changed_by': change.changed_by_username,
                    'reason': change.reason
                })
            
            return timeline
            
        except Exception as e:
            current_app.logger.error(f"Failed to get order timeline: {str(e)}")
            return []

# Global instance
realtime_kot_manager = RealTimeKOTManager()

def get_realtime_kot_manager():
    """Get the global real-time KOT manager instance"""
    return realtime_kot_manager