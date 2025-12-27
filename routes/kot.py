from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Order, OrderItem, MenuItem, Table
from datetime import datetime, timedelta
from utils.order_workflow import order_workflow, WorkflowAction, OrderWorkflowState
from utils.inventory_workflow import inventory_workflow
import json

kot_bp = Blueprint('kot', __name__)

def calculate_order_age(created_at):
    """Calculate order age in minutes"""
    if not created_at:
        return 0
    now = datetime.utcnow()
    diff = now - created_at
    return int(diff.total_seconds() / 60)

def calculate_urgency(age_minutes):
    """Calculate urgency level based on order age"""
    if age_minutes > 20:
        return 'high'
    elif age_minutes > 10:
        return 'medium'
    else:
        return 'normal'

def get_urgency_class(order):
    """Get CSS class for urgency based on order age"""
    age_minutes = calculate_order_age(order.created_at)
    return calculate_urgency(age_minutes)

@kot_bp.route('/')
@login_required
def index():
    """KOT dashboard page"""
    # Get active orders (not completed or cancelled)
    active_orders = Order.query.filter(
        Order.status.in_(['New', 'In Progress', 'Ready'])
    ).order_by(Order.created_at.desc()).all()
    
    # Calculate time-based urgency for each order
    for order in active_orders:
        order.age_minutes = calculate_order_age(order.created_at)
        order.urgency = calculate_urgency(order.age_minutes)
    
    # Get completed orders in last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_orders = Order.query.filter(
        Order.status == 'Completed',
        Order.created_at >= yesterday
    ).order_by(Order.created_at.desc()).limit(20).all()
    
    return render_template('kot/index.html',
                        active_orders=active_orders,
                        recent_orders=recent_orders)

@kot_bp.route('/active')
@login_required
def active_orders():
    """Get active orders via AJAX with workflow integration"""
    # Use workflow-aware status filtering
    workflow_states = [OrderWorkflowState.NEW.value, OrderWorkflowState.IN_KITCHEN.value, OrderWorkflowState.READY.value]
    orders = Order.query.filter(
        Order.status.in_(workflow_states)
    ).order_by(Order.created_at.desc()).all()
    
    # Add priority calculation and workflow metadata
    enhanced_orders = []
    for order in orders:
        order_dict = order.to_dict()
        
        # Calculate priority based on multiple factors
        priority_info = calculate_order_priority(order)
        order_dict['priority'] = priority_info
        
        # Get available workflow actions for current user
        available_actions = get_kitchen_available_actions(current_user, order)
        order_dict['available_actions'] = available_actions
        
        # Get workflow timeline
        timeline = order_workflow.get_order_timeline(order.id)
        order_dict['timeline'] = timeline
        
        # Add item-level workflow information
        items = OrderItem.query.filter_by(order_id=order.id).all()
        order_dict['items'] = [
            {
                'id': item.id,
                'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                'quantity': item.quantity,
                'status': item.status,
                'special_instructions': item.special_instructions,
                'workflow_state': get_item_workflow_state(item.status)
            }
            for item in items
        ]
        
        if order.table_id:
            table = Table.query.get(order.table_id)
            order_dict['table_number'] = table.table_number if table else None
        
        enhanced_orders.append(order_dict)
    
    return jsonify({
        'success': True,
        'orders': enhanced_orders,
        'workflow_states': [state.value for state in OrderWorkflowState],
        'timestamp': datetime.utcnow().isoformat()
    })

@kot_bp.route('/update_item_status', methods=['POST'])
@login_required
def update_item_status():
    """Update KOT item status via AJAX"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        status = data.get('status')
        
        valid_statuses = ['Pending', 'In Progress', 'Ready', 'Completed', 'Cancelled']
        if status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        order_item = OrderItem.query.get(item_id)
        if not order_item:
            return jsonify({'success': False, 'message': 'Order item not found'}), 404
        
        order_item.status = status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Item status updated to {status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@kot_bp.route('/print/<int:order_id>')
@login_required
def print_kot(order_id):
    """Print KOT for order"""
    from models import Settings
    order = Order.query.get_or_404(order_id)
    items = OrderItem.query.filter_by(order_id=order_id).all()
    settings = Settings.get_all_as_dict()
    
    # Calculate time-based urgency
    order.age_minutes = calculate_order_age(order.created_at)
    order.urgency = calculate_urgency(order.age_minutes)
    
    # Check for modifiers
    has_modifiers = any(item.modifications for item in items if item.modifications)
    
    return render_template('kot/print.html',
                        order=order,
                        order_items=items,
                        settings=settings,
                        has_modifiers=has_modifiers,
                        get_urgency_class=get_urgency_class)

@kot_bp.route('/kitchen_display')
@login_required
def kitchen_display():
    """Kitchen display for monitors"""
    active_orders = Order.query.filter(
        Order.status.in_(['New', 'In Progress'])
    ).order_by(Order.created_at.desc()).all()
    
    # Group by status for display
    pending_orders = [o for o in active_orders if o.status == 'New']
    progress_orders = [o for o in active_orders if o.status == 'In Progress']
    ready_orders = [o for o in active_orders if o.status == 'Ready']
    
    return render_template('kot/kitchen_display.html',
                        pending_orders=pending_orders,
                        progress_orders=progress_orders,
                        ready_orders=ready_orders)

@kot_bp.route('/window')
@login_required
def kot_window():
    """KOT screen that opens in a new window"""
    # Get active orders (not completed or cancelled)
    active_orders = Order.query.filter(
        Order.status.in_(['New', 'In Progress', 'Ready'])
    ).order_by(Order.created_at.desc()).all()
    
    # Get completed orders in last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_orders = Order.query.filter(
        Order.status == 'Completed',
        Order.created_at >= yesterday
    ).order_by(Order.created_at.desc()).limit(20).all()
    
    return render_template('kot/window.html',
                        active_orders=active_orders,
                        recent_orders=recent_orders)

@kot_bp.route('/api/orders')
@login_required
def get_orders_api():
    """API endpoint to get orders with real-time updates"""
    status_filter = request.args.get('status', 'active')
    
    if status_filter == 'active':
        orders = Order.query.filter(
            Order.status.in_(['New', 'In Progress', 'Ready'])
        ).order_by(Order.created_at.desc()).all()
    elif status_filter == 'completed':
        yesterday = datetime.utcnow() - timedelta(days=1)
        orders = Order.query.filter(
            Order.status == 'Completed',
            Order.created_at >= yesterday
        ).order_by(Order.created_at.desc()).limit(50).all()
    else:
        orders = Order.query.filter_by(status=status_filter).order_by(Order.created_at.desc()).all()
    
    order_data = []
    for order in orders:
        items = OrderItem.query.filter_by(order_id=order.id).all()
        
        order_dict = order.to_dict()
        order_dict['items'] = [
            {
                'id': item.id,
                'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                'quantity': item.quantity,
                'status': item.status,
                'special_instructions': item.special_instructions,
                'price': float(item.price) if item.price else 0.0,
                'total': float(item.total) if item.total else 0.0
            }
            for item in items
        ]
        
        if order.table_id:
            table = Table.query.get(order.table_id)
            order_dict['table_number'] = table.table_number if table else None
        
        # Calculate order age for urgency indicator
        order_age = datetime.utcnow() - order.created_at
        order_dict['age_minutes'] = int(order_age.total_seconds() / 60)
        order_dict['urgency'] = 'high' if order_age > timedelta(minutes=30) else 'medium' if order_age > timedelta(minutes=15) else 'normal'
        
        order_data.append(order_dict)
    
    return jsonify({
        'success': True,
        'orders': order_data,
        'timestamp': datetime.utcnow().isoformat()
    })

@kot_bp.route('/api/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    """Update order status via AJAX"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        status = data.get('status')
        
        valid_statuses = ['New', 'In Progress', 'Ready', 'Completed', 'Cancelled']
        if status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        order.status = status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Order status updated to {status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@kot_bp.route('/api/update_item_status', methods=['POST'])
@login_required
def update_item_status_api():
    """Update individual item status via AJAX"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        status = data.get('status')
        
        valid_statuses = ['Pending', 'In Progress', 'Ready', 'Completed', 'Cancelled']
        if status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        order_item = OrderItem.query.get(item_id)
        if not order_item:
            return jsonify({'success': False, 'message': 'Order item not found'}), 404
        
        order_item.status = status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Item status updated to {status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@kot_bp.route('/api/bulk_update', methods=['POST'])
@login_required
def bulk_update_status():
    """Bulk update multiple items status with workflow integration"""
    try:
        data = request.get_json()
        item_ids = data.get('item_ids', [])
        status = data.get('status')
        order_id = data.get('order_id')  # Optional: bulk update for specific order
        
        if not item_ids:
            return jsonify({'success': False, 'message': 'No items selected'}), 400
        
        # Validate status against workflow states
        try:
            workflow_state = OrderWorkflowState(status)
        except ValueError:
            valid_states = [state.value for state in OrderWorkflowState]
            return jsonify({'success': False, 'message': f'Invalid status. Valid statuses: {valid_states}'}), 400
        
        updated_count = 0
        results = []
        
        for item_id in item_ids:
            order_item = OrderItem.query.get(item_id)
            if order_item:
                # Use workflow engine for consistent status updates
                order = order_item.order
                if order:
                    # Determine appropriate workflow action based on new status
                    workflow_action = get_workflow_action_from_status(workflow_state, current_user.role)
                    
                    if workflow_action:
                        success, message, result = order_workflow.execute_workflow_action(
                            current_user, order.id, workflow_action, 
                            {'item_id': item_id, 'target_status': status}
                        )
                        
                        results.append({
                            'item_id': item_id,
                            'success': success,
                            'message': message
                        })
                        
                        if success:
                            updated_count += 1
                    else:
                        # Fallback to direct status update
                        order_item.status = status
                        updated_count += 1
                        results.append({
                            'item_id': item_id,
                            'success': True,
                            'message': 'Status updated directly'
                        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{updated_count} items updated successfully',
            'updated_count': updated_count,
            'results': results
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Workflow Management Endpoints
@kot_bp.route('/workflow/send_to_kitchen', methods=['POST'])
@login_required
def workflow_send_to_kitchen():
    """Send order to kitchen using workflow engine"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        success, message, result = order_workflow.execute_workflow_action(
            current_user, order_id, WorkflowAction.SEND_TO_KITCHEN, data
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'result': result
            })
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@kot_bp.route('/workflow/mark_ready', methods=['POST'])
@login_required
def workflow_mark_ready():
    """Mark order as ready using workflow engine"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        success, message, result = order_workflow.execute_workflow_action(
            current_user, order_id, WorkflowAction.MARK_READY, data
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'result': result
            })
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@kot_bp.route('/workflow/priority_orders')
@login_required
def get_priority_orders():
    """Get orders prioritized by workflow and business rules"""
    try:
        # Get active orders
        workflow_states = [OrderWorkflowState.NEW.value, OrderWorkflowState.IN_KITCHEN.value]
        orders = Order.query.filter(
            Order.status.in_(workflow_states)
        ).order_by(Order.created_at.asc()).all()
        
        # Calculate priorities
        prioritized_orders = []
        for order in orders:
            priority_info = calculate_order_priority(order)
            order_dict = order.to_dict()
            order_dict['priority'] = priority_info
            order_dict['available_actions'] = get_kitchen_available_actions(current_user, order)
            prioritized_orders.append(order_dict)
        
        # Sort by priority score (higher score = higher priority)
        prioritized_orders.sort(key=lambda x: x['priority']['score'], reverse=True)
        
        return jsonify({
            'success': True,
            'orders': prioritized_orders,
            'priority_criteria': {
                'time_based': 'Orders older than 10 minutes get higher priority',
                'table_based': 'Dine-in orders get priority over takeaway',
                'complexity_based': 'Orders with more items get earlier attention',
                'status_based': 'New orders get priority over in-progress orders'
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@kot_bp.route('/workflow/kitchen_metrics')
@login_required
def kitchen_workflow_metrics():
    """Get kitchen workflow performance metrics"""
    try:
        # Calculate metrics for last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        # Get orders from last 24 hours
        recent_orders = Order.query.filter(
            Order.created_at >= yesterday
        ).all()
        
        # Calculate workflow metrics
        metrics = {
            'total_orders_24h': len(recent_orders),
            'completed_orders_24h': len([o for o in recent_orders if o.status == OrderWorkflowState.COMPLETED.value]),
            'average_completion_time': 0,
            'orders_by_status': {},
            'peak_hours': [],
            'kitchen_efficiency': {}
        }
        
        # Status distribution
        for order in recent_orders:
            status = order.status
            metrics['orders_by_status'][status] = metrics['orders_by_status'].get(status, 0) + 1
        
        # Calculate average completion time
        completed_orders = [o for o in recent_orders if o.status == OrderWorkflowState.COMPLETED.value and o.completed_at]
        if completed_orders:
            total_time = sum([(o.completed_at - o.created_at).total_seconds() for o in completed_orders])
            metrics['average_completion_time'] = total_time / len(completed_orders) / 60  # in minutes
        
        # Peak hours analysis
        hourly_counts = {}
        for order in recent_orders:
            hour = order.created_at.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        # Find peak hours (top 3 hours with most orders)
        sorted_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)
        metrics['peak_hours'] = sorted_hours[:3]
        
        return jsonify({
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Helper Functions
def calculate_order_priority(order):
    """Calculate order priority based on multiple factors"""
    score = 0
    factors = []
    
    # Time-based priority (older orders get higher priority)
    age_minutes = calculate_order_age(order.created_at)
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
    
    # Table-based priority (occupied tables get priority)
    if order.table_id:
        table = Table.query.get(order.table_id)
        if table and table.status == 'Occupied':
            score += 15
            factors.append('occupied_table')
    
    # Complexity-based priority (more items = higher priority for attention)
    item_count = len(order.order_items)
    if item_count > 5:
        score += 20
        factors.append('complex_order')
    elif item_count > 3:
        score += 10
        factors.append('medium_complexity')
    
    # Status-based priority
    if order.status == OrderWorkflowState.NEW.value:
        score += 30
        factors.append('new_order')
    elif order.status == OrderWorkflowState.IN_KITCHEN.value:
        score += 20
        factors.append('in_progress')
    
    return {
        'score': score,
        'factors': factors,
        'age_minutes': age_minutes,
        'level': 'critical' if score >= 60 else 'high' if score >= 40 else 'medium' if score >= 20 else 'normal'
    }

def get_kitchen_available_actions(user, order):
    """Get available workflow actions for kitchen staff on specific order"""
    available_actions = []
    
    # Check each workflow action
    for action in WorkflowAction:
        can_perform, _ = order_workflow.can_perform_action(user, action, order)
        if can_perform:
            # Filter actions relevant to kitchen workflow
            if action in [WorkflowAction.SEND_TO_KITCHEN, WorkflowAction.MARK_READY, WorkflowAction.MODIFY_ORDER]:
                available_actions.append(action.value)
    
    return available_actions

def get_item_workflow_state(item_status):
    """Get workflow state for order item"""
    status_mapping = {
        'Pending': OrderWorkflowState.NEW.value,
        'In Progress': OrderWorkflowState.IN_KITCHEN.value,
        'Ready': OrderWorkflowState.READY.value,
        'Completed': OrderWorkflowState.COMPLETED.value,
        'Cancelled': OrderWorkflowState.CANCELLED.value
    }
    return status_mapping.get(item_status, OrderWorkflowState.NEW.value)

def get_workflow_action_from_status(workflow_state, user_role):
    """Get appropriate workflow action based on target status and user role"""
    # This would be enhanced based on your specific workflow requirements
    if user_role.lower() in ['kitchen_staff', 'manager', 'admin']:
        if workflow_state == OrderWorkflowState.IN_KITCHEN:
            return WorkflowAction.SEND_TO_KITCHEN
        elif workflow_state == OrderWorkflowState.READY:
            return WorkflowAction.MARK_READY
    
    return None
