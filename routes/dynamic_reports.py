"""
Dynamic Reports API Routes
RESTful API endpoints for dynamic reports with real-time capabilities
"""

from flask import Blueprint, request, jsonify, render_template, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import io
import csv
from decimal import Decimal

from models import db, Order, Payment, MenuItem, Category, User
from utils.dynamic_reports import DynamicReportsEngine
from utils.permissions import Permissions, require_permission
from utils.cache_manager import MultiLevelCache, get_cache_manager

dynamic_reports_bp = Blueprint('dynamic_reports', __name__)
reports_engine = DynamicReportsEngine()
cache_manager = get_cache_manager()

@dynamic_reports_bp.route('/')
@login_required
@require_permission(Permissions.VIEW_REPORTS)
def dashboard():
    """Main dynamic reports dashboard"""
    return render_template('dynamic_reports/dashboard.html')

@dynamic_reports_bp.route('/sales')
@login_required
@require_permission(Permissions.VIEW_REPORTS)
def sales_report():
    """Interactive sales analytics dashboard"""
    return render_template('dynamic_reports/sales_report.html')

@dynamic_reports_bp.route('/inventory')
@login_required
@require_permission(Permissions.VIEW_INVENTORY)
def inventory_report():
    """Real-time inventory analytics dashboard"""
    return render_template('dynamic_reports/inventory_report.html')

@dynamic_reports_bp.route('/orders')
@login_required
@require_permission(Permissions.VIEW_ORDERS)
def order_analytics():
    """Order performance metrics dashboard"""
    return render_template('dynamic_reports/order_analytics.html')

# API Endpoints

@dynamic_reports_bp.route('/api/dashboard/data')
@login_required
@require_permission(Permissions.VIEW_REPORTS)
def api_dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        # Parse query parameters
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        include_realtime = request.args.get('realtime', 'true').lower() == 'true'
        
        # Parse dates
        if from_date_str:
            from_date = datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
        else:
            from_date = datetime.utcnow() - timedelta(days=30)
            
        if to_date_str:
            to_date = datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
        else:
            to_date = datetime.utcnow()
        
        # Generate dashboard data
        dashboard_data = reports_engine.generate_dashboard_data(
            from_date=from_date,
            to_date=to_date,
            include_realtime=include_realtime
        )
        
        return jsonify({
            'success': True,
            'data': dashboard_data,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate dashboard data'
        }), 500

@dynamic_reports_bp.route('/api/sales/analytics')
@login_required
@require_permission(Permissions.VIEW_REPORTS)
def api_sales_analytics():
    """Get detailed sales analytics"""
    try:
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        group_by = request.args.get('group_by', 'day')  # day, week, month
        chart_type = request.args.get('chart_type', 'line')
        
        # Parse dates
        if from_date_str:
            from_date = datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
        else:
            from_date = datetime.utcnow() - timedelta(days=30)
            
        if to_date_str:
            to_date = datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
        else:
            to_date = datetime.utcnow()
        
        # Get sales data
        sales_data = get_sales_analytics(from_date, to_date, group_by)
        
        # Generate chart configuration
        chart_config = generate_chart_config(chart_type, sales_data, 'Sales Analytics')
        
        return jsonify({
            'success': True,
            'data': sales_data,
            'chart_config': chart_config,
            'summary': generate_sales_summary(sales_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate sales analytics'
        }), 500

@dynamic_reports_bp.route('/api/inventory/analytics')
@login_required
@require_permission(Permissions.VIEW_INVENTORY)
def api_inventory_analytics():
    """Get inventory analytics and alerts"""
    try:
        # Get inventory data
        inventory_data = get_inventory_analytics()
        
        return jsonify({
            'success': True,
            'data': inventory_data,
            'alerts': get_inventory_alerts(),
            'summary': generate_inventory_summary(inventory_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate inventory analytics'
        }), 500

@dynamic_reports_bp.route('/api/orders/performance')
@login_required
@require_permission(Permissions.VIEW_ORDERS)
def api_order_performance():
    """Get order performance metrics"""
    try:
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        
        # Parse dates
        if from_date_str:
            from_date = datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
        else:
            from_date = datetime.utcnow() - timedelta(days=7)
            
        if to_date_str:
            to_date = datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
        else:
            to_date = datetime.utcnow()
        
        # Get order performance data
        performance_data = get_order_performance(from_date, to_date)
        
        return jsonify({
            'success': True,
            'data': performance_data,
            'trends': get_order_trends(from_date, to_date),
            'summary': generate_order_summary(performance_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate order performance data'
        }), 500

@dynamic_reports_bp.route('/api/revenue/breakdown')
@login_required
@require_permission(Permissions.VIEW_REPORTS)
def api_revenue_breakdown():
    """Get detailed revenue breakdown by categories, payment methods, etc."""
    try:
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        breakdown_type = request.args.get('type', 'category')  # category, payment_method, staff
        
        # Parse dates
        if from_date_str:
            from_date = datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
        else:
            from_date = datetime.utcnow() - timedelta(days=30)
            
        if to_date_str:
            to_date = datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
        else:
            to_date = datetime.utcnow()
        
        # Get revenue breakdown
        breakdown_data = get_revenue_breakdown(from_date, to_date, breakdown_type)
        
        return jsonify({
            'success': True,
            'data': breakdown_data,
            'breakdown_type': breakdown_type,
            'summary': generate_revenue_summary(breakdown_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate revenue breakdown'
        }), 500

@dynamic_reports_bp.route('/api/indian-food-analytics')
@login_required
@require_permission(Permissions.VIEW_REPORTS)
def api_indian_food_analytics():
    """Get Indian food specific analytics"""
    try:
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        
        # Parse dates
        if from_date_str:
            from_date = datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
        else:
            from_date = datetime.utcnow() - timedelta(days=30)
            
        if to_date_str:
            to_date = datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
        else:
            to_date = datetime.utcnow()
        
        # Get Indian food analytics
        indian_food_data = get_indian_food_analytics(from_date, to_date)
        
        return jsonify({
            'success': True,
            'data': indian_food_data,
            'insights': generate_indian_food_insights(indian_food_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate Indian food analytics'
        }), 500

@dynamic_reports_bp.route('/api/staff/performance')
@login_required
@require_permission(Permissions.VIEW_REPORTS)
def api_staff_performance():
    """Get staff performance analytics"""
    try:
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        
        # Parse dates
        if from_date_str:
            from_date = datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
        else:
            from_date = datetime.utcnow() - timedelta(days=30)
            
        if to_date_str:
            to_date = datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
        else:
            to_date = datetime.utcnow()
        
        # Get staff performance data
        staff_data = get_staff_performance(from_date, to_date)
        
        return jsonify({
            'success': True,
            'data': staff_data,
            'rankings': generate_staff_rankings(staff_data),
            'summary': generate_staff_summary(staff_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate staff performance data'
        }), 500

@dynamic_reports_bp.route('/api/export')
@login_required
@require_permission(Permissions.EXPORT_REPORTS)
def api_export_reports():
    """Export reports in various formats"""
    try:
        report_type = request.args.get('type', 'dashboard')
        format_type = request.args.get('format', 'json')  # json, csv, pdf
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        
        # Parse dates
        if from_date_str:
            from_date = datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
        else:
            from_date = datetime.utcnow() - timedelta(days=30)
            
        if to_date_str:
            to_date = datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
        else:
            to_date = datetime.utcnow()
        
        # Generate report data
        report_data = reports_engine.generate_dashboard_data(from_date, to_date)
        
        # Export in requested format
        if format_type == 'json':
            return json_export(report_data, report_type, from_date, to_date)
        elif format_type == 'csv':
            return csv_export(report_data, report_type, from_date, to_date)
        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported export format',
                'message': f'Format {format_type} is not supported'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to export report'
        }), 500

@dynamic_reports_bp.route('/api/realtime/stream')
@login_required
@require_permission(Permissions.VIEW_REPORTS)
def api_realtime_stream():
    """Get real-time data stream"""
    try:
        # This endpoint would typically use WebSocket
        # For now, return latest data
        realtime_data = reports_engine._get_realtime_metrics()
        
        return jsonify({
            'success': True,
            'data': realtime_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get real-time data'
        }), 500

# Helper Functions

def get_sales_analytics(from_date: datetime, to_date: datetime, group_by: str) -> Dict[str, Any]:
    """Get detailed sales analytics"""
    
    # Get completed orders in date range
    orders = Order.query.filter(
        Order.created_at >= from_date,
        Order.created_at <= to_date,
        Order.status == 'Completed'
    ).all()
    
    if group_by == 'day':
        return get_daily_sales(orders)
    elif group_by == 'week':
        return get_weekly_sales(orders)
    elif group_by == 'month':
        return get_monthly_sales(orders)
    else:
        return get_daily_sales(orders)

def get_daily_sales(orders) -> Dict[str, Any]:
    """Get daily sales breakdown"""
    daily_data = {}
    
    for order in orders:
        date_key = order.created_at.date().isoformat()
        if date_key not in daily_data:
            daily_data[date_key] = {
                'date': date_key,
                'orders': 0,
                'sales': 0.0,
                'avg_order_value': 0.0,
                'tax': 0.0
            }
        
        daily_data[date_key]['orders'] += 1
        daily_data[date_key]['sales'] += float(order.grand_total or 0)
        daily_data[date_key]['tax'] += float(order.total_tax or 0)
    
    # Calculate averages
    for date_key, data in daily_data.items():
        data['avg_order_value'] = data['sales'] / data['orders'] if data['orders'] > 0 else 0
    
    return {
        'type': 'daily',
        'data': list(daily_data.values()),
        'total_sales': sum(data['sales'] for data in daily_data.values()),
        'total_orders': sum(data['orders'] for data in daily_data.values())
    }

def get_weekly_sales(orders) -> Dict[str, Any]:
    """Get weekly sales breakdown"""
    # Implementation for weekly breakdown
    return get_daily_sales(orders)  # Simplified for now

def get_monthly_sales(orders) -> Dict[str, Any]:
    """Get monthly sales breakdown"""
    # Implementation for monthly breakdown
    return get_daily_sales(orders)  # Simplified for now

def get_inventory_analytics() -> Dict[str, Any]:
    """Get inventory analytics"""
    
    # Get all menu items
    items = MenuItem.query.filter_by(is_active=True).all()
    
    low_stock_items = []
    out_of_stock_items = []
    healthy_stock_items = []
    
    for item in items:
        stock_level = item.stock_quantity or 0
        min_level = item.min_stock_level or 0
        
        if stock_level <= 0:
            out_of_stock_items.append({
                'id': item.id,
                'name': item.name,
                'current_stock': stock_level,
                'category': item.category.name if item.category else 'Unknown'
            })
        elif stock_level <= min_level:
            low_stock_items.append({
                'id': item.id,
                'name': item.name,
                'current_stock': stock_level,
                'min_stock': min_level,
                'category': item.category.name if item.category else 'Unknown',
                'reorder_needed': min_level - stock_level
            })
        else:
            healthy_stock_items.append({
                'id': item.id,
                'name': item.name,
                'current_stock': stock_level,
                'min_stock': min_level,
                'category': item.category.name if item.category else 'Unknown'
            })
    
    return {
        'low_stock': low_stock_items,
        'out_of_stock': out_of_stock_items,
        'healthy_stock': healthy_stock_items,
        'total_items': len(items),
        'low_stock_count': len(low_stock_items),
        'out_of_stock_count': len(out_of_stock_items)
    }

def get_inventory_alerts() -> List[Dict[str, Any]]:
    """Get inventory alerts"""
    alerts = []
    
    low_stock_items = MenuItem.query.filter(
        MenuItem.stock_quantity <= MenuItem.min_stock_level,
        MenuItem.is_active == True
    ).all()
    
    if low_stock_items:
        alerts.append({
            'type': 'warning',
            'title': 'Low Stock Alert',
            'message': f'{len(low_stock_items)} items need restocking',
            'items': [item.name for item in low_stock_items[:5]],
            'count': len(low_stock_items)
        })
    
    return alerts

def get_order_performance(from_date: datetime, to_date: datetime) -> Dict[str, Any]:
    """Get order performance metrics"""
    
    orders = Order.query.filter(
        Order.created_at >= from_date,
        Order.created_at <= to_date
    ).all()
    
    # Calculate performance metrics
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o.status == 'Completed'])
    cancelled_orders = len([o for o in orders if o.status == 'Cancelled'])
    
    # Average completion time (simplified - would need actual timing data)
    avg_completion_time = 25  # minutes, placeholder
    
    return {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
        'cancellation_rate': (cancelled_orders / total_orders * 100) if total_orders > 0 else 0,
        'avg_completion_time': avg_completion_time,
        'orders_by_status': get_orders_by_status(orders)
    }

def get_orders_by_status(orders) -> Dict[str, int]:
    """Get order count by status"""
    status_counts = {}
    for order in orders:
        status = order.status
        status_counts[status] = status_counts.get(status, 0) + 1
    return status_counts

def get_revenue_breakdown(from_date: datetime, to_date: datetime, breakdown_type: str) -> Dict[str, Any]:
    """Get revenue breakdown by type"""
    
    orders = Order.query.filter(
        Order.created_at >= from_date,
        Order.created_at <= to_date,
        Order.status == 'Completed'
    ).all()
    
    if breakdown_type == 'category':
        return get_category_revenue_breakdown(orders)
    elif breakdown_type == 'payment_method':
        return get_payment_method_breakdown(orders)
    elif breakdown_type == 'staff':
        return get_staff_revenue_breakdown(orders)
    else:
        return get_category_revenue_breakdown(orders)

def get_category_revenue_breakdown(orders) -> Dict[str, Any]:
    """Get revenue breakdown by category"""
    category_revenue = {}
    
    for order in orders:
        for order_item in order.order_items:
            if order_item.menu_item and order_item.menu_item.category:
                category_name = order_item.menu_item.category.name
                if category_name not in category_revenue:
                    category_revenue[category_name] = 0
                category_revenue[category_name] += float(order_item.total or 0)
    
    # Convert to list format
    breakdown = [{'category': cat, 'revenue': revenue} for cat, revenue in category_revenue.items()]
    breakdown.sort(key=lambda x: x['revenue'], reverse=True)
    
    return {
        'type': 'category',
        'breakdown': breakdown,
        'total_revenue': sum(item['revenue'] for item in breakdown)
    }

def get_payment_method_breakdown(orders) -> Dict[str, Any]:
    """Get revenue breakdown by payment method"""
    payment_revenue = {}
    
    for order in orders:
        payments = Payment.get_completed_payments_by_order(order.id)
        for payment in payments:
            method = payment.payment_mode
            if method not in payment_revenue:
                payment_revenue[method] = 0
            payment_revenue[method] += float(payment.amount)
    
    # Convert to list format
    breakdown = [{'method': method, 'revenue': revenue} for method, revenue in payment_revenue.items()]
    breakdown.sort(key=lambda x: x['revenue'], reverse=True)
    
    return {
        'type': 'payment_method',
        'breakdown': breakdown,
        'total_revenue': sum(item['revenue'] for item in breakdown)
    }

def get_staff_revenue_breakdown(orders) -> Dict[str, Any]:
    """Get revenue breakdown by staff"""
    staff_revenue = {}
    
    for order in orders:
        if order.created_by:
            staff_id = order.created_by
            if staff_id not in staff_revenue:
                staff_revenue[staff_id] = 0
            staff_revenue[staff_id] += float(order.grand_total or 0)
    
    # Get staff names and convert to list format
    breakdown = []
    for staff_id, revenue in staff_revenue.items():
        user = User.query.get(staff_id)
        breakdown.append({
            'staff_id': staff_id,
            'staff_name': user.username if user else 'Unknown',
            'revenue': revenue
        })
    
    breakdown.sort(key=lambda x: x['revenue'], reverse=True)
    
    return {
        'type': 'staff',
        'breakdown': breakdown,
        'total_revenue': sum(item['revenue'] for item in breakdown)
    }

def get_indian_food_analytics(from_date: datetime, to_date: datetime) -> Dict[str, Any]:
    """Get Indian food specific analytics"""
    
    orders = Order.query.filter(
        Order.created_at >= from_date,
        Order.created_at <= to_date,
        Order.status == 'Completed'
    ).all()
    
    # Get Indian food items (simplified - would need proper categorization)
    indian_food_items = MenuItem.query.filter(
        MenuItem.category.has(Category.name.like('%Indian%')) |
        MenuItem.category.has(Category.name.like('%Curry%')) |
        MenuItem.category.has(Category.name.like('%Spice%'))
    ).all()
    
    spice_level_popularity = {}
    vegetarian_popularity = {}
    popular_dishes = {}
    
    for order in orders:
        for order_item in order.order_items:
            if order_item.menu_item:
                item = order_item.menu_item
                
                # Spice level analysis
                if item.spice_level:
                    spice_level_popularity[item.spice_level] = spice_level_popularity.get(item.spice_level, 0) + order_item.quantity
                
                # Vegetarian preference
                veg_status = 'Vegetarian' if item.is_vegetarian else 'Non-Vegetarian'
                vegetarian_popularity[veg_status] = vegetarian_popularity.get(veg_status, 0) + order_item.quantity
                
                # Popular dishes
                popular_dishes[item.name] = popular_dishes.get(item.name, 0) + order_item.quantity
    
    # Sort popular dishes
    top_dishes = sorted(popular_dishes.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'spice_level_popularity': spice_level_popularity,
        'vegetarian_preference': vegetarian_popularity,
        'top_dishes': [{'name': dish, 'orders': count} for dish, count in top_dishes],
        'total_indian_food_orders': len([o for o in orders if any(
            oi.menu_item in indian_food_items for oi in o.order_items
        )])
    }

def get_staff_performance(from_date: datetime, to_date: datetime) -> Dict[str, Any]:
    """Get staff performance analytics"""
    
    orders = Order.query.filter(
        Order.created_at >= from_date,
        Order.created_at <= to_date
    ).all()
    
    staff_performance = {}
    
    for order in orders:
        if order.created_by:
            staff_id = order.created_by
            if staff_id not in staff_performance:
                staff_performance[staff_id] = {
                    'orders': 0,
                    'sales': 0.0,
                    'completed': 0,
                    'cancelled': 0
                }
            
            staff_performance[staff_id]['orders'] += 1
            staff_performance[staff_id]['sales'] += float(order.grand_total or 0)
            
            if order.status == 'Completed':
                staff_performance[staff_id]['completed'] += 1
            elif order.status == 'Cancelled':
                staff_performance[staff_id]['cancelled'] += 1
    
    # Add staff names and calculate metrics
    performance_list = []
    for staff_id, stats in staff_performance.items():
        user = User.query.get(staff_id)
        if user:
            completion_rate = (stats['completed'] / stats['orders'] * 100) if stats['orders'] > 0 else 0
            performance_list.append({
                'staff_id': staff_id,
                'staff_name': user.username,
                'orders': stats['orders'],
                'sales': stats['sales'],
                'completed': stats['completed'],
                'cancelled': stats['cancelled'],
                'completion_rate': completion_rate,
                'avg_order_value': stats['sales'] / stats['orders'] if stats['orders'] > 0 else 0
            })
    
    performance_list.sort(key=lambda x: x['sales'], reverse=True)
    
    return {
        'staff_performance': performance_list,
        'total_staff': len(performance_list),
        'top_performer': performance_list[0] if performance_list else None
    }

def get_order_trends(from_date: datetime, to_date: datetime) -> Dict[str, Any]:
    """Get order trends over time"""
    
    # Get daily order trends
    daily_trends = []
    current_date = from_date.date()
    end_date = to_date.date()
    
    while current_date <= end_date:
        day_orders = Order.query.filter(
            db.func.date(Order.created_at) == current_date
        ).all()
        
        daily_trends.append({
            'date': current_date.isoformat(),
            'orders': len(day_orders),
            'completed': len([o for o in day_orders if o.status == 'Completed']),
            'cancelled': len([o for o in day_orders if o.status == 'Cancelled'])
        })
        
        current_date += timedelta(days=1)
    
    return {
        'daily_trends': daily_trends,
        'peak_day': max(daily_trends, key=lambda x: x['orders']) if daily_trends else None,
        'trend_direction': 'increasing' if len(daily_trends) > 1 and daily_trends[-1]['orders'] > daily_trends[0]['orders'] else 'decreasing'
    }

# Chart generation helpers
def generate_chart_config(chart_type: str, data: Dict[str, Any], title: str) -> Dict[str, Any]:
    """Generate Chart.js configuration"""
    return reports_engine.generate_chart_config(chart_type, data.get('data', []), title)

# Summary generators
def generate_sales_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate sales summary"""
    return {
        'total_sales': data.get('total_sales', 0),
        'total_orders': data.get('total_orders', 0),
        'avg_order_value': data.get('total_sales', 0) / data.get('total_orders', 1) if data.get('total_orders', 0) > 0 else 0
    }

def generate_inventory_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate inventory summary"""
    return {
        'total_items': data.get('total_items', 0),
        'low_stock_count': data.get('low_stock_count', 0),
        'out_of_stock_count': data.get('out_of_stock_count', 0),
        'health_percentage': ((data.get('total_items', 0) - data.get('low_stock_count', 0) - data.get('out_of_stock_count', 0)) / data.get('total_items', 1) * 100) if data.get('total_items', 0) > 0 else 0
    }

def generate_order_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate order summary"""
    return {
        'completion_rate': data.get('completion_rate', 0),
        'cancellation_rate': data.get('cancellation_rate', 0),
        'avg_completion_time': data.get('avg_completion_time', 0)
    }

def generate_revenue_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate revenue summary"""
    return {
        'total_revenue': data.get('total_revenue', 0),
        'top_category': data.get('breakdown', [{}])[0].get('category', 'N/A') if data.get('breakdown') else 'N/A'
    }

def generate_indian_food_insights(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Indian food insights"""
    spice_prefs = data.get('spice_level_popularity', {})
    top_spice = max(spice_prefs.items(), key=lambda x: x[1])[0] if spice_prefs else 'Unknown'
    
    return {
        'most_popular_spice_level': top_spice,
        'vegetarian_preference': data.get('vegetarian_preference', {}),
        'total_orders': data.get('total_indian_food_orders', 0)
    }

def generate_staff_rankings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate staff performance rankings"""
    staff_list = data.get('staff_performance', [])
    
    return {
        'top_sales': staff_list[0] if staff_list else None,
        'top_completion_rate': max(staff_list, key=lambda x: x.get('completion_rate', 0)) if staff_list else None,
        'total_staff': len(staff_list)
    }

def generate_staff_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate staff summary"""
    staff_list = data.get('staff_performance', [])
    total_sales = sum(staff.get('sales', 0) for staff in staff_list)
    
    return {
        'total_sales': total_sales,
        'total_staff': len(staff_list),
        'avg_sales_per_staff': total_sales / len(staff_list) if staff_list else 0
    }

# Export functions
def json_export(data: Dict[str, Any], report_type: str, from_date: datetime, to_date: datetime):
    """Export report as JSON"""
    export_data = {
        'report_type': report_type,
        'generated_at': datetime.utcnow().isoformat(),
        'date_range': {
            'from': from_date.isoformat(),
            'to': to_date.isoformat()
        },
        'data': data
    }
    
    output = io.BytesIO(json.dumps(export_data, indent=2, default=str).encode('utf-8'))
    filename = f"{report_type}_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.json"
    
    return send_file(
        output,
        filename=filename,
        as_attachment=True,
        mimetype='application/json'
    )

def csv_export(data: Dict[str, Any], report_type: str, from_date: datetime, to_date: datetime):
    """Export report as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Report Type', 'Generated At', 'From Date', 'To Date'])
    writer.writerow([report_type, datetime.utcnow().isoformat(), from_date.isoformat(), to_date.isoformat()])
    writer.writerow([])
    
    # Write data summary (simplified)
    if 'overview' in data:
        writer.writerow(['Metric', 'Value'])
        for key, value in data['overview'].items():
            writer.writerow([key, value])
    
    output.seek(0)
    filename = f"{report_type}_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        filename=filename,
        as_attachment=True,
        mimetype='text/csv'
    )