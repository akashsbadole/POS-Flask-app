from datetime import datetime, timedelta
from collections import defaultdict
from models import db, Order, OrderItem, MenuItem, User, Table, Category, AnalyticsData, TrendAnalysis, CustomerInsights, BusinessMetrics
import json
import logging
from decimal import Decimal
import numpy as np
from scipy import stats

class AnalyticsDataPipeline:
    """Analytics data pipeline for real-time and batch processing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.processing_cache = {}
    
    def process_real_time_order(self, order_id):
        """Process real-time order data for analytics"""
        try:
            order = Order.query.get(order_id)
            if not order or not order.is_completed:
                return False
            
            # Process sales analytics
            self._process_sales_data(order)
            
            # Process order analytics
            self._process_order_data(order)
            
            # Process customer analytics
            self._process_customer_data(order)
            
            # Process menu item analytics
            self._process_menu_item_data(order)
            
            # Process staff performance analytics
            self._process_staff_data(order)
            
            return True
        except Exception as e:
            self.logger.error(f"Error processing real-time order {order_id}: {str(e)}")
            return False
    
    def _process_sales_data(self, order):
        """Process sales data from completed order"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        # Daily sales
        sales_metric = AnalyticsData.query.filter_by(
            metric_type='sales',
            metric_name='daily_revenue',
            period_start=today,
            period_end=tomorrow
        ).first()
        
        if sales_metric:
            sales_metric.metric_value += order.grand_total
            sales_metric.sample_size += 1
        else:
            sales_metric = AnalyticsData.create_sales_metric(
                metric_name='daily_revenue',
                value=order.grand_total,
                period_start=today,
                period_end=tomorrow
            )
            db.session.add(sales_metric)
        
        # Sales by hour
        hour_start = order.completed_at.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        
        hourly_sales = AnalyticsData.query.filter_by(
            metric_type='sales',
            metric_name='hourly_revenue',
            period_start=hour_start,
            period_end=hour_end
        ).first()
        
        if hourly_sales:
            hourly_sales.metric_value += order.grand_total
        else:
            hourly_sales = AnalyticsData.create_sales_metric(
                metric_name='hourly_revenue',
                value=order.grand_total,
                period_start=hour_start,
                period_end=hour_end
            )
            db.session.add(hourly_sales)
        
        db.session.commit()
    
    def _process_order_data(self, order):
        """Process order-related analytics"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        # Order count
        order_count = AnalyticsData.query.filter_by(
            metric_type='orders',
            metric_name='daily_order_count',
            period_start=today,
            period_end=tomorrow
        ).first()
        
        if order_count:
            order_count.metric_value += 1
            order_count.sample_size += 1
        else:
            order_count = AnalyticsData.create_order_metric(
                metric_name='daily_order_count',
                value=1,
                period_start=today,
                period_end=tomorrow
            )
            db.session.add(order_count)
        
        # Average order value
        avg_order_metric = AnalyticsData.query.filter_by(
            metric_type='orders',
            metric_name='daily_average_order_value',
            period_start=today,
            period_end=tomorrow
        ).first()
        
        if avg_order_metric:
            # Update rolling average
            current_total = float(avg_order_metric.metric_value) * (avg_order_metric.sample_size - 1)
            new_total = current_total + float(order.grand_total)
            avg_order_metric.metric_value = new_total / avg_order_metric.sample_size
        else:
            avg_order_metric = AnalyticsData.create_order_metric(
                metric_name='daily_average_order_value',
                value=order.grand_total,
                period_start=today,
                period_end=tomorrow
            )
            avg_order_metric.sample_size = 1
            db.session.add(avg_order_metric)
        
        db.session.commit()
    
    def _process_customer_data(self, order):
        """Process customer-related analytics"""
        if not order.customer_mobile:
            return
        
        # Encrypt customer mobile for privacy
        from utils.encryption import get_encryption_manager
        encryption_manager = get_encryption_manager()
        
        customer_hash = encryption_manager.hash_field(order.customer_mobile)
        
        # Find or create customer insights
        customer = CustomerInsights.query.filter_by(customer_hash=customer_hash).first()
        
        if not customer:
            customer = CustomerInsights(customer_hash=customer_hash)
            db.session.add(customer)
        
        # Update customer metrics
        today = datetime.now().date()
        last_visit = customer.last_visit_date.date() if customer.last_visit_date else None
        
        if last_visit:
            recency_days = (today - last_visit).days
        else:
            recency_days = 0
        
        customer.update_rfm_metrics(
            recency_days=recency_days,
            frequency_count=customer.total_orders + 1,
            monetary_value=float(customer.monetary_value) + float(order.grand_total)
        )
        
        # Update other customer metrics
        customer.total_orders += 1
        customer.last_visit_date = order.completed_at
        
        # Update preferred order time
        hour = order.completed_at.hour
        if 6 <= hour < 12:
            customer.preferred_order_time = 'morning'
        elif 12 <= hour < 17:
            customer.preferred_order_time = 'afternoon'
        elif 17 <= hour < 22:
            customer.preferred_order_time = 'evening'
        else:
            customer.preferred_order_time = 'night'
        
        # Update preferred order type
        customer.preferred_order_type = order.order_type
        
        # Calculate loyalty score
        customer.calculate_loyalty_score()
        
        db.session.commit()
    
    def _process_menu_item_data(self, order):
        """Process menu item performance analytics"""
        for item in order.order_items:
            if item.status != 'Completed':
                continue
            
            # Daily item sales
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            item_sales = AnalyticsData.query.filter_by(
                metric_type='sales',
                metric_name='daily_item_sales',
                menu_item_id=item.menu_item_id,
                period_start=today,
                period_end=tomorrow
            ).first()
            
            if item_sales:
                item_sales.metric_value += item.total
            else:
                item_sales = AnalyticsData.create_sales_metric(
                    metric_name='daily_item_sales',
                    value=item.total,
                    period_start=today,
                    period_end=tomorrow,
                    menu_item_id=item.menu_item_id
                )
                db.session.add(item_sales)
            
            # Item quantity
            item_quantity = AnalyticsData.query.filter_by(
                metric_type='orders',
                metric_name='daily_item_quantity',
                menu_item_id=item.menu_item_id,
                period_start=today,
                period_end=tomorrow
            ).first()
            
            if item_quantity:
                item_quantity.metric_value += item.quantity
            else:
                item_quantity = AnalyticsData.create_order_metric(
                    metric_name='daily_item_quantity',
                    value=item.quantity,
                    period_start=today,
                    period_end=tomorrow
                )
                item_quantity.menu_item_id = item.menu_item_id
                db.session.add(item_quantity)
        
        db.session.commit()
    
    def _process_staff_data(self, order):
        """Process staff performance analytics"""
        if not order.created_by_user:
            return
        
        # Daily sales per staff
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        staff_sales = AnalyticsData.query.filter_by(
            metric_type='sales',
            metric_name='daily_staff_sales',
            user_id=order.created_by,
            period_start=today,
            period_end=tomorrow
        ).first()
        
        if staff_sales:
            staff_sales.metric_value += order.grand_total
            staff_sales.sample_size += 1
        else:
            staff_sales = AnalyticsData.create_sales_metric(
                metric_name='daily_staff_sales',
                value=order.grand_total,
                period_start=today,
                period_end=tomorrow,
                user_id=order.created_by
            )
            db.session.add(staff_sales)
        
        # Orders per staff
        staff_orders = AnalyticsData.query.filter_by(
            metric_type='orders',
            metric_name='daily_staff_orders',
            user_id=order.created_by,
            period_start=today,
            period_end=tomorrow
        ).first()
        
        if staff_orders:
            staff_orders.metric_value += 1
        else:
            staff_orders = AnalyticsData.create_order_metric(
                metric_name='daily_staff_orders',
                value=1,
                period_start=today,
                period_end=tomorrow
            )
            staff_orders.user_id = order.created_by
            db.session.add(staff_orders)
        
        db.session.commit()
    
    def process_batch_analytics(self, start_date, end_date):
        """Process batch analytics for historical data"""
        try:
            self.logger.info(f"Starting batch analytics processing for {start_date} to {end_date}")
            
            # Process sales trends
            self._analyze_sales_trends(start_date, end_date)
            
            # Process menu item performance trends
            self._analyze_menu_trends(start_date, end_date)
            
            # Process customer behavior trends
            self._analyze_customer_trends(start_date, end_date)
            
            # Process operational metrics
            self._analyze_operational_metrics(start_date, end_date)
            
            # Update business KPIs
            self._update_business_metrics(start_date, end_date)
            
            self.logger.info("Batch analytics processing completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in batch analytics processing: {str(e)}")
            return False
    
    def _analyze_sales_trends(self, start_date, end_date):
        """Analyze sales trends and patterns"""
        # Get daily sales data
        sales_data = AnalyticsData.query.filter(
            AnalyticsData.metric_type == 'sales',
            AnalyticsData.metric_name == 'daily_revenue',
            AnalyticsData.period_start >= start_date,
            AnalyticsData.period_end <= end_date
        ).order_by(AnalyticsData.period_start).all()
        
        if len(sales_data) < 7:  # Need at least a week of data
            return
        
        # Prepare time series data
        dates = []
        values = []
        for data in sales_data:
            dates.append(data.period_start.date())
            values.append(float(data.metric_value))
        
        # Perform linear trend analysis
        x = np.arange(len(dates))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        
        # Determine trend direction
        if slope > 0.1:
            direction = 'increasing'
        elif slope < -0.1:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        # Create trend analysis record
        trend = TrendAnalysis(
            trend_name=f"Sales Trend {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            trend_type='sales_growth',
            time_period='daily',
            trend_start_date=start_date,
            trend_end_date=end_date,
            trend_direction=direction,
            trend_strength=abs(r_value),
            trend_slope=slope,
            r_squared=r_value**2,
            p_value=p_value,
            data_points=values,
            algorithm_used='linear_regression'
        )
        
        db.session.add(trend)
        db.session.commit()
        
        # Check for seasonality (weekly pattern)
        self._analyze_seasonality(trend, sales_data)
    
    def _analyze_seasonality(self, trend, sales_data):
        """Analyze seasonal patterns in sales data"""
        if len(sales_data) < 14:  # Need at least 2 weeks for seasonality
            return
        
        # Group by day of week
        day_totals = defaultdict(list)
        for data in sales_data:
            day_of_week = data.period_start.weekday()
            day_totals[day_of_week].append(float(data.metric_value))
        
        # Calculate averages for each day
        day_averages = {}
        for day, values in day_totals.items():
            if values:
                day_averages[day] = sum(values) / len(values)
        
        # Check if there's significant variation
        if len(day_averages) >= 7:
            avg_values = list(day_averages.values())
            overall_avg = sum(avg_values) / len(avg_values)
            
            # Calculate coefficient of variation
            variance = sum((x - overall_avg)**2 for x in avg_values) / len(avg_values)
            std_dev = variance ** 0.5
            cv = std_dev / overall_avg if overall_avg > 0 else 0
            
            if cv > 0.1:  # 10% variation indicates seasonality
                trend.has_seasonality = True
                trend.seasonality_period = 7  # Weekly seasonality
                trend.seasonality_amplitude = cv
                db.session.commit()
    
    def _analyze_menu_trends(self, start_date, end_date):
        """Analyze menu item performance trends"""
        # Get menu item sales data
        menu_data = AnalyticsData.query.filter(
            AnalyticsData.metric_type == 'sales',
            AnalyticsData.metric_name == 'daily_item_sales',
            AnalyticsData.period_start >= start_date,
            AnalyticsData.period_end <= end_date
        ).all()
        
        # Group by menu item
        item_performance = defaultdict(list)
        for data in menu_data:
            if data.menu_item_id:
                item_performance[data.menu_item_id].append(data)
        
        # Analyze each item's performance
        for item_id, data_points in item_performance.items():
            if len(data_points) < 3:
                continue
            
            # Calculate performance metrics
            values = [float(d.metric_value) for d in data_points]
            avg_performance = sum(values) / len(values)
            performance_trend = self._calculate_trend(values)
            
            # Determine if item is trending up or down
            if performance_trend > 0.05:
                trend_direction = 'increasing'
            elif performance_trend < -0.05:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'
            
            # Create trend analysis for menu item
            menu_trend = TrendAnalysis(
                trend_name=f"Menu Item {item_id} Performance Trend",
                trend_type='menu_performance',
                time_period='daily',
                trend_start_date=start_date,
                trend_end_date=end_date,
                trend_direction=trend_direction,
                trend_strength=abs(performance_trend),
                trend_slope=performance_trend,
                data_points=values,
                algorithm_used='moving_average'
            )
            
            db.session.add(menu_trend)
        
        db.session.commit()
    
    def _analyze_customer_trends(self, start_date, end_date):
        """Analyze customer behavior trends"""
        # Get customer insights data
        customers = CustomerInsights.query.filter(
            CustomerInsights.analysis_date >= start_date,
            CustomerInsights.analysis_date <= end_date
        ).all()
        
        if not customers:
            return
        
        # Analyze customer segmentation distribution
        segment_counts = defaultdict(int)
        total_customers = len(customers)
        
        for customer in customers:
            segment_counts[customer.customer_segment] += 1
        
        # Calculate customer lifetime value trends
        clv_values = [float(c.customer_lifetime_value) for c in customers if c.customer_lifetime_value > 0]
        
        if clv_values:
            avg_clv = sum(clv_values) / len(clv_values)
            clv_trend = TrendAnalysis(
                trend_name="Customer Lifetime Value Trend",
                trend_type='customer_value',
                time_period='daily',
                trend_start_date=start_date,
                trend_end_date=end_date,
                trend_direction='stable',  # Would need historical data to determine trend
                trend_strength=0.5,
                data_points=clv_values,
                algorithm_used='average_calculation'
            )
            db.session.add(clv_trend)
        
        db.session.commit()
    
    def _analyze_operational_metrics(self, start_date, end_date):
        """Analyze operational performance metrics"""
        # Calculate average order processing time
        orders = Order.query.filter(
            Order.created_at >= start_date,
            Order.completed_at <= end_date,
            Order.status == 'Completed'
        ).all()
        
        if not orders:
            return
        
        processing_times = []
        for order in orders:
            if order.completed_at:
                processing_time = (order.completed_at - order.created_at).total_seconds() / 60  # minutes
                processing_times.append(processing_time)
        
        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)
            
            processing_trend = TrendAnalysis(
                trend_name="Order Processing Time Trend",
                trend_type='operational_efficiency',
                time_period='daily',
                trend_start_date=start_date,
                trend_end_date=end_date,
                trend_direction='stable',
                trend_strength=0.5,
                data_points=processing_times,
                algorithm_used='average_calculation'
            )
            db.session.add(processing_trend)
        
        db.session.commit()
    
    def _update_business_metrics(self, start_date, end_date):
        """Update key business performance metrics"""
        # Calculate total revenue
        total_revenue = db.session.query(db.func.sum(Order.grand_total)).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == 'Completed'
        ).scalar() or 0
        
        # Calculate total orders
        total_orders = Order.query.filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == 'Completed'
        ).count()
        
        # Calculate average order value
        avg_order_value = float(total_revenue) / total_orders if total_orders > 0 else 0
        
        # Get previous period for comparison
        period_length = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_length)
        prev_end = start_date
        
        prev_revenue = db.session.query(db.func.sum(Order.grand_total)).filter(
            Order.created_at >= prev_start,
            Order.created_at <= prev_end,
            Order.status == 'Completed'
        ).scalar() or 0
        
        prev_orders = Order.query.filter(
            Order.created_at >= prev_start,
            Order.created_at <= prev_end,
            Order.status == 'Completed'
        ).count()
        
        prev_avg_order_value = float(prev_revenue) / prev_orders if prev_orders > 0 else 0
        
        # Create business metrics
        metrics = [
            ('Total Revenue', 'financial', total_revenue, prev_revenue, 'currency'),
            ('Total Orders', 'operational', total_orders, prev_orders, 'count'),
            ('Average Order Value', 'financial', avg_order_value, prev_avg_order_value, 'currency')
        ]
        
        for metric_name, category, current_value, previous_value, unit in metrics:
            metric = BusinessMetrics(
                metric_name=metric_name,
                metric_category=category,
                current_value=current_value,
                calculation_period='weekly',
                period_start=start_date,
                period_end=end_date,
                unit=unit,
                calculation_method='aggregation'
            )
            metric.calculate_change(previous_value)
            db.session.add(metric)
        
        db.session.commit()
    
    def _calculate_trend(self, values):
        """Calculate trend slope for a list of values"""
        if len(values) < 2:
            return 0
        
        x = np.arange(len(values))
        slope, _, _, _, _ = stats.linregress(x, values)
        return slope
    
    def get_real_time_dashboard_data(self):
        """Get real-time data for dashboard"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Today's metrics
        today_revenue = AnalyticsData.query.filter_by(
            metric_type='sales',
            metric_name='daily_revenue',
            period_start=today
        ).first()
        
        today_orders = AnalyticsData.query.filter_by(
            metric_type='orders',
            metric_name='daily_order_count',
            period_start=today
        ).first()
        
        # Active orders
        active_orders = Order.query.filter(
            Order.status.in_(['New', 'In Progress', 'Ready'])
        ).count()
        
        # Hourly sales for today
        hourly_sales = AnalyticsData.query.filter_by(
            metric_type='sales',
            metric_name='hourly_revenue',
        ).filter(
            AnalyticsData.period_start >= today
        ).all()
        
        return {
            'today_revenue': float(today_revenue.metric_value) if today_revenue else 0,
            'today_orders': int(today_orders.metric_value) if today_orders else 0,
            'active_orders': active_orders,
            'hourly_sales': [
                {
                    'hour': data.period_start.hour,
                    'revenue': float(data.metric_value)
                } for data in hourly_sales
            ]
        }


# Global analytics pipeline instance
analytics_pipeline = AnalyticsDataPipeline()