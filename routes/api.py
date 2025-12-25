from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import db, Order, OrderItem, MenuItem, Table, Category
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__)

@api_bp.route('/menu/items')
@login_required
def get_menu_items():
    """Get menu items for POS"""
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '')
    
    query = MenuItem.query.filter_by(is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(MenuItem.name.contains(search))
    
    items = query.order_by(MenuItem.name).all()
    
    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in items]
    })

@api_bp.route('/menu/categories')
@login_required
def get_categories():
    """Get categories for POS"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    
    return jsonify({
        'success': True,
        'categories': [cat.to_dict() for cat in categories]
    })

@api_bp.route('/tables')
@login_required
def get_tables():
    """Get available tables"""
    available_only = request.args.get('available_only', type=bool, default=False)
    
    query = Table.query
    if available_only:
        query = query.filter_by(is_available=True)
    
    tables = query.order_by(Table.table_number).all()
    
    return jsonify({
        'success': True,
        'tables': [table.to_dict() for table in tables]
    })

@api_bp.route('/orders/active')
@login_required
def get_active_orders():
    """Get active orders for display"""
    orders = Order.query.filter(
        Order.status.in_(['New', 'In Progress', 'Ready'])
    ).order_by(Order.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'orders': [order.to_dict() for order in orders]
    })

@api_bp.route('/orders/<int:order_id>')
@login_required
def get_order(order_id):
    """Get specific order details"""
    order = Order.query.get_or_404(order_id)
    items = OrderItem.query.filter_by(order_id=order_id).all()
    
    order_data = order.to_dict()
    order_data['items'] = [
        {
            'id': item.id,
            'menu_item_id': item.menu_item_id,
            'name': item.menu_item.name if item.menu_item else 'Unknown',
            'quantity': item.quantity,
            'price': float(item.price),
            'total': float(item.price * item.quantity),
            'status': item.status,
            'special_instructions': item.special_instructions
        }
        for item in items
    ]
    
    return jsonify({
        'success': True,
        'order': order_data
    })

@api_bp.route('/inventory/low_stock')
@login_required
def get_low_stock_items():
    """Get low stock items"""
    low_stock_items = MenuItem.query.filter_by(
        is_low_stock=True, 
        is_active=True
    ).order_by(MenuItem.stock_quantity).all()
    
    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in low_stock_items]
    })

@api_bp.route('/dashboard/stats')
@login_required
def get_dashboard_stats():
    """Get dashboard statistics"""
    today = datetime.utcnow().date()
    
    # Today's stats
    today_orders = Order.query.filter(
        Order.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    
    today_revenue = db.session.query(db.func.sum(Order.grand_total)).filter(
        Order.created_at >= datetime.combine(today, datetime.min.time())
    ).scalar() or 0
    
    # Low stock count
    low_stock_count = MenuItem.query.filter_by(is_low_stock=True, is_active=True).count()
    
    # Available tables
    available_tables = Table.query.filter_by(is_available=True).count()
    
    return jsonify({
        'success': True,
        'stats': {
            'today_orders': today_orders,
            'today_revenue': float(today_revenue),
            'low_stock_count': low_stock_count,
            'available_tables': available_tables
        }
    })

@api_bp.route('/search')
@login_required
def search():
    """Global search across items and orders"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')  # all, items, orders
    
    if not query:
        return jsonify({
            'success': False,
            'message': 'Search query required'
        }), 400
    
    results = {}
    
    if search_type in ['all', 'items']:
        # Search menu items
        items = MenuItem.query.filter(
            MenuItem.is_active == True,
            MenuItem.name.contains(query)
        ).limit(10).all()
        
        results['items'] = [item.to_dict() for item in items]
    
    if search_type in ['all', 'orders']:
        # Search orders by number or customer
        orders = Order.query.filter(
            Order.order_number.contains(query) |
            Order.customer_name.contains(query)
        ).limit(10).all()
        
        results['orders'] = [order.to_dict() for order in orders]
    
    return jsonify({
        'success': True,
        'query': query,
        'results': results
    })

@api_bp.route('/kot/active')
@login_required
def get_kot_active_orders():
    """Get active orders for KOT display"""
    orders = Order.query.filter(
        Order.status.in_(['New', 'In Progress', 'Ready'])
    ).order_by(Order.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'orders': [order.to_dict() for order in orders]
    })

@api_bp.route('/kot/update_item_status', methods=['POST'])
@login_required
def update_kot_item_status():
    """Update individual item status"""
    data = request.get_json()
    
    if not data or 'item_id' not in data or 'status' not in data:
        return jsonify({
            'success': False,
            'message': 'Item ID and status required'
        }), 400
    
    item = OrderItem.query.get_or_404(data['item_id'])
    old_status = item.status
    item.status = data['status']
    
    # Update order status if all items are ready
    if data['status'] == 'Completed':
        all_completed = OrderItem.query.filter_by(
            order_id=item.order_id
        ).filter(OrderItem.status != 'Completed').count() == 0
        
        if all_completed:
            order = Order.query.get(item.order_id)
            order.status = 'Completed'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Item status updated from {old_status} to {data["status"]}'
    })
