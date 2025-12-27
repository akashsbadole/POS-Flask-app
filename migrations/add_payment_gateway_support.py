"""
Migration: Add Payment Gateway Support
Adds payment gateway and transaction tables to support Razorpay and Stripe integration
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Numeric, Text, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Get database URL from environment or use default
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///restaurant_pos.db')

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class PaymentGateway(Base):
    """Payment Gateway configuration table"""
    __tablename__ = 'payment_gateways'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)  # razorpay, stripe
    display_name = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=False)
    is_test_mode = Column(Boolean, default=True)
    
    # Configuration fields (encrypted)
    api_key_encrypted = Column(Text, nullable=True)
    secret_key_encrypted = Column(Text, nullable=True)
    webhook_secret_encrypted = Column(Text, nullable=True)
    additional_config_encrypted = Column(Text, nullable=True)  # JSON config
    
    # Gateway-specific settings
    supported_currencies = Column(Text, nullable=True)  # Comma-separated
    supported_payment_methods = Column(Text, nullable=True)  # JSON array
    transaction_fee_percentage = Column(Numeric(5, 4), default=0)  # e.g., 0.029 for 2.9%
    transaction_fee_fixed = Column(Numeric(10, 2), default=0)
    
    # Limits and restrictions
    min_amount = Column(Numeric(10, 2), default=1)
    max_amount = Column(Numeric(10, 2), nullable=True)
    daily_transaction_limit = Column(Numeric(12, 2), nullable=True)
    monthly_transaction_limit = Column(Numeric(12, 2), nullable=True)
    
    # Status tracking
    last_transaction_at = Column(DateTime, nullable=True)
    total_transactions_today = Column(Integer, default=0)
    total_amount_today = Column(Numeric(12, 2), default=0)
    is_suspended = Column(Boolean, default=False)
    suspension_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentTransaction(Base):
    """Payment Transaction table for tracking gateway transactions"""
    __tablename__ = 'payment_transactions'
    
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=False)
    gateway_id = Column(Integer, ForeignKey('payment_gateways.id'), nullable=False)
    
    # Gateway transaction identifiers
    gateway_transaction_id = Column(String(200), nullable=True)  # Razorpay payment_id, Stripe charge_id
    gateway_order_id = Column(String(200), nullable=True)        # Razorpay order_id, Stripe payment_intent_id
    gateway_customer_id = Column(String(200), nullable=True)     # Gateway customer identifier
    
    # Transaction details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default='INR')
    transaction_fee = Column(Numeric(10, 2), default=0)
    net_amount = Column(Numeric(10, 2), nullable=False)  # amount - transaction_fee
    
    # Payment method details (encrypted)
    payment_method_type = Column(String(50), nullable=True)  # card, upi, wallet, netbanking
    payment_method_details_encrypted = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String(20), default='pending')  # pending, processing, succeeded, failed, cancelled, refunded
    gateway_status = Column(String(50), nullable=True)  # Original gateway status
    
    # Error handling
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    error_description = Column(Text, nullable=True)
    
    # Timing
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Retry handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    parent_transaction_id = Column(Integer, ForeignKey('payment_transactions.id'), nullable=True)
    
    # Webhook handling
    webhook_received_at = Column(DateTime, nullable=True)
    webhook_data_encrypted = Column(Text, nullable=True)
    webhook_processed = Column(Boolean, default=False)
    
    # Metadata
    metadata_encrypted = Column(Text, nullable=True)  # Additional transaction metadata
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Add indexes for performance
Index('idx_payment_gateway_name', PaymentGateway.name)
Index('idx_payment_transaction_payment_id', PaymentTransaction.payment_id)
Index('idx_payment_transaction_gateway_id', PaymentTransaction.gateway_id)
Index('idx_payment_transaction_status', PaymentTransaction.status)
Index('idx_payment_transaction_gateway_transaction_id', PaymentTransaction.gateway_transaction_id)
Index('idx_payment_transaction_created_at', PaymentTransaction.created_at)


def upgrade():
    """Create new tables"""
    Base.metadata.create_all(engine)
    
    # Create session to insert initial data
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create default gateways
        razorpay_gateway = PaymentGateway(
            name='razorpay',
            display_name='Razorpay',
            is_enabled=False,
            is_test_mode=True,
            supported_currencies='INR',
            supported_payment_methods='["card", "upi", "wallet", "netbanking"]',
            transaction_fee_percentage=0.029,  # 2.9%
            transaction_fee_fixed=0,
            min_amount=1,
            max_amount=100000
        )
        
        stripe_gateway = PaymentGateway(
            name='stripe',
            display_name='Stripe',
            is_enabled=False,
            is_test_mode=True,
            supported_currencies='INR,USD,EUR',
            supported_payment_methods='["card", "upi", "wallet"]',
            transaction_fee_percentage=0.029,  # 2.9%
            transaction_fee_fixed=0,
            min_amount=1,
            max_amount=100000
        )
        
        session.add(razorpay_gateway)
        session.add(stripe_gateway)
        
        session.commit()
        print("✅ Payment gateway tables created successfully")
        print("✅ Default gateways (Razorpay, Stripe) added")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating payment gateway tables: {e}")
        raise
    finally:
        session.close()


def downgrade():
    """Drop new tables"""
    try:
        PaymentTransaction.__table__.drop(engine)
        PaymentGateway.__table__.drop(engine)
        print("✅ Payment gateway tables dropped successfully")
    except Exception as e:
        print(f"❌ Error dropping payment gateway tables: {e}")
        raise


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'upgrade':
            upgrade()
        elif command == 'downgrade':
            downgrade()
        else:
            print("Usage: python add_payment_gateway_support.py [upgrade|downgrade]")
    else:
        print("Usage: python add_payment_gateway_support.py [upgrade|downgrade]")