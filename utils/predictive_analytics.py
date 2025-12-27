from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from models import db, AnalyticsData, TrendAnalysis, PredictiveModel, CustomerInsights, Order, OrderItem
import json
import logging
from decimal import Decimal

class PredictiveAnalyticsEngine:
    """Predictive analytics engine with ML models for forecasting"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scaler = StandardScaler()
    
    def create_sales_forecast_model(self, training_days=90):
        """Create and train sales forecast model"""
        try:
            # Get historical sales data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=training_days)
            
            sales_data = AnalyticsData.query.filter(
                AnalyticsData.metric_type == 'sales',
                AnalyticsData.metric_name == 'daily_revenue',
                AnalyticsData.period_start >= start_date,
                AnalyticsData.period_end <= end_date
            ).order_by(AnalyticsData.period_start).all()
            
            if len(sales_data) < 30:  # Need sufficient data
                self.logger.warning("Insufficient data for sales forecast model")
                return None
            
            # Prepare features
            features = []
            targets = []
            
            for i in range(7, len(sales_data)):  # Use 7-day window
                # Features: past 7 days of sales + day of week + day of month
                past_sales = [float(sales_data[j].metric_value) for j in range(i-7, i)]
                current_date = sales_data[i].period_start
                
                feature_vector = past_sales + [
                    current_date.weekday(),  # Day of week (0=Monday)
                    current_date.day,  # Day of month
                    current_date.month,  # Month
                    current_date.timetuple().tm_yday  # Day of year
                ]
                
                features.append(feature_vector)
                targets.append(float(sales_data[i].metric_value))
            
            if len(features) < 20:
                self.logger.warning("Not enough feature samples for training")
                return None
            
            # Convert to arrays
            X = np.array(features)
            y = np.array(targets)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            model = LinearRegression()
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Save model to database
            model_record = PredictiveModel(
                model_name='Sales Forecast Model',
                model_type='sales_forecast',
                algorithm='linear_regression',
                target_variable='daily_revenue',
                training_start_date=start_date,
                training_end_date=end_date,
                training_data_size=len(features)
            )
            
            # Store model parameters (simplified for demo)
            model_params = {
                'coefficients': model.coef_.tolist(),
                'intercept': float(model.intercept_),
                'feature_names': ['past_7_days'] + ['day_of_week', 'day_of_month', 'month', 'day_of_year'],
                'scaler_mean': self.scaler.mean_.tolist(),
                'scaler_scale': self.scaler.scale_.tolist()
            }
            
            model_record.model_data = json.dumps(model_params)
            model_record.update_performance_metrics(
                accuracy_score=r2,
                r2_score=r2,
                mae=mae,
                rmse=np.sqrt(np.mean((y_test - y_pred) ** 2))
            )
            
            db.session.add(model_record)
            db.session.commit()
            
            self.logger.info(f"Sales forecast model created with R² score: {r2:.3f}")
            return model_record
            
        except Exception as e:
            self.logger.error(f"Error creating sales forecast model: {str(e)}")
            return None
    
    def predict_sales(self, forecast_days=7):
        """Predict sales for next N days"""
        try:
            # Get the best trained model
            model_record = PredictiveModel.query.filter_by(
                model_type='sales_forecast',
                is_active=True,
                is_trained=True
            ).order_by(PredictiveModel.last_trained_at.desc()).first()
            
            if not model_record or not model_record.model_data:
                # Create new model if none exists
                model_record = self.create_sales_forecast_model()
                if not model_record:
                    return []
            
            model_params = json.loads(model_record.model_data)
            coefficients = model_params['coefficients']
            intercept = model_params['intercept']
            
            # Get recent sales data for features
            end_date = datetime.now()
            start_date = end_date - timedelta(days=14)
            
            recent_sales = AnalyticsData.query.filter(
                AnalyticsData.metric_type == 'sales',
                AnalyticsData.metric_name == 'daily_revenue',
                AnalyticsData.period_start >= start_date,
                AnalyticsData.period_end <= end_date
            ).order_by(AnalyticsData.period_start).all()
            
            if len(recent_sales) < 7:
                return []
            
            predictions = []
            
            # Use last 7 days as base
            base_sales = [float(s.metric_value) for s in recent_sales[-7:]]
            
            for i in range(forecast_days):
                # Create feature vector
                if i == 0:
                    feature_vector = base_sales.copy()
                else:
                    # Use prediction as part of next prediction
                    feature_vector = base_sales[1:] + [predictions[-1]['predicted_revenue']]
                
                # Add date features
                pred_date = end_date + timedelta(days=i+1)
                feature_vector.extend([
                    pred_date.weekday(),
                    pred_date.day,
                    pred_date.month,
                    pred_date.timetuple().tm_yday
                ])
                
                # Scale features
                X_scaled = (np.array(feature_vector) - np.array(model_params['scaler_mean'])) / np.array(model_params['scaler_scale'])
                
                # Make prediction
                prediction = np.dot(X_scaled, coefficients) + intercept
                prediction = max(0, prediction)  # Sales can't be negative
                
                predictions.append({
                    'date': pred_date.strftime('%Y-%m-%d'),
                    'predicted_revenue': float(prediction),
                    'confidence_interval': {
                        'lower': float(prediction * 0.8),
                        'upper': float(prediction * 1.2)
                    }
                })
            
            # Update model usage
            model_record.update_usage()
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error predicting sales: {str(e)}")
            return []
    
    def create_demand_forecast_model(self, menu_item_id=None, training_days=60):
        """Create demand forecast model for specific menu item or overall"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=training_days)
            
            # Get demand data (daily item quantities)
            query = AnalyticsData.query.filter(
                AnalyticsData.metric_type == 'orders',
                AnalyticsData.metric_name == 'daily_item_quantity',
                AnalyticsData.period_start >= start_date,
                AnalyticsData.period_end <= end_date
            )
            
            if menu_item_id:
                query = query.filter_by(menu_item_id=menu_item_id)
            
            demand_data = query.order_by(AnalyticsData.period_start).all()
            
            if len(demand_data) < 20:
                self.logger.warning(f"Insufficient demand data for {'item ' + str(menu_item_id) if menu_item_id else 'overall'}")
                return None
            
            # Prepare features for demand forecasting
            features = []
            targets = []
            
            for i in range(5, len(demand_data)):  # Use 5-day window
                past_quantities = [float(d.metric_value) for d in demand_data[i-5:i]]
                current_date = demand_data[i].period_start
                
                # Include weekend indicator
                is_weekend = 1 if current_date.weekday() >= 5 else 0
                
                feature_vector = past_quantities + [is_weekend, current_date.weekday()]
                features.append(feature_vector)
                targets.append(float(demand_data[i].metric_value))
            
            if len(features) < 15:
                return None
            
            # Convert to arrays
            X = np.array(features)
            y = np.array(targets)
            
            # Train model
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            model = LinearRegression()
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Save model
            model_name = f"Demand Forecast - {'Item ' + str(menu_item_id) if menu_item_id else 'Overall'}"
            model_type = 'item_demand_forecast' if menu_item_id else 'overall_demand_forecast'
            
            model_record = PredictiveModel(
                model_name=model_name,
                model_type=model_type,
                algorithm='linear_regression',
                target_variable='daily_quantity',
                training_start_date=start_date,
                training_end_date=end_date,
                training_data_size=len(features)
            )
            
            model_params = {
                'coefficients': model.coef_.tolist(),
                'intercept': float(model.intercept_),
                'menu_item_id': menu_item_id,
                'feature_names': ['past_5_days', 'is_weekend', 'day_of_week']
            }
            
            model_record.model_data = json.dumps(model_params)
            model_record.update_performance_metrics(
                accuracy_score=r2,
                r2_score=r2,
                mae=mae,
                rmse=np.sqrt(np.mean((y_test - y_pred) ** 2))
            )
            
            db.session.add(model_record)
            db.session.commit()
            
            return model_record
            
        except Exception as e:
            self.logger.error(f"Error creating demand forecast model: {str(e)}")
            return None
    
    def predict_demand(self, menu_item_id=None, forecast_days=7):
        """Predict demand for menu item or overall"""
        try:
            model_type = 'item_demand_forecast' if menu_item_id else 'overall_demand_forecast'
            
            model_record = PredictiveModel.query.filter_by(
                model_type=model_type,
                is_active=True,
                is_trained=True
            ).order_by(PredictiveModel.last_trained_at.desc()).first()
            
            if not model_record or not model_record.model_data:
                model_record = self.create_demand_forecast_model(menu_item_id)
                if not model_record:
                    return []
            
            model_params = json.loads(model_record.model_data)
            coefficients = model_params['coefficients']
            intercept = model_params['intercept']
            
            # Get recent demand data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=10)
            
            query = AnalyticsData.query.filter(
                AnalyticsData.metric_type == 'orders',
                AnalyticsData.metric_name == 'daily_item_quantity',
                AnalyticsData.period_start >= start_date,
                AnalyticsData.period_end <= end_date
            )
            
            if menu_item_id:
                query = query.filter_by(menu_item_id=menu_item_id)
            
            recent_demand = query.order_by(AnalyticsData.period_start).all()
            
            if len(recent_demand) < 5:
                return []
            
            predictions = []
            
            # Use last 5 days as base
            base_quantities = [float(d.metric_value) for d in recent_demand[-5:]]
            
            for i in range(forecast_days):
                # Create feature vector
                if i == 0:
                    feature_vector = base_quantities.copy()
                else:
                    feature_vector = base_quantities[1:] + [predictions[-1]['predicted_quantity']]
                
                # Add date features
                pred_date = end_date + timedelta(days=i+1)
                is_weekend = 1 if pred_date.weekday() >= 5 else 0
                feature_vector.extend([is_weekend, pred_date.weekday()])
                
                # Make prediction
                prediction = np.dot(feature_vector, coefficients) + intercept
                prediction = max(0, prediction)  # Quantity can't be negative
                
                predictions.append({
                    'date': pred_date.strftime('%Y-%m-%d'),
                    'predicted_quantity': float(prediction),
                    'predicted_quantity_int': int(round(prediction))
                })
            
            model_record.update_usage()
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error predicting demand: {str(e)}")
            return []
    
    def analyze_customer_lifetime_value(self):
        """Analyze and predict customer lifetime value"""
        try:
            customers = CustomerInsights.query.filter(
                CustomerInsights.total_orders > 0
            ).all()
            
            if not customers:
                return {}
            
            # Calculate features for CLV prediction
            features = []
            clv_values = []
            
            for customer in customers:
                # Feature vector: [frequency, recency, avg_order_value, loyalty_score]
                feature_vector = [
                    customer.frequency_count,
                    customer.recency_days or 30,  # Default if None
                    float(customer.average_order_value),
                    customer.loyalty_score
                ]
                
                features.append(feature_vector)
                clv_values.append(float(customer.customer_lifetime_value))
            
            # Train simple linear regression for CLV prediction
            X = np.array(features)
            y = np.array(clv_values)
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict CLV for new customers (using averages)
            avg_features = np.mean(X, axis=0)
            predicted_clv = model.predict(avg_features.reshape(1, -1))[0]
            
            # Analyze customer segments
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
            
            # Calculate averages
            for segment in segments:
                count = segments[segment]['count']
                segments[segment]['avg_clv'] = segments[segment]['total_clv'] / count
                segments[segment]['avg_frequency'] = segments[segment]['avg_frequency'] / count
                segments[segment]['avg_loyalty'] = segments[segment]['avg_loyalty'] / count
            
            # Save customer insights model
            clv_model = PredictiveModel(
                model_name='Customer Lifetime Value Model',
                model_type='customer_clv',
                algorithm='linear_regression',
                target_variable='customer_lifetime_value',
                training_start_date=datetime.now() - timedelta(days=365),
                training_end_date=datetime.now(),
                training_data_size=len(features)
            )
            
            model_params = {
                'coefficients': model.coef_.tolist(),
                'intercept': float(model.intercept_),
                'feature_names': ['frequency', 'recency', 'avg_order_value', 'loyalty_score'],
                'predicted_clv': float(predicted_clv),
                'segments': segments
            }
            
            clv_model.model_data = json.dumps(model_params)
            clv_model.update_performance_metrics(
                accuracy_score=model.score(X, y),
                r2_score=model.score(X, y),
                mae=mean_absolute_error(y, model.predict(X)),
                rmse=np.sqrt(np.mean((y - model.predict(X)) ** 2))
            )
            
            db.session.add(clv_model)
            db.session.commit()
            
            return {
                'predicted_new_customer_clv': float(predicted_clv),
                'customer_segments': segments,
                'model_performance': {
                    'r2_score': model.score(X, y),
                    'mae': mean_absolute_error(y, model.predict(X))
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing customer lifetime value: {str(e)}")
            return {}
    
    def identify_anomalies(self, metric_type='sales', metric_name='daily_revenue', days=30):
        """Identify anomalies in business metrics"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            data = AnalyticsData.query.filter(
                AnalyticsData.metric_type == metric_type,
                AnalyticsData.metric_name == metric_name,
                AnalyticsData.period_start >= start_date,
                AnalyticsData.period_end <= end_date
            ).order_by(AnalyticsData.period_start).all()
            
            if len(data) < 10:
                return []
            
            values = [float(d.metric_value) for d in data]
            
            # Calculate z-scores
            mean_val = np.mean(values)
            std_val = np.std(values)
            
            anomalies = []
            for i, data_point in enumerate(data):
                z_score = (values[i] - mean_val) / std_val if std_val > 0 else 0
                
                # Flag as anomaly if z-score > 2.5 or < -2.5
                if abs(z_score) > 2.5:
                    anomalies.append({
                        'date': data_point.period_start.strftime('%Y-%m-%d'),
                        'value': values[i],
                        'expected_value': float(mean_val),
                        'deviation': values[i] - mean_val,
                        'z_score': float(z_score),
                        'anomaly_type': 'high' if z_score > 2.5 else 'low'
                    })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error identifying anomalies: {str(e)}")
            return []
    
    def optimize_staff_scheduling(self, forecast_days=7):
        """Optimize staff scheduling based on predicted demand"""
        try:
            # Get predicted orders for each day
            demand_predictions = self.predict_demand(forecast_days=forecast_days)
            
            if not demand_predictions:
                return {}
            
            # Analyze historical order patterns by hour
            orders = Order.query.filter(
                Order.created_at >= datetime.now() - timedelta(days=30),
                Order.status == 'Completed'
            ).all()
            
            # Calculate average orders by day of week and hour
            hourly_patterns = {}
            for order in orders:
                day_of_week = order.created_at.weekday()
                hour = order.created_at.hour
                
                if day_of_week not in hourly_patterns:
                    hourly_patterns[day_of_week] = {}
                
                if hour not in hourly_patterns[day_of_week]:
                    hourly_patterns[day_of_week][hour] = []
                
                hourly_patterns[day_of_week][hour].append(1)  # Count orders
            
            # Calculate averages
            staffing_recommendations = []
            
            for pred in demand_predictions:
                date_obj = datetime.strptime(pred['date'], '%Y-%m-%d')
                day_of_week = date_obj.weekday()
                predicted_orders = pred['predicted_quantity_int']
                
                # Get historical hourly pattern for this day
                if day_of_week in hourly_patterns:
                    hour_distributions = hourly_patterns[day_of_week]
                    
                    # Calculate recommended staffing per hour
                    recommended_staff = {}
                    for hour in range(6, 24):  # Restaurant hours 6 AM to 11 PM
                        if hour in hour_distributions:
                            # Calculate percentage of daily orders at this hour
                            total_daily_orders = sum(len(orders) for orders in hour_distributions.values())
                            hour_percentage = len(hour_distributions[hour]) / total_daily_orders if total_daily_orders > 0 else 0
                            
                            # Recommend staff based on predicted demand
                            recommended_orders = predicted_orders * hour_percentage
                            
                            # Assume 1 staff member can handle 20 orders per hour
                            staff_needed = max(1, int(round(recommended_orders / 20)))
                            recommended_staff[f"{hour:02d}:00"] = staff_needed
                        else:
                            recommended_staff[f"{hour:02d}:00"] = 1  # Minimum 1 staff
                    
                    staffing_recommendations.append({
                        'date': pred['date'],
                        'predicted_orders': predicted_orders,
                        'hourly_staffing': recommended_staff,
                        'total_staff_needed': sum(recommended_staff.values())
                    })
            
            return {
                'forecast': demand_predictions,
                'staffing_recommendations': staffing_recommendations,
                'optimization_notes': [
                    'Staffing recommendations based on historical patterns and predicted demand',
                    'Assumes 1 staff member can handle 20 orders per hour',
                    'Consider actual staff skills and experience when finalizing schedules',
                    'Review and adjust based on special events or seasonal variations'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing staff scheduling: {str(e)}")
            return {}
    
    def generate_insights_report(self):
        """Generate comprehensive insights report"""
        try:
            insights = {
                'sales_forecast': self.predict_sales(forecast_days=7),
                'demand_forecast': self.predict_demand(forecast_days=7),
                'customer_analysis': self.analyze_customer_lifetime_value(),
                'anomalies': {
                    'sales': self.identify_anomalies('sales', 'daily_revenue', days=30),
                    'orders': self.identify_anomalies('orders', 'daily_order_count', days=30)
                },
                'staff_optimization': self.optimize_staff_scheduling(),
                'generated_at': datetime.now().isoformat()
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating insights report: {str(e)}")
            return {}


# Global predictive analytics instance
predictive_analytics = PredictiveAnalyticsEngine()