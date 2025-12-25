from datetime import datetime
from decimal import Decimal
from utils.encryption import get_encryption_manager
from . import db

class Payment(db.Model):
    """Payment model for order payments"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    payment_mode = db.Column(db.String(20), nullable=False)  # Cash, Card, UPI, Wallet
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reference_number = db.Column(db.String(100), nullable=True)  # For card/UPI transactions
    status = db.Column(db.String(20), default='Completed')  # Completed, Pending, Failed, Refunded
    payment_details = db.Column(db.Text, nullable=True)  # Additional payment information
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __init__(self, order_id, payment_mode, amount, processed_by=None,
                 reference_number=None, payment_details=None):
        self.order_id = order_id
        self.payment_mode = payment_mode
        self.amount = Decimal(str(amount))
        self.processed_by = processed_by
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
    
    def mark_refunded(self):
        """Mark payment as refunded"""
        return self.update_status('Refunded')
    
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
                     reference_number=None, payment_details=None):
        """Create new payment"""
        payment = Payment(
            order_id=order_id,
            payment_mode=payment_mode,
            amount=amount,
            processed_by=processed_by,
            reference_number=reference_number,
            payment_details=payment_details
        )
        db.session.add(payment)
        db.session.commit()
        return payment
    
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
