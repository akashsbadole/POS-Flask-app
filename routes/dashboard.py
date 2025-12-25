from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Order, MenuItem, Table, Category, Settings
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard home page"""
    # Get dashboard statistics
    stats = get_dashboard_stats()
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Get low stock items
    low_stock_items = MenuItem.query.filter_by(is_low_stock=True, is_active=True).limit(5).all()
    
    # Get available tables
    available_tables = Table.query.filter_by(status='Available', is_active=True).count()
    
    return render_template('dashboard/index.html', 
                        stats=stats, 
                        recent_orders=recent_orders,
                        low_stock_items=low_stock_items,
                        available_tables=available_tables)

@dashboard_bp.route('/stats')
@login_required
def get_stats():
    """Get dashboard statistics via AJAX"""
    stats = get_dashboard_stats()
    return jsonify(stats)

def get_dashboard_stats():
    """Get dashboard statistics"""
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Today's stats
    today_orders = Order.query.filter(Order.created_at >= datetime.combine(today, datetime.min.time())).count()
    today_revenue = db.session.query(db.func.sum(Order.grand_total)).filter(
        Order.created_at >= datetime.combine(today, datetime.min.time())
    ).scalar() or 0
    
    # This week's stats
    week_orders = Order.query.filter(Order.created_at >= datetime.combine(week_ago, datetime.min.time())).count()
    week_revenue = db.session.query(db.func.sum(Order.grand_total)).filter(
        Order.created_at >= datetime.combine(week_ago, datetime.min.time())
    ).scalar() or 0
    
    # This month's stats
    month_orders = Order.query.filter(Order.created_at >= datetime.combine(month_ago, datetime.min.time())).count()
    month_revenue = db.session.query(db.func.sum(Order.grand_total)).filter(
        Order.created_at >= datetime.combine(month_ago, datetime.min.time())
    ).scalar() or 0
    
    # Order status breakdown
    order_stats = {}
    for status in ['New', 'In Progress', 'Ready', 'Completed', 'Cancelled']:
        count = Order.query.filter_by(status=status).count()
        order_stats[status.lower().replace(' ', '_')] = count
    
    # Menu and table stats
    total_menu_items = MenuItem.query.filter_by(is_active=True).count()
    total_categories = Category.query.filter_by(is_active=True).count()
    total_tables = Table.query.count()
    
    return {
        'today': {
            'orders': today_orders,
            'revenue': float(today_revenue)
        },
        'week': {
            'orders': week_orders,
            'revenue': float(week_revenue)
        },
        'month': {
            'orders': month_orders,
            'revenue': float(month_revenue)
        },
        'orders': order_stats,
        'menu': {
            'items': total_menu_items,
            'categories': total_categories
        },
        'tables': {
            'total': total_tables,
            'available': Table.query.filter_by(status='Available', is_active=True).count()
        }
    }
