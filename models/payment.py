from datetime import datetime
from decimal import Decimal
from utils.encryption import get_encryption_manager
from . import db

class Payment(db.Model):
    """Payment model for order payments"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    payment_mode = db.Column(db.String(20), nullable=False)  # Cash, Card, UPI, Wallet, Razorpay, Stripe
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reference_number = db.Column(db.String(100), nullable=True)  # For card/UPI transactions
    status = db.Column(db.String(20), default='Completed')  # Completed, Pending, Failed, Refunded
    payment_details = db.Column(db.Text, nullable=True)  # Additional payment information
    
    # Gateway integration fields
    gateway_id = db.Column(db.Integer, db.ForeignKey('payment_gateways.id'), nullable=True)
    gateway_transaction_id = db.Column(db.String(200), nullable=True)
    gateway_order_id = db.Column(db.String(200), nullable=True)
    gateway_response_encrypted = db.Column(db.Text, nullable=True)
    
    # Payment method specific details
    payment_method_type = db.Column(db.String(50), nullable=True)  # card, upi, wallet, netbanking
    payment_method_details_encrypted = db.Column(db.Text, nullable=True)
    
    # Transaction timing
    authorized_at = db.Column(db.DateTime, nullable=True)
    captured_at = db.Column(db.DateTime, nullable=True)
    refunded_at = db.Column(db.DateTime, nullable=True)
    
    # Refund tracking
    refunded_amount = db.Column(db.Numeric(10, 2), default=0)
    refund_reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    gateway = db.relationship('PaymentGateway', backref='payments')
    transactions = db.relationship('PaymentTransaction', backref='payment', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, order_id, payment_mode, amount, processed_by=None,
                 reference_number=None, payment_details=None, gateway_id=None):
        self.order_id = order_id
        self.payment_mode = payment_mode
        self.amount = Decimal(str(amount))
        self.processed_by = processed_by
        self.gateway_id = gateway_id
        self.reference_number = self._encrypt_reference_number(reference_number) if reference_number else None
        self.payment_details = self._encrypt_payment_details(payment_details) if payment_details else None
    
    @property
    def formatted_amount(self):
        """Get formatted amount"""
        return f"₹{self.amount:.2f}"
    
    @property
    def is_completed(self):
        """Check if payment is completed"""
        return self.status == 'Completed'
    
    @property
    def is_pending(self):
        """Check if payment is pending"""
        return self.status == 'Pending'
    
    @property
    def is_failed(self):
        """Check if payment is failed"""
        return self.status == 'Failed'
    
    @property
    def is_refunded(self):
        """Check if payment is refunded"""
        return self.status == 'Refunded'
    
    @property
    def is_gateway_payment(self):
        """Check if payment uses a gateway"""
        return self.gateway_id is not None
    
    @property
    def is_partially_refunded(self):
        """Check if payment is partially refunded"""
        return self.refunded_amount > 0 and self.refunded_amount < self.amount
    
    @property
    def is_fully_refunded(self):
        """Check if payment is fully refunded"""
        return self.refunded_amount >= self.amount
    
    @property
    def pending_refund_amount(self):
        """Get pending refund amount"""
        return self.amount - self.refunded_amount
    
    @property
    def gateway_response(self):
        """Get decrypted gateway response"""
        if not self.gateway_response_encrypted:
            return {}
        return get_encryption_manager().decrypt_field(self.gateway_response_encrypted)
    
    @gateway_response.setter
    def gateway_response(self, value):
        """Set encrypted gateway response"""
        if value:
            import json
            response_str = json.dumps(value)
            self.gateway_response_encrypted = get_encryption_manager().encrypt_field(response_str)
        else:
            self.gateway_response_encrypted = None
    
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
    
    def update_status(self, new_status):
        """Update payment status"""
        valid_statuses = ['Completed', 'Pending', 'Failed', 'Refunded']
        if new_status not in valid_statuses:
            return False
        
        self.status = new_status
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def mark_completed(self):
        """Mark payment as completed"""
        return self.update_status('Completed')
    
    def mark_pending(self):
        """Mark payment as pending"""
        return self.update_status('Pending')
    
    def mark_failed(self):
        """Mark payment as failed"""
        return self.update_status('Failed')
    
    def mark_refunded(self, refund_amount=None, refund_reason=None):
        """Mark payment as refunded"""
        if refund_amount is not None:
            self.refunded_amount = Decimal(str(refund_amount))
        if refund_reason:
            self.refund_reason = refund_reason
        self.refunded_at = datetime.utcnow()
        return self.update_status('Refunded')
    
    def mark_partially_refunded(self, refund_amount, refund_reason=None):
        """Mark payment as partially refunded"""
        self.refunded_amount = Decimal(str(refund_amount))
        if refund_reason:
            self.refund_reason = refund_reason
        self.refunded_at = datetime.utcnow()
        # Keep status as Completed but track refund
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def to_dict(self):
        """Convert payment to dictionary"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else None,
            'payment_mode': self.payment_mode,
            'amount': float(self.amount),
            'formatted_amount': self.formatted_amount,
            'reference_number': self._decrypt_reference_number(self.reference_number),
            'status': self.status,
            'is_completed': self.is_completed,
            'is_pending': self.is_pending,
            'is_failed': self.is_failed,
            'is_refunded': self.is_refunded,
            'is_gateway_payment': self.is_gateway_payment,
            'is_partially_refunded': self.is_partially_refunded,
            'is_fully_refunded': self.is_fully_refunded,
            'pending_refund_amount': float(self.pending_refund_amount),
            'refunded_amount': float(self.refunded_amount),
            'refund_reason': self.refund_reason,
            'gateway_id': self.gateway_id,
            'gateway_name': self.gateway.name if self.gateway else None,
            'gateway_transaction_id': self.gateway_transaction_id,
            'gateway_order_id': self.gateway_order_id,
            'gateway_response': self.gateway_response,
            'payment_method_type': self.payment_method_type,
            'payment_method_details': self.payment_method_details,
            'authorized_at': self.authorized_at.isoformat() if self.authorized_at else None,
            'captured_at': self.captured_at.isoformat() if self.captured_at else None,
            'refunded_at': self.refunded_at.isoformat() if self.refunded_at else None,
            'payment_details': self._decrypt_payment_details(self.payment_details),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processed_by': self.processed_by
        }
    
    @staticmethod
    def get_by_id(payment_id):
        """Get payment by ID"""
        return Payment.query.get(payment_id)
    
    @staticmethod
    def get_by_order(order_id):
        """Get all payments for an order"""
        return Payment.query.filter_by(order_id=order_id).order_by(Payment.created_at).all()
    
    @staticmethod
    def get_completed_payments_by_order(order_id):
        """Get all completed payments for an order"""
        return Payment.query.filter_by(order_id=order_id, status='Completed').all()
    
    @staticmethod
    def create_payment(order_id, payment_mode, amount, processed_by=None, 
                     reference_number=None, payment_details=None, gateway_id=None):
        """Create new payment"""
        payment = Payment(
            order_id=order_id,
            payment_mode=payment_mode,
            amount=amount,
            processed_by=processed_by,
            reference_number=reference_number,
            payment_details=payment_details,
            gateway_id=gateway_id
        )
        db.session.add(payment)
        db.session.commit()
        return payment
    
    @staticmethod
    def create_gateway_payment(order_id, payment_mode, amount, gateway_id, 
                             gateway_transaction_id=None, gateway_order_id=None,
                             payment_method_type=None, payment_method_details=None,
                             processed_by=None):
        """Create new gateway payment"""
        payment = Payment.create_payment(
            order_id=order_id,
            payment_mode=payment_mode,
            amount=amount,
            gateway_id=gateway_id,
            processed_by=processed_by
        )
        
        # Set gateway-specific fields
        if gateway_transaction_id:
            payment.gateway_transaction_id = gateway_transaction_id
        if gateway_order_id:
            payment.gateway_order_id = gateway_order_id
        if payment_method_type:
            payment.payment_method_type = payment_method_type
        if payment_method_details:
            payment.payment_method_details = payment_method_details
        
        db.session.commit()
        return payment
    
    def update_gateway_transaction(self, gateway_transaction_id, gateway_order_id=None, 
                                 gateway_response=None, status=None):
        """Update gateway transaction details"""
        if gateway_transaction_id:
            self.gateway_transaction_id = gateway_transaction_id
        if gateway_order_id:
            self.gateway_order_id = gateway_order_id
        if gateway_response:
            self.gateway_response = gateway_response
        if status and status in ['Completed', 'Pending', 'Failed', 'Refunded']:
            self.status = status
            if status == 'Completed':
                self.captured_at = datetime.utcnow()
            elif status == 'Pending':
                self.authorized_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def process_refund(self, refund_amount, refund_reason=None, gateway_refund_id=None):
        """Process refund for this payment"""
        refund_amount = Decimal(str(refund_amount))
        
        if refund_amount > self.pending_refund_amount:
            return False, "Refund amount exceeds pending refund amount"
        
        # Update refund tracking
        self.refunded_amount += refund_amount
        if refund_reason:
            self.refund_reason = refund_reason
        
        if self.is_fully_refunded:
            self.status = 'Refunded'
            self.refunded_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        
        return True, "Refund processed successfully"
    
    @staticmethod
    def get_total_paid(order_id):
        """Get total amount paid for an order"""
        payments = Payment.get_completed_payments_by_order(order_id)
        return sum(payment.amount for payment in payments)
    
    @staticmethod
    def get_payment_summary(order_id):
        """Get payment summary for an order"""
        payments = Payment.get_by_order(order_id)
        summary = {
            'total_paid': Decimal('0'),
            'pending_amount': Decimal('0'),
            'payment_modes': {}
        }
        
        for payment in payments:
            if payment.is_completed:
                summary['total_paid'] += payment.amount
                mode = payment.payment_mode
                if mode not in summary['payment_modes']:
                    summary['payment_modes'][mode] = Decimal('0')
                summary['payment_modes'][mode] += payment.amount
        
        return summary
    
    def _encrypt_reference_number(self, reference_number):
        """Encrypt payment reference number"""
        if not reference_number:
            return None
        return get_encryption_manager().encrypt_field(reference_number)
    
    def _decrypt_reference_number(self, encrypted_reference_number):
        """Decrypt payment reference number"""
        if not encrypted_reference_number:
            return None
        return get_encryption_manager().decrypt_field(encrypted_reference_number)
    
    def _encrypt_payment_details(self, payment_details):
        """Encrypt payment details"""
        if not payment_details:
            return None
        return get_encryption_manager().encrypt_field(payment_details)
    
    def _decrypt_payment_details(self, encrypted_payment_details):
        """Decrypt payment details"""
        if not encrypted_payment_details:
            return None
        return get_encryption_manager().decrypt_field(encrypted_payment_details)
    
    @property
    def reference_number_decrypted(self):
        """Get decrypted reference number"""
        return self._decrypt_reference_number(self.reference_number)
    
    @property
    def payment_details_decrypted(self):
        """Get decrypted payment details"""
        return self._decrypt_payment_details(self.payment_details)
    
    def __repr__(self):
        return f'<Payment {self.payment_mode} ₹{self.amount} ({self.status})>'
