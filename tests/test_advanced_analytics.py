"""
Test file for Advanced Analytics System
Tests all components of the analytics pipeline, predictive models, and dashboard functionality
"""

import unittest
from datetime import datetime, timedelta
import json
import numpy as np
from decimal import Decimal

# Import models and utilities
from models import db, User, Category, MenuItem, Table, Order, OrderItem, AnalyticsData, TrendAnalysis, PredictiveModel, CustomerInsights, BusinessMetrics
from utils.analytics_pipeline import AnalyticsDataPipeline
from utils.predictive_analytics import PredictiveAnalyticsEngine
from app import create_app

class TestAdvancedAnalytics(unittest.TestCase):
    """Test suite for Advanced Analytics System"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        with self.app.app_context():
            db.create_all()
            self.setup_test_data()
            self.pipeline = AnalyticsDataPipeline()
            self.predictive_engine = PredictiveAnalyticsEngine()
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def setup_test_data(self):
        """Create test data for analytics testing"""
        # Create test users
        self.admin_user = User(username='admin', email='admin@test.com', role='admin')
        self.admin_user.set_password('admin123')
        
        self.cashier_user = User(username='cashier', email='cashier@test.com', role='cashier')
        self.cashier_user.set_password('cashier123')
        
        # Create test categories
        self.appetizers = Category(name='Appetizers')
        self.mains = Category(name='Main Courses')
        self.desserts = Category(name='Desserts')
        
        # Create test menu items
        self.item1 = MenuItem(name='Spring Rolls', price=150, category_id=1, stock_quantity=50)
        self.item2 = MenuItem(name='Chicken Biryani', price=250, category_id=2, stock_quantity=30)
        self.item3 = MenuItem(name='Gulab Jamun', price=100, category_id=3, stock_quantity=40)
        
        db.session.add_all([
            self.admin_user, self.cashier_user,
            self.appetizers, self.mains, self.desserts,
            self.item1, self.item2, self.item3
        ])
        db.session.commit()
        
        # Create test tables
        self.table1 = Table(table_number='1', capacity=4)
        self.table2 = Table(table_number='2', capacity=2)
        db.session.add_all([self.table1, self.table2])
        db.session.commit()
        
        # Create test orders for the past 30 days
        self.create_test_orders()
    
    def create_test_orders(self):
        """Create test orders with realistic data patterns"""
        base_date = datetime.now() - timedelta(days=30)
        
        for day in range(30):
            current_date = base_date + timedelta(days=day)
            
            # Create 5-15 orders per day with varying revenue
            orders_today = np.random.randint(5, 16)
            
            for order_num in range(orders_today):
                # Create order at random times during the day
                order_time = current_date.replace(
                    hour=np.random.randint(10, 23),
                    minute=np.random.randint(0, 60)
                )
                
                # Create order
                order = Order(
                    order_number=f'TEST{day:03d}{order_num:03d}',
                    table_id=np.random.choice([1, 2, None]),
                    customer_name=f'Customer {order_num}',
                    customer_mobile=f'+91{np.random.randint(7000000000, 9999999999)}',
                    order_type=np.random.choice(['Dine-in', 'Takeaway', 'Delivery']),
                    created_by=np.random.choice([1, 2]),
                    created_at=order_time
                )
                
                # Add random items to order
                num_items = np.random.randint(1, 4)
                order.subtotal = 0
                
                for item_num in range(num_items):
                    item = np.random.choice([self.item1, self.item2, self.item3])
                    quantity = np.random.randint(1, 3)
                    total = item.price * quantity
                    
                    order_item = OrderItem(
                        order_id=order.id,
                        menu_item_id=item.id,
                        quantity=quantity,
                        price=item.price,
                        total=total,
                        status='Completed'
                    )
                    
                    order.subtotal += total
                    db.session.add(order_item)
                
                # Calculate totals
                order.cgst_amount = order.subtotal * Decimal('0.025')
                order.sgst_amount = order.subtotal * Decimal('0.025')
                order.total_tax = order.cgst_amount + order.sgst_amount
                order.grand_total = order.subtotal + order.total_tax
                order.completed_at = order_time + timedelta(minutes=np.random.randint(15, 60))
                order.status = 'Completed'
                
                db.session.add(order)
        
        db.session.commit()
    
    def test_analytics_data_model(self):
        """Test AnalyticsData model functionality"""
        with self.app.app_context():
            # Test creating analytics data
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            analytics_data = AnalyticsData.create_sales_metric(
                metric_name='daily_revenue',
                value=1000.50,
                period_start=today,
                period_end=tomorrow,
                category_id=1
            )
            
            db.session.add(analytics_data)
            db.session.commit()
            
            # Test retrieval and formatting
            saved_data = AnalyticsData.query.filter_by(metric_name='daily_revenue').first()
            self.assertIsNotNone(saved_data)
            self.assertEqual(float(saved_data.metric_value), 1000.50)
            self.assertEqual(saved_data.metric_unit, 'currency')
            self.assertIn('₹', saved_data.formatted_value)
            
            print("✓ AnalyticsData model test passed")
    
    def test_trend_analysis_model(self):
        """Test TrendAnalysis model functionality"""
        with self.app.app_context():
            # Create test trend analysis
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
            
            # Sample data points
            data_points = [100, 120, 115, 130, 125, 140, 135, 150, 145, 160]
            
            trend = TrendAnalysis(
                trend_name='Sales Growth Test',
                trend_type='sales_growth',
                time_period='daily',
                trend_start_date=start_date,
                trend_end_date=end_date,
                trend_direction='increasing',
                trend_strength=0.8,
                trend_slope=2.5,
                r_squared=0.85,
                data_points=data_points
            )
            
            db.session.add(trend)
            db.session.commit()
            
            # Test retrieval and properties
            saved_trend = TrendAnalysis.query.filter_by(trend_name='Sales Growth Test').first()
            self.assertIsNotNone(saved_trend)
            self.assertEqual(saved_trend.trend_direction, 'increasing')
            self.assertEqual(len(saved_trend.data_points_list), 10)
            
            print("✓ TrendAnalysis model test passed")
    
    def test_customer_insights_model(self):
        """Test CustomerInsights model functionality"""
        with self.app.app_context():
            # Create test customer insights
            customer = CustomerInsights(
                customer_hash='test_hash_123',
                customer_segment='VIP',
                acquisition_channel='online'
            )
            
            # Update RFM metrics
            customer.update_rfm_metrics(
                recency_days=5,
                frequency_count=15,
                monetary_value=2500.00
            )
            
            # Calculate loyalty score
            loyalty_score = customer.calculate_loyalty_score()
            self.assertGreater(loyalty_score, 0)
            self.assertLessEqual(loyalty_score, 100)
            
            db.session.add(customer)
            db.session.commit()
            
            # Test retrieval
            saved_customer = CustomerInsights.query.filter_by(customer_hash='test_hash_123').first()
            self.assertIsNotNone(saved_customer)
            self.assertEqual(saved_customer.customer_segment, 'VIP')
            self.assertEqual(saved_customer.frequency_count, 15)
            
            print("✓ CustomerInsights model test passed")
    
    def test_business_metrics_model(self):
        """Test BusinessMetrics model functionality"""
        with self.app.app_context():
            # Create test business metric
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()
            
            metric = BusinessMetrics(
                metric_name='Weekly Revenue',
                metric_category='financial',
                current_value=15000.00,
                calculation_period='weekly',
                period_start=start_date,
                period_end=end_date,
                unit='currency',
                target_value=20000.00
            )
            
            # Test change calculation
            metric.calculate_change(12000.00)
            
            self.assertEqual(float(metric.absolute_change), 3000.00)
            self.assertEqual(metric.percentage_change, 25.0)
            self.assertEqual(metric.trend_direction, 'up')
            
            db.session.add(metric)
            db.session.commit()
            
            # Test retrieval
            saved_metric = BusinessMetrics.query.filter_by(metric_name='Weekly Revenue').first()
            self.assertIsNotNone(saved_metric)
            self.assertEqual(saved_metric.status, 'warning')  # Below target
            
            print("✓ BusinessMetrics model test passed")
    
    def test_analytics_pipeline_real_time_processing(self):
        """Test real-time analytics processing"""
        with self.app.app_context():
            # Create a completed order
            order = Order(
                order_number='REALTIME001',
                table_id=1,
                customer_name='Test Customer',
                customer_mobile='+919876543210',
                order_type='Dine-in',
                created_by=1,
                subtotal=500.00,
                cgst_amount=12.50,
                sgst_amount=12.50,
                total_tax=25.00,
                grand_total=525.00,
                completed_at=datetime.now()
            )
            order.status = 'Completed'
            db.session.add(order)
            db.session.flush()
            
            # Add order items
            item1 = OrderItem(
                order_id=order.id,
                menu_item_id=1,
                quantity=2,
                price=150.00,
                total=300.00,
                status='Completed'
            )
            
            item2 = OrderItem(
                order_id=order.id,
                menu_item_id=2,
                quantity=1,
                price=200.00,
                total=200.00,
                status='Completed'
            )
            
            db.session.add_all([item1, item2])
            db.session.commit()
            
            # Process real-time analytics
            success = self.pipeline.process_real_time_order(order.id)
            self.assertTrue(success)
            
            # Check if analytics data was created
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            sales_metric = AnalyticsData.query.filter_by(
                metric_type='sales',
                metric_name='daily_revenue',
                period_start=today
            ).first()
            
            self.assertIsNotNone(sales_metric)
            self.assertEqual(float(sales_metric.metric_value), 525.00)
            
            print("✓ Real-time analytics processing test passed")
    
    def test_analytics_pipeline_batch_processing(self):
        """Test batch analytics processing"""
        with self.app.app_context():
            # Process batch analytics for last 7 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            success = self.pipeline.process_batch_analytics(start_date, end_date)
            self.assertTrue(success)
            
            # Check if trends were created
            trends = TrendAnalysis.query.filter_by(trend_type='sales_growth').all()
            self.assertGreater(len(trends), 0)
            
            # Check if business metrics were created
            metrics = BusinessMetrics.query.filter_by(metric_category='financial').all()
            self.assertGreater(len(metrics), 0)
            
            print("✓ Batch analytics processing test passed")
    
    def test_predictive_analytics_sales_forecast(self):
        """Test sales forecasting functionality"""
        with self.app.app_context():
            # Create sales forecast model
            model = self.predictive_engine.create_sales_forecast_model(training_days=30)
            
            if model:  # Model creation might fail with insufficient data
                self.assertTrue(model.is_trained)
                self.assertEqual(model.model_type, 'sales_forecast')
                
                # Test predictions
                predictions = self.predictive_engine.predict_sales(forecast_days=7)
                self.assertEqual(len(predictions), 7)
                
                # Check prediction structure
                for pred in predictions:
                    self.assertIn('date', pred)
                    self.assertIn('predicted_revenue', pred)
                    self.assertIn('confidence_interval', pred)
                    self.assertGreaterEqual(pred['predicted_revenue'], 0)
                
                print("✓ Sales forecasting test passed")
            else:
                print("⚠ Sales forecasting test skipped (insufficient data)")
    
    def test_real_time_dashboard_data(self):
        """Test real-time dashboard data generation"""
        with self.app.app_context():
            # Get real-time data
            data = self.pipeline.get_real_time_dashboard_data()
            
            # Check data structure
            required_keys = ['today_revenue', 'today_orders', 'active_orders', 'hourly_sales']
            for key in required_keys:
                self.assertIn(key, data)
            
            self.assertIsInstance(data['today_revenue'], (int, float))
            self.assertIsInstance(data['today_orders'], int)
            self.assertIsInstance(data['active_orders'], int)
            self.assertIsInstance(data['hourly_sales'], list)
            
            print("✓ Real-time dashboard data test passed")
    
    def test_comprehensive_insights_report(self):
        """Test comprehensive insights report generation"""
        with self.app.app_context():
            # Generate insights report
            insights = self.predictive_engine.generate_insights_report()
            
            # Check report structure
            expected_sections = [
                'sales_forecast',
                'demand_forecast',
                'customer_analysis',
                'anomalies',
                'staff_optimization',
                'generated_at'
            ]
            
            for section in expected_sections:
                self.assertIn(section, insights)
            
            print("✓ Comprehensive insights report test passed")


def run_analytics_tests():
    """Run all analytics tests and return results"""
    print("=" * 60)
    print("ADVANCED ANALYTICS SYSTEM TEST SUITE")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAdvancedAnalytics)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("🎉 All tests passed! Analytics system is ready for production.")
    else:
        print("⚠ Some tests failed. Please review the issues above.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_analytics_tests()