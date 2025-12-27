from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
from sqlalchemy import func, desc

from models import db, AnalyticsData, TrendAnalysis, PredictiveModel, CustomerInsights, BusinessMetrics, Order, MenuItem, Category
from utils.analytics_pipeline import analytics_pipeline
from utils.predictive_analytics import predictive_analytics

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/')
@login_required
def analytics_dashboard():
    """Main analytics dashboard"""
    if not current_user.is_manager():
        flash('Access denied. Manager role required.', 'error')
        return redirect(url_for('dashboard.index'))
    
    return render_template('analytics/dashboard.html')

@analytics_bp.route('/api/realtime-data')
@login_required
def get_realtime_data():
    """Get real-time analytics data"""
    try:
        data = analytics_pipeline.get_real_time_dashboard_data()
        return jsonify({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/sales-trends')
@login_required
def get_sales_trends():
    """Get sales trend analysis"""
    try:
        # Get time period from request
        period = request.args.get('period', '30')  # days
        try:
            days = int(period)
        except ValueError:
            days = 30
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get trend data
        trends = TrendAnalysis.query.filter_by(
            trend_type='sales_growth',
            is_active=True
        ).filter(
            TrendAnalysis.trend_start_date >= start_date
        ).order_by(desc(TrendAnalysis.computed_at)).all()
        
        # Get raw sales data for charting
        sales_data = AnalyticsData.query.filter(
            AnalyticsData.metric_type == 'sales',
            AnalyticsData.metric_name == 'daily_revenue',
            AnalyticsData.period_start >= start_date,
            AnalyticsData.period_end <= end_date
        ).order_by(AnalyticsData.period_start).all()
        
        trends_data = []
        for trend in trends:
            trends_data.append({
                'trend_name': trend.trend_name,
                'trend_direction': trend.trend_direction,
                'trend_strength': trend.trend_strength,
                'trend_slope': trend.trend_slope,
                'r_squared': trend.r_squared,
                'data_points': trend.data_points_list,
                'algorithm_used': trend.algorithm_used,
                'computed_at': trend.computed_at.isoformat()
            })
        
        chart_data = []
        for data in sales_data:
            chart_data.append({
                'date': data.period_start.strftime('%Y-%m-%d'),
                'revenue': float(data.metric_value),
                'period': data.period_start.strftime('%Y-%m-%d')
            })
        
        return jsonify({
            'success': True,
            'trends': trends_data,
            'chart_data': chart_data,
            'summary': {
                'total_revenue': sum(float(d.metric_value) for d in sales_data),
                'average_daily': sum(float(d.metric_value) for d in sales_data) / len(sales_data) if sales_data else 0,
                'best_day': max(sales_data, key=lambda x: float(x.metric_value)).period_start.strftime('%Y-%m-%d') if sales_data else None,
                'trend_summary': trends_data[0] if trends_data else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/predictive-analytics')
@login_required
def get_predictive_analytics():
    """Get predictive analytics and forecasting"""
    try:
        # Generate comprehensive insights
        insights = predictive_analytics.generate_insights_report()
        
        return jsonify({
            'success': True,
            'insights': insights
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/customer-insights')
@login_required
def get_customer_insights():
    """Get customer analytics and segmentation"""
    try:
        # Get customer segmentation data
        customers = CustomerInsights.query.all()
        
        if not customers:
            return jsonify({
                'success': True,
                'data': {
                    'total_customers': 0,
                    'segments': [],
                    'top_customers': [],
                    'insights': []
                }
            })
        
        # Calculate customer metrics
        total_customers = len(customers)
        total_revenue = sum(float(c.customer_lifetime_value) for c in customers)
        
        # Customer segments
        segments = {}
        for customer in customers:
            segment = customer.customer_segment
            if segment not in segments:
                segments[segment] = {
                    'count': 0,
                    'total_clv': 0,
                    'avg_clv': 0,
                    'avg_frequency': 0,
                    'avg_loyalty': 0
                }
            
            segments[segment]['count'] += 1
            segments[segment]['total_clv'] += float(customer.customer_lifetime_value)
            segments[segment]['avg_frequency'] += customer.frequency_count
            segments[segment]['avg_loyalty'] += customer.loyalty_score
        
        # Calculate segment averages
        for segment in segments:
            count = segments[segment]['count']
            segments[segment]['avg_clv'] = segments[segment]['total_clv'] / count
            segments[segment]['avg_frequency'] = segments[segment]['avg_frequency'] / count
            segments[segment]['avg_loyalty'] = segments[segment]['avg_loyalty'] / count
            segments[segment]['percentage'] = (count / total_customers) * 100
        
        # Top customers
        top_customers = sorted(customers, key=lambda x: float(x.customer_lifetime_value), reverse=True)[:10]
        top_customers_data = []
        for customer in top_customers:
            top_customers_data.append({
                'id': customer.id,
                'customer_segment': customer.customer_segment,
                'customer_lifetime_value': float(customer.customer_lifetime_value),
                'frequency_count': customer.frequency_count,
                'loyalty_score': customer.loyalty_score,
                'last_visit': customer.last_visit_date.strftime('%Y-%m-%d') if customer.last_visit_date else None
            })
        
        # RFM Analysis
        rfm_analysis = {
            'high_value': len([c for c in customers if c.customer_segment == 'VIP']),
            'frequent': len([c for c in customers if c.frequency_count >= 10]),
            'recent': len([c for c in customers if c.recency_days and c.recency_days <= 7]),
            'at_risk': len([c for c in customers if c.churn_risk_score >= 0.7])
        }
        
        return jsonify({
            'success': True,
            'data': {
                'total_customers': total_customers,
                'total_revenue': total_revenue,
                'segments': segments,
                'top_customers': top_customers_data,
                'rfm_analysis': rfm_analysis,
                'customer_metrics': {
                    'avg_clv': total_revenue / total_customers if total_customers > 0 else 0,
                    'avg_frequency': sum(c.frequency_count for c in customers) / total_customers if total_customers > 0 else 0,
                    'avg_loyalty': sum(c.loyalty_score for c in customers) / total_customers if total_customers > 0 else 0
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/menu-analytics')
@login_required
def get_menu_analytics():
    """Get menu item performance analytics"""
    try:
        # Get menu item sales data
        menu_sales = AnalyticsData.query.filter(
            AnalyticsData.metric_type == 'sales',
            AnalyticsData.metric_name == 'daily_item_sales'
        ).order_by(desc(AnalyticsData.metric_value)).limit(50).all()
        
        # Get menu item quantities
        menu_quantities = AnalyticsData.query.filter(
            AnalyticsData.metric_type == 'orders',
            AnalyticsData.metric_name == 'daily_item_quantity'
        ).order_by(desc(AnalyticsData.metric_value)).limit(50).all()
        
        # Group by menu item
        item_performance = {}
        
        for data in menu_sales:
            if data.menu_item_id:
                if data.menu_item_id not in item_performance:
                    item_performance[data.menu_item_id] = {
                        'menu_item': data.menu_item,
                        'total_revenue': 0,
                        'total_quantity': 0,
                        'avg_daily_revenue': 0,
                        'performance_score': 0
                    }
                
                item_performance[data.menu_item_id]['total_revenue'] += float(data.metric_value)
        
        for data in menu_quantities:
            if data.menu_item_id and data.menu_item_id in item_performance:
                item_performance[data.menu_item_id]['total_quantity'] += float(data.metric_value)
        
        # Calculate performance scores
        for item_id, performance in item_performance.items():
            # Simple performance score: revenue * quantity normalized
            revenue = performance['total_revenue']
            quantity = performance['total_quantity']
            
            if quantity > 0:
                performance['avg_daily_revenue'] = revenue / quantity
                performance['performance_score'] = (revenue * quantity) / 1000  # Normalized score
            
            # Sort by performance score
        top_items = sorted(item_performance.values(), key=lambda x: x['performance_score'], reverse=True)[:20]
        
        # Convert to JSON-serializable format
        top_items_data = []
        for item in top_items:
            top_items_data.append({
                'name': item['menu_item'].name if item['menu_item'] else 'Unknown',
                'category': item['menu_item'].category.name if item['menu_item'] and item['menu_item'].category else 'Unknown',
                'total_revenue': item['total_revenue'],
                'total_quantity': item['total_quantity'],
                'avg_daily_revenue': item['avg_daily_revenue'],
                'performance_score': item['performance_score']
            })
        
        return jsonify({
            'success': True,
            'data': {
                'top_performing_items': top_items_data,
                'total_items_analyzed': len(item_performance)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/business-metrics')
@login_required
def get_business_metrics():
    """Get key business performance metrics"""
    try:
        # Get business metrics
        metrics = BusinessMetrics.query.filter_by(
            is_monitoring_enabled=True
        ).order_by(desc(BusinessMetrics.calculated_at)).limit(20).all()
        
        # Group by category
        metrics_by_category = {}
        for metric in metrics:
            category = metric.metric_category
            if category not in metrics_by_category:
                metrics_by_category[category] = []
            
            metrics_by_category[category].append(metric.get_performance_summary())
        
        # Get critical alerts
        critical_metrics = BusinessMetrics.get_critical_metrics()
        alerts = []
        for metric in critical_metrics:
            alerts.append({
                'metric_name': metric.metric_name,
                'current_value': float(metric.current_value),
                'target_value': float(metric.target_value) if metric.target_value else None,
                'percentage_change': metric.percentage_change,
                'status': metric.status,
                'period': f"{metric.period_start.strftime('%Y-%m-%d')} to {metric.period_end.strftime('%Y-%m-%d')}"
            })
        
        return jsonify({
            'success': True,
            'data': {
                'metrics_by_category': metrics_by_category,
                'alerts': alerts,
                'summary': {
                    'total_metrics': len(metrics),
                    'critical_alerts': len(critical_metrics),
                    'categories': list(metrics_by_category.keys())
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/anomalies')
@login_required
def get_anomalies():
    """Get anomaly detection results"""
    try:
        anomalies = predictive_analytics.identify_anomalies(days=30)
        
        return jsonify({
            'success': True,
            'data': {
                'anomalies': anomalies,
                'summary': {
                    'total_anomalies': len(anomalies),
                    'high_anomalies': len([a for a in anomalies if a['anomaly_type'] == 'high']),
                    'low_anomalies': len([a for a in anomalies if a['anomaly_type'] == 'low'])
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/staff-performance')
@login_required
def get_staff_performance():
    """Get staff performance analytics"""
    try:
        # Get staff sales data
        staff_sales = AnalyticsData.query.filter(
            AnalyticsData.metric_type == 'sales',
            AnalyticsData.metric_name == 'daily_staff_sales'
        ).filter(
            AnalyticsData.period_start >= datetime.now() - timedelta(days=30)
        ).all()
        
        # Group by user
        staff_performance = {}
        
        for data in staff_sales:
            if data.user_id:
                if data.user_id not in staff_performance:
                    staff_performance[data.user_id] = {
                        'user': data.user,
                        'total_sales': 0,
                        'total_orders': 0,
                        'avg_daily_sales': 0,
                        'days_worked': 0
                    }
                
                staff_performance[data.user_id]['total_sales'] += float(data.metric_value)
                staff_performance[data.user_id]['days_worked'] += 1
        
        # Get staff order counts
        staff_orders = AnalyticsData.query.filter(
            AnalyticsData.metric_type == 'orders',
            AnalyticsData.metric_name == 'daily_staff_orders'
        ).filter(
            AnalyticsData.period_start >= datetime.now() - timedelta(days=30)
        ).all()
        
        for data in staff_orders:
            if data.user_id and data.user_id in staff_performance:
                staff_performance[data.user_id]['total_orders'] += float(data.metric_value)
        
        # Calculate averages and performance scores
        staff_data = []
        for user_id, performance in staff_performance.items():
            if performance['days_worked'] > 0:
                performance['avg_daily_sales'] = performance['total_sales'] / performance['days_worked']
                performance['avg_orders_per_day'] = performance['total_orders'] / performance['days_worked']
                
                # Calculate performance score
                sales_score = performance['avg_daily_sales'] / 1000  # Normalize
                order_score = performance['avg_orders_per_day']
                performance['performance_score'] = (sales_score + order_score) / 2
                
                staff_data.append({
                    'name': performance['user'].full_name or performance['user'].username,
                    'role': performance['user'].role,
                    'total_sales': performance['total_sales'],
                    'total_orders': performance['total_orders'],
                    'avg_daily_sales': performance['avg_daily_sales'],
                    'avg_orders_per_day': performance['avg_orders_per_day'],
                    'days_worked': performance['days_worked'],
                    'performance_score': performance['performance_score']
                })
        
        # Sort by performance score
        staff_data.sort(key=lambda x: x['performance_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'staff_performance': staff_data,
                'summary': {
                    'total_staff': len(staff_data),
                    'avg_performance': sum(s['performance_score'] for s in staff_data) / len(staff_data) if staff_data else 0
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/export/<format>')
@login_required
def export_analytics(format):
    """Export analytics data"""
    try:
        if format == 'json':
            # Get all analytics data
            analytics_data = {
                'sales_trends': [],
                'customer_insights': [],
                'business_metrics': [],
                'generated_at': datetime.now().isoformat()
            }
            
            # Get sales trends
            trends = TrendAnalysis.query.all()
            for trend in trends:
                analytics_data['sales_trends'].append(trend.to_dict())
            
            # Get customer insights
            customers = CustomerInsights.query.all()
            for customer in customers:
                analytics_data['customer_insights'].append(customer.to_dict())
            
            # Get business metrics
            metrics = BusinessMetrics.query.all()
            for metric in metrics:
                analytics_data['business_metrics'].append(metric.to_dict())
            
            return jsonify(analytics_data)
        
        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported export format'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/refresh-models', methods=['POST'])
@login_required
def refresh_predictive_models():
    """Refresh and retrain predictive models"""
    try:
        if not current_user.is_manager():
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions'
            }), 403
        
        # Create new sales forecast model
        sales_model = predictive_analytics.create_sales_forecast_model()
        
        # Create demand forecast model
        demand_model = predictive_analytics.create_demand_forecast_model()
        
        # Analyze customer lifetime value
        clv_analysis = predictive_analytics.analyze_customer_lifetime_value()
        
        return jsonify({
            'success': True,
            'message': 'Models refreshed successfully',
            'models_created': {
                'sales_forecast': sales_model is not None,
                'demand_forecast': demand_model is not None,
                'clv_analysis': bool(clv_analysis)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/process-batch', methods=['POST'])
@login_required
def process_batch_analytics():
    """Process batch analytics for historical data"""
    try:
        if not current_user.is_manager():
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions'
            }), 403
        
        # Get date range from request
        data = request.get_json() or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end_date = datetime.now()
        
        # Process batch analytics
        success = analytics_pipeline.process_batch_analytics(start_date, end_date)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Batch analytics processed for {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Batch processing failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500