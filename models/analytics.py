from datetime import datetime, timedelta
from decimal import Decimal
from . import db
import json
import uuid

class AnalyticsData(db.Model):
    """AnalyticsData model for storing processed business metrics"""
    __tablename__ = 'analytics_data'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_type = db.Column(db.String(50), nullable=False)  # sales, orders, customers, inventory, etc.
    metric_name = db.Column(db.String(100), nullable=False)  # daily_revenue, order_count, etc.
    metric_value = db.Column(db.Numeric(15, 2), nullable=False)  # Numeric value
    metric_unit = db.Column(db.String(20), nullable=True)  # currency, count, percentage, etc.
    
    # Time period information
    period_type = db.Column(db.String(20), nullable=False)  # hourly, daily, weekly, monthly, yearly
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    
    # Additional dimensions
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Aggregation and metadata
    aggregation_method = db.Column(db.String(20), default='sum')  # sum, avg, min, max, count
    sample_size = db.Column(db.Integer, default=1)  # Number of data points aggregated
    confidence_level = db.Column(db.Float, nullable=True)  # For statistical metrics
    
    # Raw data for advanced analytics
    raw_data = db.Column(db.Text, nullable=True)  # JSON string of raw values
    computed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    category = db.relationship('Category', backref='analytics_data', lazy=True)
    menu_item = db.relationship('MenuItem', backref='analytics_data', lazy=True)
    table = db.relationship('Table', backref='analytics_data', lazy=True)
    user = db.relationship('User', backref='analytics_data', lazy=True)
    
    def __init__(self, metric_type, metric_name, metric_value, period_type, 
                 period_start, period_end, metric_unit=None, category_id=None, 
                 menu_item_id=None, table_id=None, user_id=None, 
                 aggregation_method='sum', sample_size=1, confidence_level=None,
                 raw_data=None):
        self.metric_type = metric_type
        self.metric_name = metric_name
        self.metric_value = Decimal(str(metric_value))
        self.metric_unit = metric_unit
        self.period_type = period_type
        self.period_start = period_start
        self.period_end = period_end
        self.category_id = category_id
        self.menu_item_id = menu_item_id
        self.table_id = table_id
        self.user_id = user_id
        self.aggregation_method = aggregation_method
        self.sample_size = sample_size
        self.confidence_level = confidence_level
        self.raw_data = json.dumps(raw_data) if raw_data else None
    
    @property
    def formatted_value(self):
        """Get formatted metric value"""
        if self.metric_unit == 'currency':
            return f"₹{self.metric_value:.2f}"
        elif self.metric_unit == 'percentage':
            return f"{self.metric_value:.1f}%"
        else:
            return f"{self.metric_value:.2f}"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'metric_type': self.metric_type,
            'metric_name': self.metric_name,
            'metric_value': float(self.metric_value),
            'formatted_value': self.formatted_value,
            'metric_unit': self.metric_unit,
            'period_type': self.period_type,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'menu_item_id': self.menu_item_id,
            'menu_item_name': self.menu_item.name if self.menu_item else None,
            'table_id': self.table_id,
            'table_number': self.table.table_number if self.table else None,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'aggregation_method': self.aggregation_method,
            'sample_size': self.sample_size,
            'confidence_level': self.confidence_level,
            'raw_data': json.loads(self.raw_data) if self.raw_data else None,
            'computed_at': self.computed_at.isoformat() if self.computed_at else None
        }
    
    @staticmethod
    def get_metrics_by_type(metric_type, start_date=None, end_date=None):
        """Get analytics data by metric type"""
        query = AnalyticsData.query.filter_by(metric_type=metric_type)
        
        if start_date:
            query = query.filter(AnalyticsData.period_start >= start_date)
        if end_date:
            query = query.filter(AnalyticsData.period_end <= end_date)
        
        return query.order_by(AnalyticsData.period_start.desc()).all()
    
    @staticmethod
    def create_sales_metric(metric_name, value, period_start, period_end, 
                           category_id=None, menu_item_id=None, raw_data=None):
        """Create sales-related analytics data"""
        return AnalyticsData(
            metric_type='sales',
            metric_name=metric_name,
            metric_value=value,
            metric_unit='currency',
            period_type='daily',
            period_start=period_start,
            period_end=period_end,
            category_id=category_id,
            menu_item_id=menu_item_id,
            raw_data=raw_data
        )
    
    @staticmethod
    def create_order_metric(metric_name, value, period_start, period_end, raw_data=None):
        """Create order-related analytics data"""
        return AnalyticsData(
            metric_type='orders',
            metric_name=metric_name,
            metric_value=value,
            metric_unit='count',
            period_type='daily',
            period_start=period_start,
            period_end=period_end,
            raw_data=raw_data
        )
    
    @staticmethod
    def create_customer_metric(metric_name, value, period_start, period_end, raw_data=None):
        """Create customer-related analytics data"""
        return AnalyticsData(
            metric_type='customers',
            metric_name=metric_name,
            metric_value=value,
            metric_unit='count',
            period_type='daily',
            period_start=period_start,
            period_end=period_end,
            raw_data=raw_data
        )
    
    def __repr__(self):
        return f'<AnalyticsData {self.metric_type}.{self.metric_name}: {self.metric_value}>'


class TrendAnalysis(db.Model):
    """TrendAnalysis model for tracking historical patterns and trends"""
    __tablename__ = 'trend_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    trend_name = db.Column(db.String(100), nullable=False)
    trend_type = db.Column(db.String(50), nullable=False)  # sales_growth, seasonal_pattern, etc.
    
    # Time series data
    time_period = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly
    trend_start_date = db.Column(db.DateTime, nullable=False)
    trend_end_date = db.Column(db.DateTime, nullable=False)
    
    # Trend characteristics
    trend_direction = db.Column(db.String(20))  # increasing, decreasing, stable, cyclical
    trend_strength = db.Column(db.Float)  # 0-1, strength of the trend
    trend_slope = db.Column(db.Float)  # Rate of change per period
    
    # Statistical measures
    r_squared = db.Column(db.Float)  # Correlation coefficient
    p_value = db.Column(db.Float)  # Statistical significance
    confidence_interval = db.Column(db.Float)  # Confidence level
    
    # Seasonal analysis
    has_seasonality = db.Column(db.Boolean, default=False)
    seasonality_period = db.Column(db.Integer, nullable=True)  # Days in cycle
    seasonality_amplitude = db.Column(db.Float, nullable=True)
    
    # Data points
    data_points = db.Column(db.Text)  # JSON array of data points
    trend_values = db.Column(db.Text)  # JSON array of calculated trend values
    
    # Predictions
    forecast_horizon = db.Column(db.Integer)  # Days/weeks to forecast
    predicted_values = db.Column(db.Text)  # JSON array of predictions
    
    # Metadata
    algorithm_used = db.Column(db.String(50))  # linear_regression, moving_average, etc.
    computed_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __init__(self, trend_name, trend_type, time_period, trend_start_date, trend_end_date,
                 trend_direction=None, trend_strength=None, trend_slope=None,
                 r_squared=None, p_value=None, confidence_interval=None,
                 has_seasonality=False, seasonality_period=None, seasonality_amplitude=None,
                 data_points=None, trend_values=None, forecast_horizon=None, predicted_values=None,
                 algorithm_used=None):
        self.trend_name = trend_name
        self.trend_type = trend_type
        self.time_period = time_period
        self.trend_start_date = trend_start_date
        self.trend_end_date = trend_end_date
        self.trend_direction = trend_direction
        self.trend_strength = trend_strength
        self.trend_slope = trend_slope
        self.r_squared = r_squared
        self.p_value = p_value
        self.confidence_interval = confidence_interval
        self.has_seasonality = has_seasonality
        self.seasonality_period = seasonality_period
        self.seasonality_amplitude = seasonality_amplitude
        self.data_points = json.dumps(data_points) if data_points else None
        self.trend_values = json.dumps(trend_values) if trend_values else None
        self.forecast_horizon = forecast_horizon
        self.predicted_values = json.dumps(predicted_values) if predicted_values else None
        self.algorithm_used = algorithm_used
    
    @property
    def data_points_list(self):
        """Get data points as list"""
        return json.loads(self.data_points) if self.data_points else []
    
    @property
    def trend_values_list(self):
        """Get trend values as list"""
        return json.loads(self.trend_values) if self.trend_values else []
    
    @property
    def predicted_values_list(self):
        """Get predicted values as list"""
        return json.loads(self.predicted_values) if self.predicted_values else []
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'trend_name': self.trend_name,
            'trend_type': self.trend_type,
            'time_period': self.time_period,
            'trend_start_date': self.trend_start_date.isoformat(),
            'trend_end_date': self.trend_end_date.isoformat(),
            'trend_direction': self.trend_direction,
            'trend_strength': self.trend_strength,
            'trend_slope': self.trend_slope,
            'r_squared': self.r_squared,
            'p_value': self.p_value,
            'confidence_interval': self.confidence_interval,
            'has_seasonality': self.has_seasonality,
            'seasonality_period': self.seasonality_period,
            'seasonality_amplitude': self.seasonality_amplitude,
            'data_points': self.data_points_list,
            'trend_values': self.trend_values_list,
            'forecast_horizon': self.forecast_horizon,
            'predicted_values': self.predicted_values_list,
            'algorithm_used': self.algorithm_used,
            'computed_at': self.computed_at.isoformat(),
            'is_active': self.is_active
        }
    
    @staticmethod
    def get_trends_by_type(trend_type, is_active=True):
        """Get trends by type"""
        query = TrendAnalysis.query.filter_by(trend_type=trend_type)
        if is_active:
            query = query.filter_by(is_active=True)
        return query.order_by(TrendAnalysis.computed_at.desc()).all()
    
    def __repr__(self):
        return f'<TrendAnalysis {self.trend_name} ({self.trend_direction})>'


class PredictiveModel(db.Model):
    """PredictiveModel model for ML-based forecasting"""
    __tablename__ = 'predictive_models'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)  # sales_forecast, demand_prediction, etc.
    
    # Model parameters
    algorithm = db.Column(db.String(50), nullable=False)  # arima, lstm, linear_regression, etc.
    hyperparameters = db.Column(db.Text)  # JSON string of model parameters
    features = db.Column(db.Text)  # JSON array of input features
    target_variable = db.Column(db.String(50), nullable=False)
    
    # Training data
    training_start_date = db.Column(db.DateTime, nullable=False)
    training_end_date = db.Column(db.DateTime, nullable=False)
    training_data_size = db.Column(db.Integer)
    
    # Model performance
    accuracy_score = db.Column(db.Float)
    r2_score = db.Column(db.Float)
    mean_absolute_error = db.Column(db.Float)
    root_mean_square_error = db.Column(db.Float)
    
    # Model metadata
    model_version = db.Column(db.String(20), default='1.0')
    is_trained = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Serialized model (could be large, so we might need to store in files)
    model_data = db.Column(db.Text)  # JSON or serialized model parameters
    
    # Validation metrics
    cross_validation_score = db.Column(db.Float)
    validation_start_date = db.Column(db.DateTime)
    validation_end_date = db.Column(db.DateTime)
    
    # Predictions
    last_prediction_date = db.Column(db.DateTime)
    prediction_horizon_days = db.Column(db.Integer, default=30)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_trained_at = db.Column(db.DateTime)
    last_used_at = db.Column(db.DateTime)
    
    def __init__(self, model_name, model_type, algorithm, target_variable, 
                 training_start_date, training_end_date, features=None,
                 hyperparameters=None, model_version='1.0'):
        self.model_name = model_name
        self.model_type = model_type
        self.algorithm = algorithm
        self.target_variable = target_variable
        self.training_start_date = training_start_date
        self.training_end_date = training_end_date
        self.features = json.dumps(features) if features else None
        self.hyperparameters = json.dumps(hyperparameters) if hyperparameters else None
        self.model_version = model_version
    
    @property
    def features_list(self):
        """Get features as list"""
        return json.loads(self.features) if self.features else []
    
    @property
    def hyperparameters_dict(self):
        """Get hyperparameters as dictionary"""
        return json.loads(self.hyperparameters) if self.hyperparameters else {}
    
    def update_performance_metrics(self, accuracy_score, r2_score, mae, rmse, 
                                   cross_validation_score=None):
        """Update model performance metrics"""
        self.accuracy_score = accuracy_score
        self.r2_score = r2_score
        self.mean_absolute_error = mae
        self.root_mean_square_error = rmse
        if cross_validation_score:
            self.cross_validation_score = cross_validation_score
        self.last_trained_at = datetime.utcnow()
        self.is_trained = True
        db.session.commit()
    
    def update_usage(self):
        """Update last used timestamp"""
        self.last_used_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'algorithm': self.algorithm,
            'features': self.features_list,
            'hyperparameters': self.hyperparameters_dict,
            'target_variable': self.target_variable,
            'training_start_date': self.training_start_date.isoformat(),
            'training_end_date': self.training_end_date.isoformat(),
            'training_data_size': self.training_data_size,
            'accuracy_score': self.accuracy_score,
            'r2_score': self.r2_score,
            'mean_absolute_error': self.mean_absolute_error,
            'root_mean_square_error': self.root_mean_square_error,
            'model_version': self.model_version,
            'is_trained': self.is_trained,
            'is_active': self.is_active,
            'cross_validation_score': self.cross_validation_score,
            'validation_start_date': self.validation_start_date.isoformat() if self.validation_start_date else None,
            'validation_end_date': self.validation_end_date.isoformat() if self.validation_end_date else None,
            'last_prediction_date': self.last_prediction_date.isoformat() if self.last_prediction_date else None,
            'prediction_horizon_days': self.prediction_horizon_days,
            'created_at': self.created_at.isoformat(),
            'last_trained_at': self.last_trained_at.isoformat() if self.last_trained_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }
    
    @staticmethod
    def get_active_models():
        """Get all active models"""
        return PredictiveModel.query.filter_by(is_active=True, is_trained=True).all()
    
    @staticmethod
    def get_models_by_type(model_type):
        """Get models by type"""
        return PredictiveModel.query.filter_by(model_type=model_type, is_active=True).all()
    
    def __repr__(self):
        return f'<PredictiveModel {self.model_name} ({self.algorithm})>'


class CustomerInsights(db.Model):
    """CustomerInsights model for customer behavior analysis"""
    __tablename__ = 'customer_insights'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Customer identification (anonymized for privacy)
    customer_hash = db.Column(db.String(64), nullable=True)  # Hash for customer tracking
    customer_mobile = db.Column(db.String(20), nullable=True)  # Encrypted mobile
    customer_name_encrypted = db.Column(db.String(255), nullable=True)  # Encrypted name
    
    # Customer segmentation
    customer_segment = db.Column(db.String(50))  # VIP, Regular, Occasional, New, etc.
    customer_lifetime_value = db.Column(db.Numeric(12, 2), default=0)
    acquisition_channel = db.Column(db.String(50))  # walk_in, online, referral, etc.
    
    # RFM Analysis
    recency_days = db.Column(db.Integer)  # Days since last order
    frequency_count = db.Column(db.Integer, default=0)  # Number of orders
    monetary_value = db.Column(db.Numeric(12, 2), default=0)  # Total spent
    
    # Behavior patterns
    average_order_value = db.Column(db.Numeric(10, 2), default=0)
    preferred_order_time = db.Column(db.String(20))  # morning, afternoon, evening, night
    preferred_order_type = db.Column(db.String(20))  # dine_in, takeaway, delivery
    preferred_payment_method = db.Column(db.String(30))
    
    # Menu preferences
    favorite_category = db.Column(db.String(100))
    favorite_items = db.Column(db.Text)  # JSON array of item IDs
    spice_preference = db.Column(db.String(20))  # mild, medium, spicy, very_spicy
    dietary_restrictions = db.Column(db.Text)  # JSON array of restrictions
    
    # Visit patterns
    most_visited_day = db.Column(db.String(20))  # Monday, Tuesday, etc.
    most_visited_time = db.Column(db.String(20))  # 10:00-11:00, etc.
    average_visit_duration = db.Column(db.Integer)  # minutes
    
    # Loyalty and engagement
    loyalty_score = db.Column(db.Float, default=0)  # 0-100
    last_visit_date = db.Column(db.DateTime)
    churn_risk_score = db.Column(db.Float, default=0)  # 0-1, probability of churning
    
    # Order history summary
    total_orders = db.Column(db.Integer, default=0)
    cancelled_orders = db.Column(db.Integer, default=0)
    returned_customers = db.Column(db.Integer, default=0)
    
    # Seasonal preferences
    seasonal_preferences = db.Column(db.Text)  # JSON object with seasonal data
    weather_preferences = db.Column(db.Text)  # JSON object with weather correlation
    
    # Analysis metadata
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    data_source = db.Column(db.String(50))  # orders, feedback, surveys
    confidence_score = db.Column(db.Float)  # Confidence in the insights
    
    def __init__(self, customer_hash=None, customer_mobile=None, customer_name_encrypted=None,
                 customer_segment='Regular', acquisition_channel='walk_in'):
        self.customer_hash = customer_hash
        self.customer_mobile = customer_mobile
        self.customer_name_encrypted = customer_name_encrypted
        self.customer_segment = customer_segment
        self.acquisition_channel = acquisition_channel
    
    @property
    def favorite_items_list(self):
        """Get favorite items as list"""
        return json.loads(self.favorite_items) if self.favorite_items else []
    
    @property
    def dietary_restrictions_list(self):
        """Get dietary restrictions as list"""
        return json.loads(self.dietary_restrictions) if self.dietary_restrictions else []
    
    @property
    def seasonal_preferences_dict(self):
        """Get seasonal preferences as dictionary"""
        return json.loads(self.seasonal_preferences) if self.seasonal_preferences else {}
    
    @property
    def weather_preferences_dict(self):
        """Get weather preferences as dictionary"""
        return json.loads(self.weather_preferences) if self.weather_preferences else {}
    
    def update_rfm_metrics(self, recency_days, frequency_count, monetary_value):
        """Update RFM analysis metrics"""
        self.recency_days = recency_days
        self.frequency_count = frequency_count
        self.monetary_value = Decimal(str(monetary_value))
        
        # Calculate customer lifetime value
        if frequency_count > 0:
            self.customer_lifetime_value = self.monetary_value
            self.average_order_value = self.monetary_value / frequency_count
        else:
            self.average_order_value = Decimal('0')
        
        self.analysis_date = datetime.utcnow()
        db.session.commit()
    
    def calculate_loyalty_score(self):
        """Calculate customer loyalty score based on multiple factors"""
        score = 0
        
        # Frequency component (0-40 points)
        if self.frequency_count >= 20:
            score += 40
        elif self.frequency_count >= 10:
            score += 30
        elif self.frequency_count >= 5:
            score += 20
        elif self.frequency_count >= 2:
            score += 10
        
        # Monetary component (0-30 points)
        avg_order_value = float(self.average_order_value)
        if avg_order_value >= 1000:
            score += 30
        elif avg_order_value >= 500:
            score += 20
        elif avg_order_value >= 200:
            score += 10
        
        # Recency component (0-20 points)
        if self.recency_days <= 7:
            score += 20
        elif self.recency_days <= 30:
            score += 15
        elif self.recency_days <= 60:
            score += 10
        elif self.recency_days <= 90:
            score += 5
        
        # Consistency component (0-10 points)
        if self.total_orders > 0:
            consistency_ratio = (self.total_orders - self.cancelled_orders) / self.total_orders
            score += consistency_ratio * 10
        
        self.loyalty_score = min(score, 100)
        return self.loyalty_score
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'customer_hash': self.customer_hash,
            'customer_mobile': self.customer_mobile,
            'customer_segment': self.customer_segment,
            'customer_lifetime_value': float(self.customer_lifetime_value),
            'acquisition_channel': self.acquisition_channel,
            'recency_days': self.recency_days,
            'frequency_count': self.frequency_count,
            'monetary_value': float(self.monetary_value),
            'average_order_value': float(self.average_order_value),
            'preferred_order_time': self.preferred_order_time,
            'preferred_order_type': self.preferred_order_type,
            'preferred_payment_method': self.preferred_payment_method,
            'favorite_category': self.favorite_category,
            'favorite_items': self.favorite_items_list,
            'spice_preference': self.spice_preference,
            'dietary_restrictions': self.dietary_restrictions_list,
            'most_visited_day': self.most_visited_day,
            'most_visited_time': self.most_visited_time,
            'average_visit_duration': self.average_visit_duration,
            'loyalty_score': self.loyalty_score,
            'last_visit_date': self.last_visit_date.isoformat() if self.last_visit_date else None,
            'churn_risk_score': self.churn_risk_score,
            'total_orders': self.total_orders,
            'cancelled_orders': self.cancelled_orders,
            'returned_customers': self.returned_customers,
            'seasonal_preferences': self.seasonal_preferences_dict,
            'weather_preferences': self.weather_preferences_dict,
            'analysis_date': self.analysis_date.isoformat(),
            'data_source': self.data_source,
            'confidence_score': self.confidence_score
        }
    
    @staticmethod
    def get_customers_by_segment(segment):
        """Get customers by segment"""
        return CustomerInsights.query.filter_by(customer_segment=segment).all()
    
    @staticmethod
    def get_high_value_customers(min_value=1000):
        """Get high value customers"""
        return CustomerInsights.query.filter(
            CustomerInsights.customer_lifetime_value >= min_value
        ).order_by(CustomerInsights.customer_lifetime_value.desc()).all()
    
    @staticmethod
    def get_at_risk_customers():
        """Get customers at risk of churning"""
        return CustomerInsights.query.filter(
            CustomerInsights.churn_risk_score >= 0.7
        ).order_by(CustomerInsights.churn_risk_score.desc()).all()
    
    def __repr__(self):
        return f'<CustomerInsights {self.customer_segment} Customer (₹{self.customer_lifetime_value})>'


class BusinessMetrics(db.Model):
    """BusinessMetrics model for KPI tracking and benchmarking"""
    __tablename__ = 'business_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_category = db.Column(db.String(50), nullable=False)  # financial, operational, customer, marketing
    metric_description = db.Column(db.Text)
    
    # Metric values
    current_value = db.Column(db.Numeric(15, 2))
    previous_value = db.Column(db.Numeric(15, 2))
    target_value = db.Column(db.Numeric(15, 2))
    
    # Change indicators
    absolute_change = db.Column(db.Numeric(15, 2))
    percentage_change = db.Column(db.Float)
    
    # Benchmarking
    industry_benchmark = db.Column(db.Numeric(15, 2))
    competitor_benchmark = db.Column(db.Numeric(15, 2))
    best_in_class = db.Column(db.Numeric(15, 2))
    
    # Status and alerts
    status = db.Column(db.String(20))  # excellent, good, warning, critical
    alert_threshold = db.Column(db.Numeric(15, 2))
    is_monitoring_enabled = db.Column(db.Boolean, default=True)
    
    # Time period
    calculation_period = db.Column(db.String(20))  # daily, weekly, monthly, quarterly
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    
    # Additional context
    unit = db.Column(db.String(20))  # currency, percentage, count, ratio
    calculation_method = db.Column(db.String(100))  # How the metric is calculated
    data_sources = db.Column(db.Text)  # JSON array of data sources
    impact_factors = db.Column(db.Text)  # JSON object with key factors affecting the metric
    
    # Historical tracking
    trend_direction = db.Column(db.String(20))  # up, down, stable
    trend_strength = db.Column(db.Float)  # 0-1, strength of the trend
    
    # Metadata
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    calculated_by = db.Column(db.String(50), default='system')
    version = db.Column(db.String(20), default='1.0')
    
    def __init__(self, metric_name, metric_category, current_value, calculation_period,
                 period_start, period_end, metric_description=None, target_value=None,
                 industry_benchmark=None, competitor_benchmark=None, best_in_class=None,
                 unit='currency', calculation_method=None, data_sources=None):
        self.metric_name = metric_name
        self.metric_category = metric_category
        self.current_value = Decimal(str(current_value))
        self.calculation_period = calculation_period
        self.period_start = period_start
        self.period_end = period_end
        self.metric_description = metric_description
        self.target_value = Decimal(str(target_value)) if target_value else None
        self.industry_benchmark = Decimal(str(industry_benchmark)) if industry_benchmark else None
        self.competitor_benchmark = Decimal(str(competitor_benchmark)) if competitor_benchmark else None
        self.best_in_class = Decimal(str(best_in_class)) if best_in_class else None
        self.unit = unit
        self.calculation_method = calculation_method
        self.data_sources = json.dumps(data_sources) if data_sources else None
    
    @property
    def data_sources_list(self):
        """Get data sources as list"""
        return json.loads(self.data_sources) if self.data_sources else []
    
    @property
    def impact_factors_dict(self):
        """Get impact factors as dictionary"""
        return json.loads(self.impact_factors) if self.impact_factors else {}
    
    def calculate_change(self, previous_value):
        """Calculate change from previous period"""
        if previous_value is None:
            return
        
        self.previous_value = Decimal(str(previous_value))
        
        # Calculate absolute change
        self.absolute_change = self.current_value - self.previous_value
        
        # Calculate percentage change
        if self.previous_value != 0:
            self.percentage_change = (float(self.absolute_change) / float(self.previous_value)) * 100
        else:
            self.percentage_change = 0 if self.current_value == 0 else 100
        
        # Determine trend direction
        if self.percentage_change > 1:
            self.trend_direction = 'up'
        elif self.percentage_change < -1:
            self.trend_direction = 'down'
        else:
            self.trend_direction = 'stable'
        
        # Determine status based on performance vs targets
        self._determine_status()
    
    def _determine_status(self):
        """Determine metric status based on performance"""
        if self.target_value is None:
            self.status = 'unknown'
            return
        
        target_ratio = float(self.current_value) / float(self.target_value)
        
        if target_ratio >= 1.1:  # Exceeding target by 10%
            self.status = 'excellent'
        elif target_ratio >= 0.9:  # Meeting target
            self.status = 'good'
        elif target_ratio >= 0.7:  # Below target but acceptable
            self.status = 'warning'
        else:  # Significantly below target
            self.status = 'critical'
    
    def get_performance_summary(self):
        """Get performance summary for dashboard"""
        return {
            'metric_name': self.metric_name,
            'current_value': float(self.current_value),
            'target_value': float(self.target_value) if self.target_value else None,
            'previous_value': float(self.previous_value) if self.previous_value else None,
            'absolute_change': float(self.absolute_change) if self.absolute_change else 0,
            'percentage_change': self.percentage_change,
            'status': self.status,
            'trend_direction': self.trend_direction,
            'unit': self.unit,
            'period': f"{self.period_start.strftime('%Y-%m-%d')} to {self.period_end.strftime('%Y-%m-%d')}"
        }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_category': self.metric_category,
            'metric_description': self.metric_description,
            'current_value': float(self.current_value),
            'previous_value': float(self.previous_value) if self.previous_value else None,
            'target_value': float(self.target_value) if self.target_value else None,
            'absolute_change': float(self.absolute_change) if self.absolute_change else None,
            'percentage_change': self.percentage_change,
            'industry_benchmark': float(self.industry_benchmark) if self.industry_benchmark else None,
            'competitor_benchmark': float(self.competitor_benchmark) if self.competitor_benchmark else None,
            'best_in_class': float(self.best_in_class) if self.best_in_class else None,
            'status': self.status,
            'alert_threshold': float(self.alert_threshold) if self.alert_threshold else None,
            'is_monitoring_enabled': self.is_monitoring_enabled,
            'calculation_period': self.calculation_period,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'unit': self.unit,
            'calculation_method': self.calculation_method,
            'data_sources': self.data_sources_list,
            'impact_factors': self.impact_factors_dict,
            'trend_direction': self.trend_direction,
            'trend_strength': self.trend_strength,
            'calculated_at': self.calculated_at.isoformat(),
            'calculated_by': self.calculated_by,
            'version': self.version
        }
    
    @staticmethod
    def get_metrics_by_category(category):
        """Get metrics by category"""
        return BusinessMetrics.query.filter_by(metric_category=category).order_by(
            BusinessMetrics.calculated_at.desc()
        ).all()
    
    @staticmethod
    def get_critical_metrics():
        """Get metrics with critical status"""
        return BusinessMetrics.query.filter_by(status='critical', is_monitoring_enabled=True).all()
    
    @staticmethod
    def get_kpi_dashboard_data():
        """Get data for KPI dashboard"""
        metrics = BusinessMetrics.query.filter_by(is_monitoring_enabled=True).all()
        
        categories = {}
        for metric in metrics:
            if metric.metric_category not in categories:
                categories[metric.metric_category] = []
            categories[metric.metric_category].append(metric.get_performance_summary())
        
        return categories
    
    def __repr__(self):
        return f'<BusinessMetrics {self.metric_name}: {self.current_value} ({self.status})>'