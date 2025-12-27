"""
Dynamic Reports Engine for Restaurant POS System
Core report generation engine with Chart.js integration and real-time capabilities
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import logging

from models import db, Order, Payment, MenuItem, Category, User, Table, AuditLog
from utils.cache_manager import MultiLevelCache, get_cache_manager

class DynamicReportsEngine:
    """Core engine for generating dynamic reports with interactive visualizations"""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.logger = logging.getLogger(__name__)
        
        # Chart color palettes
        self.color_palettes = {
            'primary': ['#667EEA', '#764BA2', '#F093FB', '#F5576C'],
            'success': ['#48BB78', '#38A169', '#2F855A', '#276749'],
            'warning': ['#ED8936', '#DD6B20', '#C05621', '#9C4221'],
            'danger': ['#F56565', '#E53E3E', '#C53030', '#9B2C2C'],
            'info': ['#4299E1', '#3182CE', '#2B6CB0', '#2C5282'],
            'rainbow': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3']
        }
    
    def generate_dashboard_data(self, 
                              from_date: datetime = None, 
                              to_date: datetime = None,
                              include_realtime: bool = True) -> Dict[str, Any]:
        """Generate comprehensive dashboard data with real-time updates"""
        
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=30)
        if not to_date:
            to_date = datetime.utcnow()
        
        # Check cache first
        cache_key = f"dashboard_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}"
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        # Generate fresh data
        dashboard_data = {
            'overview': self._get_overview_stats(from_date, to_date),
            'trends': self._get_trend_data(from_date, to_date),
            'categories': self._get_category_analysis(from_date, to_date),
            'payment_methods': self._get_payment_breakdown(from_date, to_date),
            'staff_performance': self._get_staff_metrics(from_date, to_date),
            'time_series': self._get_time_series_data(from_date, to_date),
            'real_time': self._get_realtime_metrics() if include_realtime else {},
            'alerts': self._get_business_alerts(),
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Cache for 5 minutes
        self.cache_manager.set(cache_key, dashboard_data, timeout=300)
        
        # Send WebSocket update
        self.websocket_manager.broadcast('dashboard_update', dashboard_data)
        
        return dashboard_data
    
    def _get_overview_stats(self, from_date: datetime, to_date: datetime) -> Dict[str, Any]:
        """Get overall business statistics"""
        
        # Get orders in date range
        orders = Order.query.filter(
            Order.created_at >= from_date,
            Order.created_at <= to_date
        ).all()
        
        # Calculate key metrics
        total_sales = sum(order.grand_total or 0 for order in orders)
        total_orders = len(orders)
        completed_orders = len([o for o in orders if o.status == 'Completed'])
        cancelled_orders = len([o for o in orders if o.status == 'Cancelled'])
        
        # Calculate average order value
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        
        # Calculate growth rates
        previous_period = self._calculate_growth_rates(from_date, to_date)
        
        return {
            'total_sales': float(total_sales),
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
            'cancelled_rate': (cancelled_orders / total_orders * 100) if total_orders > 0 else 0,
            'average_order_value': float(avg_order_value),
            'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
            'growth': {
                'sales': previous_period['sales_growth'],
                'orders': previous_period['orders_growth'],
                'aov': previous_period['aov_growth']
            }
        }
    
    def _get_trend_data(self, from_date: datetime, to_date: datetime) -> Dict[str, Any]:
        """Get trend analysis data for charts"""
        
        # Daily trend data
        daily_data = []
        current_date = from_date.date()
        end_date = to_date.date()
        
        while current_date <= end_date:
            day_orders = Order.query.filter(
                db.func.date(Order.created_at) == current_date
            ).all()
            
            day_sales = sum(order.grand_total or 0 for order in day_orders)
            day_orders_count = len(day_orders)
            day_completed = len([o for o in day_orders if o.status == 'Completed'])
            
            daily_data.append({
                'date': current_date.isoformat(),
                'sales': float(day_sales),
                'orders': day_orders_count,
                'completed': day_completed,
                'cancelled': day_orders_count - day_completed
            })
            
            current_date += timedelta(days=1)
        
        # Hourly patterns (for today)
        hourly_data = []
        today = datetime.utcnow().date()
        
        for hour in range(24):
            hour_orders = Order.query.filter(
                db.func.date(Order.created_at) == today,
                db.func.extract('hour', Order.created_at) == hour
            ).all()
            
            hour_sales = sum(order.grand_total or 0 for order in hour_orders)
            hourly_data.append({
                'hour': hour,
                'sales': float(hour_sales),
                'orders': len(hour_orders)
            })
        
        return {
            'daily_trend': daily_data,
            'hourly_pattern': hourly_data,
            'weekly_comparison': self._get_weekly_comparison(from_date, to_date)
        }
    
    def _get_category_analysis(self, from_date: datetime, to_date: datetime) -> Dict[str, Any]:
        """Get category-wise sales analysis"""
        
        # Get orders with items
        orders = Order.query.filter(
            Order.created_at >= from_date,
            Order.created_at <= to_date,
            Order.status == 'Completed'
        ).all()
        
        category_stats = defaultdict(lambda: {
            'sales': 0, 'quantity': 0, 'orders': 0, 'items': set()
        })
        
        for order in orders:
            for order_item in order.order_items:
                if order_item.menu_item and order_item.menu_item.category:
                    category_name = order_item.menu_item.category.name
                    category_stats[category_name]['sales'] += float(order_item.total or 0)
                    category_stats[category_name]['quantity'] += order_item.quantity or 0
                    category_stats[category_name]['orders'] += 1
                    category_stats[category_name]['items'].add(order_item.menu_item.name)
        
        # Convert to list format
        categories = []
        for name, stats in category_stats.items():
            categories.append({
                'name': name,
                'sales': stats['sales'],
                'quantity': stats['quantity'],
                'orders': stats['orders'],
                'items_count': len(stats['items']),
                'avg_price': stats['sales'] / stats['quantity'] if stats['quantity'] > 0 else 0
            })
        
        # Sort by sales
        categories.sort(key=lambda x: x['sales'], reverse=True)
        
        return {
            'categories': categories,
            'top_performers': categories[:5],
            'underperformers': categories[-5:] if len(categories) > 5 else []
        }
    
    def _get_payment_breakdown(self, from_date: datetime, to_date: datetime) -> Dict[str, Any]:
        """Get payment method breakdown"""
        
        orders = Order.query.filter(
            Order.created_at >= from_date,
            Order.created_at <= to_date,
            Order.status == 'Completed'
        ).all()
        
        payment_stats = defaultdict(lambda: {'count': 0, 'amount': 0})
        
        for order in orders:
            payments = Payment.get_completed_payments_by_order(order.id)
            for payment in payments:
                payment_stats[payment.payment_mode]['count'] += 1
                payment_stats[payment.payment_mode]['amount'] += float(payment.amount)
        
        # Convert to list
        payment_methods = []
        for method, stats in payment_stats.items():
            payment_methods.append({
                'method': method,
                'count': stats['count'],
                'amount': stats['amount'],
                'percentage': (stats['amount'] / sum(s['amount'] for s in payment_stats.values()) * 100) 
                             if payment_stats else 0
            })
        
        payment_methods.sort(key=lambda x: x['amount'], reverse=True)
        
        return {
            'methods': payment_methods,
            'preferred_method': payment_methods[0]['method'] if payment_methods else 'N/A',
            'digital_percentage': self._calculate_digital_percentage(payment_methods)
        }
    
    def _get_staff_metrics(self, from_date: datetime, to_date: datetime) -> Dict[str, Any]:
        """Get staff performance metrics"""
        
        orders = Order.query.filter(
            Order.created_at >= from_date,
            Order.created_at <= to_date
        ).all()
        
        staff_stats = defaultdict(lambda: {
            'orders': 0, 'sales': 0, 'completed': 0, 'cancelled': 0
        })
        
        for order in orders:
            if order.created_by:
                staff_id = order.created_by
                staff_stats[staff_id]['orders'] += 1
                staff_stats[staff_id]['sales'] += float(order.grand_total or 0)
                
                if order.status == 'Completed':
                    staff_stats[staff_id]['completed'] += 1
                elif order.status == 'Cancelled':
                    staff_stats[staff_id]['cancelled'] += 1
        
        # Get staff details
        staff_performance = []
        for staff_id, stats in staff_stats.items():
            user = User.query.get(staff_id)
            if user:
                completion_rate = (stats['completed'] / stats['orders'] * 100) if stats['orders'] > 0 else 0
                staff_performance.append({
                    'staff_id': staff_id,
                    'name': user.username,
                    'email': user.email,
                    'orders': stats['orders'],
                    'sales': stats['sales'],
                    'completed': stats['completed'],
                    'cancelled': stats['cancelled'],
                    'completion_rate': completion_rate,
                    'avg_order_value': stats['sales'] / stats['orders'] if stats['orders'] > 0 else 0
                })
        
        staff_performance.sort(key=lambda x: x['sales'], reverse=True)
        
        return {
            'staff': staff_performance,
            'top_performer': staff_performance[0] if staff_performance else None,
            'team_size': len(staff_performance)
        }
    
    def _get_time_series_data(self, from_date: datetime, to_date: datetime) -> Dict[str, Any]:
        """Get time series data for advanced charts"""
        
        # Weekly data
        weekly_data = []
        current_date = from_date
        while current_date <= to_date:
            week_end = min(current_date + timedelta(days=6), to_date)
            
            week_orders = Order.query.filter(
                Order.created_at >= current_date,
                Order.created_at <= week_end
            ).all()
            
            week_sales = sum(order.grand_total or 0 for order in week_orders)
            
            weekly_data.append({
                'week_start': current_date.date().isoformat(),
                'week_end': week_end.date().isoformat(),
                'sales': float(week_sales),
                'orders': len(week_orders)
            })
            
            current_date += timedelta(days=7)
        
        # Monthly aggregation
        monthly_data = []
        month_start = from_date.replace(day=1)
        
        while month_start <= to_date:
            month_end = (month_start.replace(month=month_start.month % 12 + 1, day=1) 
                        if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1, day=1)) - timedelta(days=1)
            month_end = min(month_end, to_date)
            
            month_orders = Order.query.filter(
                Order.created_at >= month_start,
                Order.created_at <= month_end
            ).all()
            
            month_sales = sum(order.grand_total or 0 for order in month_orders)
            
            monthly_data.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%B %Y'),
                'sales': float(month_sales),
                'orders': len(month_orders),
                'avg_daily': float(month_sales / (month_end - month_start).days) if (month_end - month_start).days > 0 else 0
            })
            
            if month_start.month == 12:
                month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                month_start = month_start.replace(month=month_start.month + 1, day=1)
        
        return {
            'weekly': weekly_data,
            'monthly': monthly_data
        }
    
    def _get_realtime_metrics(self) -> Dict[str, Any]:
        """Get real-time business metrics"""
        
        now = datetime.utcnow()
        today = now.date()
        
        # Today's metrics
        today_orders = Order.query.filter(
            db.func.date(Order.created_at) == today
        ).all()
        
        today_sales = sum(order.grand_total or 0 for order in today_orders)
        today_orders_count = len(today_orders)
        
        # Active orders
        active_orders = Order.query.filter(
            Order.status.in_(['New', 'In Progress', 'Ready'])
        ).count()
        
        # Low stock items
        low_stock_items = MenuItem.query.filter(
            MenuItem.stock_quantity <= MenuItem.min_stock_level,
            MenuItem.is_active == True
        ).count()
        
        # Recent activity (last hour)
        hour_ago = now - timedelta(hours=1)
        recent_orders = Order.query.filter(
            Order.created_at >= hour_ago
        ).count()
        
        return {
            'today_sales': float(today_sales),
            'today_orders': today_orders_count,
            'active_orders': active_orders,
            'low_stock_items': low_stock_items,
            'recent_orders': recent_orders,
            'last_updated': now.isoformat()
        }
    
    def _get_business_alerts(self) -> List[Dict[str, Any]]:
        """Get business alerts and recommendations"""
        
        alerts = []
        now = datetime.utcnow()
        
        # Low stock alert
        low_stock_items = MenuItem.query.filter(
            MenuItem.stock_quantity <= MenuItem.min_stock_level,
            MenuItem.is_active == True
        ).all()
        
        if low_stock_items:
            alerts.append({
                'type': 'warning',
                'title': 'Low Stock Alert',
                'message': f'{len(low_stock_items)} items are running low on stock',
                'items': [item.name for item in low_stock_items[:5]],
                'action_url': '/inventory'
            })
        
        # High cancellation rate alert
        today = now.date()
        today_orders = Order.query.filter(db.func.date(Order.created_at) == today).all()
        
        if today_orders:
            cancelled_count = len([o for o in today_orders if o.status == 'Cancelled'])
            cancellation_rate = cancelled_count / len(today_orders) * 100
            
            if cancellation_rate > 15:  # More than 15% cancellation rate
                alerts.append({
                    'type': 'error',
                    'title': 'High Cancellation Rate',
                    'message': f'Cancellation rate is {cancellation_rate:.1f}% today',
                    'action_url': '/orders'
                })
        
        return alerts
    
    def _calculate_growth_rates(self, from_date: datetime, to_date: datetime) -> Dict[str, float]:
        """Calculate growth rates compared to previous period"""
        
        period_days = (to_date - from_date).days + 1
        
        # Previous period
        prev_to_date = from_date - timedelta(days=1)
        prev_from_date = prev_to_date - timedelta(days=period_days - 1)
        
        # Current period stats
        current_orders = Order.query.filter(
            Order.created_at >= from_date,
            Order.created_at <= to_date
        ).all()
        
        current_sales = sum(order.grand_total or 0 for order in current_orders)
        current_orders_count = len(current_orders)
        current_aov = current_sales / current_orders_count if current_orders_count > 0 else 0
        
        # Previous period stats
        prev_orders = Order.query.filter(
            Order.created_at >= prev_from_date,
            Order.created_at <= prev_to_date
        ).all()
        
        prev_sales = sum(order.grand_total or 0 for order in prev_orders)
        prev_orders_count = len(prev_orders)
        prev_aov = prev_sales / prev_orders_count if prev_orders_count > 0 else 0
        
        # Calculate growth percentages
        sales_growth = ((current_sales - prev_sales) / prev_sales * 100) if prev_sales > 0 else 0
        orders_growth = ((current_orders_count - prev_orders_count) / prev_orders_count * 100) if prev_orders_count > 0 else 0
        aov_growth = ((current_aov - prev_aov) / prev_aov * 100) if prev_aov > 0 else 0
        
        return {
            'sales_growth': round(sales_growth, 1),
            'orders_growth': round(orders_growth, 1),
            'aov_growth': round(aov_growth, 1)
        }
    
    def _get_weekly_comparison(self, from_date: datetime, to_date: datetime) -> Dict[str, Any]:
        """Get week-over-week comparison data"""
        
        # Current week
        current_week_start = from_date.date()
        current_week_end = min(current_week_start + timedelta(days=6), to_date.date())
        
        current_week_orders = Order.query.filter(
            db.func.date(Order.created_at) >= current_week_start,
            db.func.date(Order.created_at) <= current_week_end
        ).all()
        
        current_week_sales = sum(order.grand_total or 0 for order in current_week_orders)
        
        # Previous week
        prev_week_start = current_week_start - timedelta(days=7)
        prev_week_end = current_week_start - timedelta(days=1)
        
        prev_week_orders = Order.query.filter(
            db.func.date(Order.created_at) >= prev_week_start,
            db.func.date(Order.created_at) <= prev_week_end
        ).all()
        
        prev_week_sales = sum(order.grand_total or 0 for order in prev_week_orders)
        
        # Calculate growth
        week_growth = ((current_week_sales - prev_week_sales) / prev_week_sales * 100) if prev_week_sales > 0 else 0
        
        return {
            'current_week': {
                'sales': float(current_week_sales),
                'orders': len(current_week_orders)
            },
            'previous_week': {
                'sales': float(prev_week_sales),
                'orders': len(prev_week_orders)
            },
            'growth': round(week_growth, 1)
        }
    
    def _calculate_digital_percentage(self, payment_methods: List[Dict]) -> float:
        """Calculate percentage of digital payments"""
        
        digital_methods = ['UPI', 'Card', 'Net Banking', 'Digital Wallet']
        digital_amount = sum(method['amount'] for method in payment_methods 
                           if method['method'] in digital_methods)
        total_amount = sum(method['amount'] for method in payment_methods)
        
        return (digital_amount / total_amount * 100) if total_amount > 0 else 0
    
    def generate_chart_config(self, chart_type: str, data: List[Dict], title: str = "") -> Dict[str, Any]:
        """Generate Chart.js configuration for different chart types"""
        
        config = {
            'type': chart_type,
            'data': {
                'labels': [],
                'datasets': []
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'title': {
                        'display': bool(title),
                        'text': title
                    },
                    'legend': {
                        'display': True,
                        'position': 'top'
                    },
                    'tooltip': {
                        'enabled': True,
                        'mode': 'index',
                        'intersect': False
                    }
                },
                'interaction': {
                    'mode': 'nearest',
                    'axis': 'x',
                    'intersect': False
                }
            }
        }
        
        if chart_type in ['line', 'bar']:
            config['options']['scales'] = {
                'x': {
                    'display': True,
                    'title': {
                        'display': True,
                        'text': 'Time Period'
                    }
                },
                'y': {
                    'display': True,
                    'title': {
                        'display': True,
                        'text': 'Value'
                    },
                    'beginAtZero': True
                }
            }
        
        return config
    
    def export_report_data(self, report_data: Dict[str, Any], format: str = 'json') -> Any:
        """Export report data in various formats"""
        
        if format == 'json':
            return json.dumps(report_data, indent=2, default=str)
        
        elif format == 'csv':
            # Convert to CSV format
            csv_lines = []
            
            # Add overview stats
            if 'overview' in report_data:
                csv_lines.append("Metric,Value")
                for key, value in report_data['overview'].items():
                    csv_lines.append(f"{key},{value}")
            
            return "\n".join(csv_lines)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_report_summary(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the report data"""
        
        summary = {
            'total_sales': 0,
            'total_orders': 0,
            'top_category': 'N/A',
            'peak_day': 'N/A',
            'avg_order_value': 0,
            'completion_rate': 0,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        if 'overview' in report_data:
            overview = report_data['overview']
            summary.update({
                'total_sales': overview.get('total_sales', 0),
                'total_orders': overview.get('total_orders', 0),
                'avg_order_value': overview.get('average_order_value', 0),
                'completion_rate': overview.get('completion_rate', 0)
            })
        
        if 'categories' in report_data and 'categories' in report_data['categories']:
            categories = report_data['categories']['categories']
            if categories:
                summary['top_category'] = categories[0]['name']
        
        if 'trends' in report_data and 'daily_trend' in report_data['trends']:
            daily_trend = report_data['trends']['daily_trend']
            if daily_trend:
                peak_day = max(daily_trend, key=lambda x: x['sales'])
                summary['peak_day'] = peak_day['date']
        
        return summary