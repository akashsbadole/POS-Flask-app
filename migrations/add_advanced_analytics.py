"""
Database Migration for Advanced Analytics System
Creates tables for AnalyticsData, TrendAnalysis, PredictiveModel, CustomerInsights, and BusinessMetrics
"""

from datetime import datetime, timedelta
from models import db, AnalyticsData, TrendAnalysis, PredictiveModel, CustomerInsights, BusinessMetrics

def create_analytics_tables():
    """Create all analytics-related database tables"""
    try:
        # Create analytics_data table
        db.create_all()
        
        # Create indexes for better performance
        create_analytics_indexes()
        
        print("✓ Analytics tables created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error creating analytics tables: {str(e)}")
        return False

def create_analytics_indexes():
    """Create indexes for analytics tables to improve query performance"""
    
    # AnalyticsData indexes
    try:
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_data_type_name 
            ON analytics_data (metric_type, metric_name)
        """)
        
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_data_period 
            ON analytics_data (period_start, period_end)
        """)
        
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_data_menu_item 
            ON analytics_data (menu_item_id)
        """)
        
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_data_user 
            ON analytics_data (user_id)
        """)
        
        print("✓ AnalyticsData indexes created")
        
    except Exception as e:
        print(f"Warning: Could not create AnalyticsData indexes: {str(e)}")
    
    # TrendAnalysis indexes
    try:
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_trend_analysis_type 
            ON trend_analysis (trend_type)
        """)
        
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_trend_analysis_period 
            ON trend_analysis (trend_start_date, trend_end_date)
        """)
        
        print("✓ TrendAnalysis indexes created")
        
    except Exception as e:
        print(f"Warning: Could not create TrendAnalysis indexes: {str(e)}")
    
    # PredictiveModel indexes
    try:
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_predictive_model_type 
            ON predictive_models (model_type)
        """)
        
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_predictive_model_active 
            ON predictive_models (is_active, is_trained)
        """)
        
        print("✓ PredictiveModel indexes created")
        
    except Exception as e:
        print(f"Warning: Could not create PredictiveModel indexes: {str(e)}")
    
    # CustomerInsights indexes
    try:
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_insights_segment 
            ON customer_insights (customer_segment)
        """)
        
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_insights_clv 
            ON customer_insights (customer_lifetime_value)
        """)
        
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_insights_churn_risk 
            ON customer_insights (churn_risk_score)
        """)
        
        print("✓ CustomerInsights indexes created")
        
    except Exception as e:
        print(f"Warning: Could not create CustomerInsights indexes: {str(e)}")
    
    # BusinessMetrics indexes
    try:
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_business_metrics_category 
            ON business_metrics (metric_category)
        """)
        
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_business_metrics_status 
            ON business_metrics (status)
        """)
        
        db.engine.execute("""
            CREATE INDEX IF NOT EXISTS idx_business_metrics_period 
            ON business_metrics (period_start, period_end)
        """)
        
        print("✓ BusinessMetrics indexes created")
        
    except Exception as e:
        print(f"Warning: Could not create BusinessMetrics indexes: {str(e)}")

def initialize_sample_data():
    """Initialize sample analytics data for testing and demonstration"""
    try:
        print("Initializing sample analytics data...")
        
        # Create sample analytics data
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Sample sales data for the past 30 days
        for i in range(30):
            date_start = today - timedelta(days=i)
            date_end = date_start + timedelta(days=1)
            
            # Daily revenue
            daily_revenue = AnalyticsData.create_sales_metric(
                metric_name='daily_revenue',
                value=1000 + (i * 50) + (i % 7 * 100),  # Growing trend with weekly patterns
                period_start=date_start,
                period_end=date_end
            )
            db.session.add(daily_revenue)
            
            # Daily order count
            daily_orders = AnalyticsData.create_order_metric(
                metric_name='daily_order_count',
                value=15 + (i % 5),
                period_start=date_start,
                period_end=date_end
            )
            db.session.add(daily_orders)
        
        # Sample business metrics
        business_metric = BusinessMetrics(
            metric_name='Monthly Revenue',
            metric_category='financial',
            current_value=35000.00,
            calculation_period='monthly',
            period_start=today.replace(day=1),
            period_end=today,
            unit='currency',
            target_value=40000.00
        )
        business_metric.calculate_change(32000.00)
        db.session.add(business_metric)
        
        # Sample customer insights
        customer_insight = CustomerInsights(
            customer_hash='sample_hash_123',
            customer_segment='VIP',
            acquisition_channel='online'
        )
        customer_insight.update_rfm_metrics(
            recency_days=3,
            frequency_count=25,
            monetary_value=5500.00
        )
        customer_insight.total_orders = 25
        customer_insight.calculate_loyalty_score()
        db.session.add(customer_insight)
        
        db.session.commit()
        print("✓ Sample analytics data initialized")
        return True
        
    except Exception as e:
        print(f"✗ Error initializing sample data: {str(e)}")
        db.session.rollback()
        return False

def verify_installation():
    """Verify that all analytics tables were created successfully"""
    try:
        # Check if tables exist
        tables_to_check = [
            'analytics_data',
            'trend_analysis', 
            'predictive_models',
            'customer_insights',
            'business_metrics'
        ]
        
        for table_name in tables_to_check:
            result = db.engine.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not result.fetchone():
                print(f"✗ Table {table_name} not found")
                return False
        
        # Check table structure
        analytics_table_info = db.engine.execute("PRAGMA table_info(analytics_data)").fetchall()
        if len(analytics_table_info) < 5:
            print("✗ AnalyticsData table structure incomplete")
            return False
        
        print("✓ All analytics tables verified successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error verifying installation: {str(e)}")
        return False

def main():
    """Main migration function"""
    print("=" * 60)
    print("ADVANCED ANALYTICS SYSTEM MIGRATION")
    print("=" * 60)
    
    print("\n1. Creating analytics tables...")
    if not create_analytics_tables():
        print("Migration failed at table creation")
        return False
    
    print("\n2. Initializing sample data...")
    initialize_sample_data()
    
    print("\n3. Verifying installation...")
    if not verify_installation():
        print("Migration verification failed")
        return False
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\nAnalytics System Features Available:")
    print("• Real-time analytics data collection")
    print("• Trend analysis and pattern recognition")
    print("• Predictive analytics with ML models")
    print("• Customer insights and segmentation")
    print("• Business metrics and KPI tracking")
    print("• Interactive analytics dashboard")
    print("• Real-time WebSocket updates")
    print("• Comprehensive reporting system")
    
    return True

if __name__ == '__main__':
    main()