from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from models import db, Order, OrderItem, MenuItem, Table
from datetime import datetime, timedelta

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
    """Get active orders via AJAX"""
    orders = Order.query.filter(
        Order.status.in_(['New', 'In Progress', 'Ready'])
    ).order_by(Order.created_at.desc()).all()
    
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
                'special_instructions': item.special_instructions
            }
            for item in items
        ]
        
        if order.table_id:
            table = Table.query.get(order.table_id)
            order_dict['table_number'] = table.table_number if table else None
        
        order_data.append(order_dict)
    
    return jsonify({
        'success': True,
        'orders': order_data
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
    """Bulk update multiple items status"""
    try:
        data = request.get_json()
        item_ids = data.get('item_ids', [])
        status = data.get('status')
        
        if not item_ids:
            return jsonify({'success': False, 'message': 'No items selected'}), 400
        
        valid_statuses = ['Pending', 'In Progress', 'Ready', 'Completed', 'Cancelled']
        if status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        updated_count = 0
        for item_id in item_ids:
            order_item = OrderItem.query.get(item_id)
            if order_item:
                order_item.status = status
                updated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{updated_count} items updated to {status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
