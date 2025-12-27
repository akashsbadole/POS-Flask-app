from datetime import datetime
from decimal import Decimal
from utils.encryption import get_encryption_manager
from . import db

class PaymentGateway(db.Model):
    """Payment Gateway configuration model"""
    __tablename__ = 'payment_gateways'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # razorpay, stripe
    display_name = db.Column(db.String(100), nullable=False)
    is_enabled = db.Column(db.Boolean, default=False)
    is_test_mode = db.Column(db.Boolean, default=True)
    
    # Configuration fields (encrypted)
    api_key_encrypted = db.Column(db.Text, nullable=True)
    secret_key_encrypted = db.Column(db.Text, nullable=True)
    webhook_secret_encrypted = db.Column(db.Text, nullable=True)
    additional_config_encrypted = db.Column(db.Text, nullable=True)  # JSON config
    
    # Gateway-specific settings
    supported_currencies = db.Column(db.Text, nullable=True)  # Comma-separated
    supported_payment_methods = db.Column(db.Text, nullable=True)  # JSON array
    transaction_fee_percentage = db.Column(db.Numeric(5, 4), default=0)  # e.g., 0.029 for 2.9%
    transaction_fee_fixed = db.Column(db.Numeric(10, 2), default=0)
    
    # Limits and restrictions
    min_amount = db.Column(db.Numeric(10, 2), default=1)
    max_amount = db.Column(db.Numeric(10, 2), nullable=True)
    daily_transaction_limit = db.Column(db.Numeric(12, 2), nullable=True)
    monthly_transaction_limit = db.Column(db.Numeric(12, 2), nullable=True)
    
    # Status tracking
    last_transaction_at = db.Column(db.DateTime, nullable=True)
    total_transactions_today = db.Column(db.Integer, default=0)
    total_amount_today = db.Column(db.Numeric(12, 2), default=0)
    is_suspended = db.Column(db.Boolean, default=False)
    suspension_reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('PaymentTransaction', backref='gateway', lazy=True)
    
    def __init__(self, name, display_name, is_enabled=False, is_test_mode=True):
        self.name = name.lower()
        self.display_name = display_name
        self.is_enabled = is_enabled
        self.is_test_mode = is_test_mode
    
    @property
    def api_key(self):
        """Get decrypted API key"""
        if not self.api_key_encrypted:
            return None
        return get_encryption_manager().decrypt_field(self.api_key_encrypted)
    
    @api_key.setter
    def api_key(self, value):
        """Set encrypted API key"""
        if value:
            self.api_key_encrypted = get_encryption_manager().encrypt_field(value)
        else:
            self.api_key_encrypted = None
    
    @property
    def secret_key(self):
        """Get decrypted secret key"""
        if not self.secret_key_encrypted:
            return None
        return get_encryption_manager().decrypt_field(self.secret_key_encrypted)
    
    @secret_key.setter
    def secret_key(self, value):
        """Set encrypted secret key"""
        if value:
            self.secret_key_encrypted = get_encryption_manager().encrypt_field(value)
        else:
            self.secret_key_encrypted = None
    
    @property
    def webhook_secret(self):
        """Get decrypted webhook secret"""
        if not self.webhook_secret_encrypted:
            return None
        return get_encryption_manager().decrypt_field(self.webhook_secret_encrypted)
    
    @webhook_secret.setter
    def webhook_secret(self, value):
        """Set encrypted webhook secret"""
        if value:
            self.webhook_secret_encrypted = get_encryption_manager().encrypt_field(value)
        else:
            self.webhook_secret_encrypted = None
    
    @property
    def additional_config(self):
        """Get decrypted additional config"""
        if not self.additional_config_encrypted:
            return {}
        try:
            import json
            return json.loads(get_encryption_manager().decrypt_field(self.additional_config_encrypted))
        except:
            return {}
    
    @additional_config.setter
    def additional_config(self, value):
        """Set encrypted additional config"""
        if value:
            import json
            config_str = json.dumps(value)
            self.additional_config_encrypted = get_encryption_manager().encrypt_field(config_str)
        else:
            self.additional_config_encrypted = None
    
    def get_supported_payment_methods(self):
        """Get supported payment methods as list"""
        if not self.supported_payment_methods:
            return []
        try:
            import json
            return json.loads(self.supported_payment_methods)
        except:
            return []
    
    def set_supported_payment_methods(self, methods):
        """Set supported payment methods"""
        import json
        self.supported_payment_methods = json.dumps(methods)
    
    def get_supported_currencies(self):
        """Get supported currencies as list"""
        if not self.supported_currencies:
            return ['INR']  # Default to INR
        return [c.strip() for c in self.supported_currencies.split(',')]
    
    def set_supported_currencies(self, currencies):
        """Set supported currencies"""
        if isinstance(currencies, list):
            self.supported_currencies = ','.join(currencies)
        else:
            self.supported_currencies = currencies
    
    def calculate_transaction_fee(self, amount):
        """Calculate transaction fee for given amount"""
        percentage_fee = amount * (self.transaction_fee_percentage / 100)
        return percentage_fee + self.transaction_fee_fixed
    
    def check_transaction_limits(self, amount):
        """Check if transaction amount is within limits"""
        if self.min_amount and amount < self.min_amount:
            return False, f"Minimum amount is {self.min_amount}"
        
        if self.max_amount and amount > self.max_amount:
            return False, f"Maximum amount is {self.max_amount}"
        
        if self.daily_transaction_limit and self.total_amount_today + amount > self.daily_transaction_limit:
            return False, "Daily transaction limit exceeded"
        
        return True, "OK"
    
    def update_daily_stats(self, amount):
        """Update daily transaction statistics"""
        self.total_transactions_today += 1
        self.total_amount_today += amount
        self.last_transaction_at = datetime.utcnow()
    
    def reset_daily_stats(self):
        """Reset daily statistics (called daily)"""
        self.total_transactions_today = 0
        self.total_amount_today = Decimal('0')
    
    def suspend(self, reason):
        """Suspend gateway with reason"""
        self.is_suspended = True
        self.suspension_reason = reason
        self.is_enabled = False
    
    def unsuspend(self):
        """Unsuspend gateway"""
        self.is_suspended = False
        self.suspension_reason = None
    
    def to_dict(self):
        """Convert gateway to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'is_enabled': self.is_enabled,
            'is_test_mode': self.is_test_mode,
            'supported_currencies': self.get_supported_currencies(),
            'supported_payment_methods': self.get_supported_payment_methods(),
            'transaction_fee_percentage': float(self.transaction_fee_percentage),
            'transaction_fee_fixed': float(self.transaction_fee_fixed),
            'min_amount': float(self.min_amount) if self.min_amount else None,
            'max_amount': float(self.max_amount) if self.max_amount else None,
            'daily_transaction_limit': float(self.daily_transaction_limit) if self.daily_transaction_limit else None,
            'monthly_transaction_limit': float(self.monthly_transaction_limit) if self.monthly_transaction_limit else None,
            'is_suspended': self.is_suspended,
            'suspension_reason': self.suspension_reason,
            'last_transaction_at': self.last_transaction_at.isoformat() if self.last_transaction_at else None,
            'total_transactions_today': self.total_transactions_today,
            'total_amount_today': float(self.total_amount_today),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_by_name(name):
        """Get gateway by name"""
        return PaymentGateway.query.filter_by(name=name.lower()).first()
    
    @staticmethod
    def get_enabled_gateways():
        """Get all enabled gateways"""
        return PaymentGateway.query.filter_by(is_enabled=True, is_suspended=False).all()
    
    @staticmethod
    def create_gateway(name, display_name, **kwargs):
        """Create new gateway"""
        gateway = PaymentGateway(name, display_name, **kwargs)
        db.session.add(gateway)
        db.session.commit()
        return gateway
    
    def __repr__(self):
        return f'<PaymentGateway {self.name}>'


class PaymentTransaction(db.Model):
    """Payment Transaction model for tracking gateway transactions"""
    __tablename__ = 'payment_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=False)
    gateway_id = db.Column(db.Integer, db.ForeignKey('payment_gateways.id'), nullable=False)
    
    # Gateway transaction identifiers
    gateway_transaction_id = db.Column(db.String(200), nullable=True)  # Razorpay payment_id, Stripe charge_id
    gateway_order_id = db.Column(db.String(200), nullable=True)        # Razorpay order_id, Stripe payment_intent_id
    gateway_customer_id = db.Column(db.String(200), nullable=True)     # Gateway customer identifier
    
    # Transaction details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='INR')
    transaction_fee = db.Column(db.Numeric(10, 2), default=0)
    net_amount = db.Column(db.Numeric(10, 2), nullable=False)  # amount - transaction_fee
    
    # Payment method details (encrypted)
    payment_method_type = db.Column(db.String(50), nullable=True)  # card, upi, wallet, netbanking
    payment_method_details_encrypted = db.Column(db.Text, nullable=True)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, processing, succeeded, failed, cancelled, refunded
    gateway_status = db.Column(db.String(50), nullable=True)  # Original gateway status
    
    # Error handling
    error_code = db.Column(db.String(50), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    error_description = db.Column(db.Text, nullable=True)
    
    # Timing
    initiated_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Retry handling
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    parent_transaction_id = db.Column(db.Integer, db.ForeignKey('payment_transactions.id'), nullable=True)
    
    # Webhook handling
    webhook_received_at = db.Column(db.DateTime, nullable=True)
    webhook_data_encrypted = db.Column(db.Text, nullable=True)
    webhook_processed = db.Column(db.Boolean, default=False)
    
    # Metadata
    metadata_encrypted = db.Column(db.Text, nullable=True)  # Additional transaction metadata
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_transaction = db.relationship('PaymentTransaction', remote_side=[id], backref='retry_transactions')
    
    def __init__(self, payment_id, gateway_id, amount, currency='INR'):
        self.payment_id = payment_id
        self.gateway_id = gateway_id
        self.amount = Decimal(str(amount))
        self.currency = currency.upper()
        self.net_amount = self.amount
    
    @property
    def payment_method_details(self):
        """Get decrypted payment method details"""
        if not self.payment_method_details_encrypted:
            return {}
        try:
            import json
            return json.loads(get_encryption_manager().decrypt_field(self.payment_method_details_encrypted))
        except:
            return {}
    
    @payment_method_details.setter
    def payment_method_details(self, value):
        """Set encrypted payment method details"""
        if value:
            import json
            details_str = json.dumps(value)
            self.payment_method_details_encrypted = get_encryption_manager().encrypt_field(details_str)
        else:
            self.payment_method_details_encrypted = None
    
    @property
    def transaction_metadata(self):
        """Get decrypted transaction metadata"""
        if not self.metadata_encrypted:
            return {}
        try:
            import json
            return json.loads(get_encryption_manager().decrypt_field(self.metadata_encrypted))
        except:
            return {}
    
    @transaction_metadata.setter
    def transaction_metadata(self, value):
        """Set encrypted transaction metadata"""
        if value:
            import json
            metadata_str = json.dumps(value)
            self.metadata_encrypted = get_encryption_manager().encrypt_field(metadata_str)
        else:
            self.metadata_encrypted = None
    
    @property
    def webhook_data(self):
        """Get decrypted webhook data"""
        if not self.webhook_data_encrypted:
            return {}
        try:
            import json
            return json.loads(get_encryption_manager().decrypt_field(self.webhook_data_encrypted))
        except:
            return {}
    
    @webhook_data.setter
    def webhook_data(self, value):
        """Set encrypted webhook data"""
        if value:
            import json
            webhook_str = json.dumps(value)
            self.webhook_data_encrypted = get_encryption_manager().encrypt_field(webhook_str)
        else:
            self.webhook_data_encrypted = None
    
    @property
    def is_pending(self):
        """Check if transaction is pending"""
        return self.status in ['pending', 'processing']
    
    @property
    def is_succeeded(self):
        """Check if transaction succeeded"""
        return self.status == 'succeeded'
    
    @property
    def is_failed(self):
        """Check if transaction failed"""
        return self.status == 'failed'
    
    @property
    def is_cancelled(self):
        """Check if transaction was cancelled"""
        return self.status == 'cancelled'
    
    @property
    def is_refunded(self):
        """Check if transaction was refunded"""
        return self.status == 'refunded'
    
    @property
    def can_retry(self):
        """Check if transaction can be retried"""
        return self.retry_count < self.max_retries and self.status in ['failed', 'cancelled']
    
    def update_status(self, new_status, gateway_status=None, error_code=None, error_message=None, error_description=None):
        """Update transaction status"""
        old_status = self.status
        self.status = new_status
        self.gateway_status = gateway_status
        
        if error_code:
            self.error_code = error_code
        if error_message:
            self.error_message = error_message
        if error_description:
            self.error_description = error_description
        
        # Set completion time
        if new_status in ['succeeded', 'failed', 'cancelled', 'refunded']:
            self.completed_at = datetime.utcnow()
        
        # Update gateway stats if successful
        if old_status in ['pending', 'processing'] and new_status == 'succeeded':
            gateway = self.gateway
            if gateway:
                gateway.update_daily_stats(self.amount)
        
        db.session.commit()
    
    def mark_succeeded(self, gateway_status=None):
        """Mark transaction as succeeded"""
        self.update_status('succeeded', gateway_status)
    
    def mark_failed(self, error_code=None, error_message=None, error_description=None):
        """Mark transaction as failed"""
        self.update_status('failed', error_code=error_code, error_message=error_message, error_description=error_description)
    
    def mark_cancelled(self, error_code=None, error_message=None, error_description=None):
        """Mark transaction as cancelled"""
        self.update_status('cancelled', error_code=error_code, error_message=error_message, error_description=error_description)
    
    def mark_refunded(self):
        """Mark transaction as refunded"""
        self.update_status('refunded')
    
    def retry(self):
        """Create retry transaction"""
        if not self.can_retry:
            return None
        
        retry_transaction = PaymentTransaction(
            payment_id=self.payment_id,
            gateway_id=self.gateway_id,
            amount=self.amount,
            currency=self.currency
        )
        retry_transaction.retry_count = self.retry_count + 1
        retry_transaction.parent_transaction_id = self.id
        
        # Copy metadata
        retry_transaction.transaction_metadata = self.transaction_metadata.copy()
        
        db.session.add(retry_transaction)
        db.session.commit()
        
        return retry_transaction
    
    def set_webhook_data(self, webhook_data):
        """Set webhook data and mark as processed"""
        self.webhook_data = webhook_data
        self.webhook_received_at = datetime.utcnow()
        self.webhook_processed = True
        db.session.commit()
    
    def to_dict(self):
        """Convert transaction to dictionary"""
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'gateway_id': self.gateway_id,
            'gateway_name': self.gateway.name if self.gateway else None,
            'gateway_transaction_id': self.gateway_transaction_id,
            'gateway_order_id': self.gateway_order_id,
            'gateway_customer_id': self.gateway_customer_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'transaction_fee': float(self.transaction_fee),
            'net_amount': float(self.net_amount),
            'payment_method_type': self.payment_method_type,
            'payment_method_details': self.payment_method_details,
            'status': self.status,
            'gateway_status': self.gateway_status,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'error_description': self.error_description,
            'is_pending': self.is_pending,
            'is_succeeded': self.is_succeeded,
            'is_failed': self.is_failed,
            'is_cancelled': self.is_cancelled,
            'is_refunded': self.is_refunded,
            'can_retry': self.can_retry,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'parent_transaction_id': self.parent_transaction_id,
            'webhook_received_at': self.webhook_received_at.isoformat() if self.webhook_received_at else None,
            'webhook_processed': self.webhook_processed,
            'metadata': self.transaction_metadata,
            'initiated_at': self.initiated_at.isoformat() if self.initiated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_by_gateway_transaction_id(gateway_transaction_id):
        """Get transaction by gateway transaction ID"""
        return PaymentTransaction.query.filter_by(gateway_transaction_id=gateway_transaction_id).first()
    
    @staticmethod
    def get_by_payment(payment_id):
        """Get all transactions for a payment"""
        return PaymentTransaction.query.filter_by(payment_id=payment_id).order_by(PaymentTransaction.created_at).all()
    
    @staticmethod
    def get_pending_transactions():
        """Get all pending transactions"""
        return PaymentTransaction.query.filter(PaymentTransaction.status.in_(['pending', 'processing'])).all()
    
    @staticmethod
    def create_transaction(payment_id, gateway_id, amount, currency='INR'):
        """Create new transaction"""
        transaction = PaymentTransaction(payment_id, gateway_id, amount, currency)
        db.session.add(transaction)
        db.session.commit()
        return transaction
    
    def __repr__(self):
        return f'<PaymentTransaction {self.gateway_transaction_id or "NoID"} ({self.status})>'