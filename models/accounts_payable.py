from datetime import datetime, date
from decimal import Decimal
from . import db
import uuid

class AccountsPayable(db.Model):
    """Accounts Payable tracking for supplier payments"""
    __tablename__ = 'accounts_payable'
    
    # Payment status
    STATUS_PENDING = 'pending'
    STATUS_PARTIAL = 'partial'
    STATUS_PAID = 'paid'
    STATUS_OVERDUE = 'overdue'
    STATUS_CANCELLED = 'cancelled'
    
    # Payment methods
    METHOD_CASH = 'cash'
    METHOD_BANK_TRANSFER = 'bank_transfer'
    METHOD_CHEQUE = 'cheque'
    METHOD_CREDIT_CARD = 'credit_card'
    METHOD_ONLINE = 'online'
    METHOD_ADVANCE = 'advance'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(100), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=True)
    
    # Invoice details
    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    payment_terms = db.Column(db.String(50), nullable=True)
    
    # Amount details
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    other_charges = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(12, 2), default=0)
    balance_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Payment tracking
    status = db.Column(db.String(20), default=STATUS_PENDING)
    payment_method = db.Column(db.String(20), nullable=True)
    payment_reference = db.Column(db.String(100), nullable=True)
    payment_date = db.Column(db.Date, nullable=True)
    
    # Banking details
    bank_name = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(50), nullable=True)
    cheque_number = db.Column(db.String(50), nullable=True)
    cheque_date = db.Column(db.Date, nullable=True)
    
    # Additional tracking
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_period = db.Column(db.String(20), nullable=True)  # monthly, quarterly, yearly
    next_due_date = db.Column(db.Date, nullable=True)
    
    # Approval and authorization
    requires_approval = db.Column(db.Boolean, default=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_notes = db.Column(db.Text, nullable=True)
    
    # Document references
    invoice_file_path = db.Column(db.String(500), nullable=True)
    supporting_documents = db.Column(db.Text, default='[]')  # JSON array of file paths
    
    # Notes and descriptions
    description = db.Column(db.Text, nullable=True)
    internal_notes = db.Column(db.Text, nullable=True)
    payment_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supplier = db.relationship('Supplier', backref='accounts_payable')
    purchase_order = db.relationship('PurchaseOrder', backref='accounts_payable')
    approved_by_user = db.relationship('User', foreign_keys=[approved_by], backref='approved_payments')
    payments = db.relationship('SupplierPaymentTransaction', backref='accounts_payable', cascade='all, delete-orphan')
    
    def __init__(self, supplier_id, invoice_number, total_amount, invoice_date=None, due_date=None):
        self.supplier_id = supplier_id
        self.invoice_number = invoice_number
        self.total_amount = total_amount
        self.balance_amount = total_amount
        self.invoice_date = invoice_date or date.today()
        self.due_date = due_date or self.calculate_due_date()
    
    def calculate_due_date(self):
        """Calculate due date based on payment terms"""
        if self.supplier and self.supplier.payment_terms:
            days = self.get_payment_terms_days(self.supplier.payment_terms)
            due_date = self.invoice_date
            if isinstance(due_date, str):
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            return due_date.replace(day=min(due_date.day + days, 28))
        else:
            # Default to 30 days
            due_date = self.invoice_date
            if isinstance(due_date, str):
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            return due_date.replace(day=min(due_date.day + 30, 28))
    
    @staticmethod
    def get_payment_terms_days(payment_terms):
        """Convert payment terms to days"""
        terms_map = {
            'net_15': 15,
            'net_30': 30,
            'net_45': 45,
            'net_60': 60,
            'cod': 0,
            'prepaid': 0
        }
        return terms_map.get(payment_terms, 30)
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        return date.today() > self.due_date and self.status != self.STATUS_PAID
    
    @property
    def days_overdue(self):
        """Get days overdue"""
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days
    
    @property
    def days_until_due(self):
        """Get days until due date"""
        if self.status == self.STATUS_PAID:
            return 0
        return (self.due_date - date.today()).days
    
    @property
    def formatted_total(self):
        """Get formatted total amount"""
        return f"₹{self.total_amount:.2f}"
    
    @property
    def formatted_paid(self):
        """Get formatted paid amount"""
        return f"₹{self.paid_amount:.2f}"
    
    @property
    def formatted_balance(self):
        """Get formatted balance amount"""
        return f"₹{self.balance_amount:.2f}"
    
    @property
    def payment_percentage(self):
        """Get payment completion percentage"""
        if self.total_amount == 0:
            return 0
        return (float(self.paid_amount) / float(self.total_amount)) * 100
    
    def add_payment(self, amount, payment_method, payment_date=None, reference=None, notes=None):
        """Add payment to accounts payable"""
        if amount <= 0:
            return False, "Payment amount must be positive"
        
        if amount > self.balance_amount:
            return False, "Payment amount cannot exceed balance"
        
        # Create payment record
        payment = SupplierPaymentTransaction(
            amount=amount,
            payment_method=payment_method,
            payment_date=payment_date or date.today(),
            reference_number=reference,
            notes=notes
        )
        
        # Update amounts
        self.paid_amount += amount
        self.balance_amount = self.total_amount - self.paid_amount
        
        # Update status
        if self.balance_amount <= 0:
            self.status = self.STATUS_PAID
            self.payment_date = payment_date or date.today()
        elif self.paid_amount > 0:
            self.status = self.STATUS_PARTIAL
        else:
            self.status = self.STATUS_PENDING
        
        # Check for overdue status
        if self.is_overdue and self.status != self.STATUS_PAID:
            self.status = self.STATUS_OVERDUE
        
        db.session.add(payment)
        db.session.flush()
        
        # Link payment to accounts payable
        payment.accounts_payable_id = self.id
        
        db.session.commit()
        
        return True, "Payment added successfully"
    
    def approve_payment(self, approved_by, notes=None):
        """Approve payment for processing"""
        self.requires_approval = False
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()
        if notes:
            self.approval_notes = notes
        db.session.commit()
    
    def mark_as_paid(self, payment_method, payment_date=None, reference=None):
        """Mark as fully paid"""
        self.status = self.STATUS_PAID
        self.payment_method = payment_method
        self.payment_date = payment_date or date.today()
        self.payment_reference = reference
        self.paid_amount = self.total_amount
        self.balance_amount = 0
        db.session.commit()
    
    def cancel_payment(self, reason=None):
        """Cancel payment"""
        self.status = self.STATUS_CANCELLED
        if reason:
            self.internal_notes = (self.internal_notes or "") + f"\nCancelled: {reason}"
        db.session.commit()
    
    def get_status_color(self):
        """Get color class for status display"""
        colors = {
            self.STATUS_PENDING: 'warning',
            self.STATUS_PARTIAL: 'info',
            self.STATUS_PAID: 'success',
            self.STATUS_OVERDUE: 'danger',
            self.STATUS_CANCELLED: 'secondary'
        }
        return colors.get(self.status, 'secondary')
    
    def to_dict(self, include_payments=False):
        data = {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'purchase_order_id': self.purchase_order_id,
            'po_number': self.purchase_order.po_number if self.purchase_order else None,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'payment_terms': self.payment_terms,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'other_charges': float(self.other_charges) if self.other_charges else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'total_amount': float(self.total_amount),
            'formatted_total': self.formatted_total,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0,
            'formatted_paid': self.formatted_paid,
            'balance_amount': float(self.balance_amount),
            'formatted_balance': self.formatted_balance,
            'payment_percentage': self.payment_percentage,
            'status': self.status,
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'cheque_number': self.cheque_number,
            'cheque_date': self.cheque_date.isoformat() if self.cheque_date else None,
            'is_recurring': self.is_recurring,
            'recurring_period': self.recurring_period,
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'requires_approval': self.requires_approval,
            'approved_by': self.approved_by,
            'approved_by_name': self.approved_by_user.username if self.approved_by_user else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approval_notes': self.approval_notes,
            'invoice_file_path': self.invoice_file_path,
            'supporting_documents': self.get_supporting_documents(),
            'description': self.description,
            'internal_notes': self.internal_notes,
            'payment_notes': self.payment_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_overdue': self.is_overdue,
            'days_overdue': self.days_overdue,
            'days_until_due': self.days_until_due,
            'status_color': self.get_status_color()
        }
        
        if include_payments:
            data['payments'] = [payment.to_dict() for payment in self.payments]
        
        return data
    
    def get_supporting_documents(self):
        """Get supporting documents as list"""
        try:
            import json
            return json.loads(self.supporting_documents) if self.supporting_documents else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_supporting_documents(self, documents):
        """Set supporting documents from list"""
        try:
            import json
            self.supporting_documents = json.dumps(documents)
        except (json.JSONDecodeError, TypeError):
            self.supporting_documents = '[]'
    
    def __repr__(self):
        return f'<AccountsPayable {self.invoice_number} - {self.formatted_balance}>'


class SupplierPaymentTransaction(db.Model):
    """Individual payment transactions"""
    __tablename__ = 'supplier_payment_transactions'
    
    # Transaction status
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    
    id = db.Column(db.Integer, primary_key=True)
    accounts_payable_id = db.Column(db.Integer, db.ForeignKey('accounts_payable.id'), nullable=False)
    
    # Payment details
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    
    # Transaction tracking
    transaction_id = db.Column(db.String(100), nullable=True)  # External transaction ID
    reference_number = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default=STATUS_PENDING)
    
    # Payment gateway details
    gateway_response = db.Column(db.Text, nullable=True)  # JSON response from payment gateway
    gateway_fees = db.Column(db.Numeric(10, 2), default=0)
    
    # Processing details
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    failure_reason = db.Column(db.Text, nullable=True)
    
    # Additional info
    notes = db.Column(db.Text, nullable=True)
    attachment_path = db.Column(db.String(500), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    processed_by_user = db.relationship('User', foreign_keys=[processed_by], backref='processed_payments')
    
    def __init__(self, amount, payment_method, payment_date=None, reference_number=None):
        self.amount = amount
        self.payment_method = payment_method
        self.payment_date = payment_date or date.today()
        self.reference_number = reference_number
        self.transaction_id = self.generate_transaction_id()
    
    @staticmethod
    def generate_transaction_id():
        """Generate unique transaction ID"""
        prefix = "PAY"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = str(uuid.uuid4())[:6].upper()
        return f"{prefix}{timestamp}{random_str}"
    
    @property
    def formatted_amount(self):
        """Get formatted amount"""
        return f"₹{self.amount:.2f}"
    
    def mark_completed(self, processed_by=None, gateway_response=None):
        """Mark transaction as completed"""
        self.status = self.STATUS_COMPLETED
        self.processed_by = processed_by
        self.processed_at = datetime.utcnow()
        if gateway_response:
            self.gateway_response = gateway_response
        db.session.commit()
    
    def mark_failed(self, failure_reason):
        """Mark transaction as failed"""
        self.status = self.STATUS_FAILED
        self.failure_reason = failure_reason
        db.session.commit()
    
    def cancel_transaction(self, reason=None):
        """Cancel transaction"""
        self.status = self.STATUS_CANCELLED
        if reason:
            self.notes = (self.notes or "") + f"\nCancelled: {reason}"
        db.session.commit()
    
    def get_status_color(self):
        """Get color class for status display"""
        colors = {
            self.STATUS_PENDING: 'warning',
            self.STATUS_COMPLETED: 'success',
            self.STATUS_FAILED: 'danger',
            self.STATUS_CANCELLED: 'secondary'
        }
        return colors.get(self.status, 'secondary')
    
    def to_dict(self):
        return {
            'id': self.id,
            'accounts_payable_id': self.accounts_payable_id,
            'amount': float(self.amount),
            'formatted_amount': self.formatted_amount,
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'transaction_id': self.transaction_id,
            'reference_number': self.reference_number,
            'status': self.status,
            'gateway_response': self.gateway_response,
            'gateway_fees': float(self.gateway_fees) if self.gateway_fees else 0,
            'processed_by': self.processed_by,
            'processed_by_name': self.processed_by_user.username if self.processed_by_user else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'failure_reason': self.failure_reason,
            'notes': self.notes,
            'attachment_path': self.attachment_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'status_color': self.get_status_color()
        }
    
    def __repr__(self):
        return f'<SupplierPaymentTransaction {self.transaction_id} - {self.formatted_amount}>'


class BudgetAllocation(db.Model):
    """Budget allocation for procurement"""
    __tablename__ = 'budget_allocations'
    
    # Budget status
    STATUS_ACTIVE = 'active'
    STATUS_EXHAUSTED = 'exhausted'
    STATUS_SUSPENDED = 'suspended'
    STATUS_ARCHIVED = 'archived'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Budget details
    total_budget = db.Column(db.Numeric(15, 2), nullable=False)
    allocated_amount = db.Column(db.Numeric(15, 2), default=0)
    spent_amount = db.Column(db.Numeric(15, 2), default=0)
    remaining_amount = db.Column(db.Numeric(15, 2), nullable=False)
    
    # Budget period
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default=STATUS_ACTIVE)
    
    # Category and department
    category = db.Column(db.String(100), nullable=True)  # Food, Beverages, Equipment, etc.
    department = db.Column(db.String(100), nullable=True)
    
    # Approval workflow
    requires_approval = db.Column(db.Boolean, default=True)
    approval_limit = db.Column(db.Numeric(12, 2), nullable=True)
    
    # Budget rules
    max_order_amount = db.Column(db.Numeric(12, 2), nullable=True)
    auto_alert_threshold = db.Column(db.Numeric(5, 2), default=80)  # Percentage
    
    # Tracking
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # Alerts and notifications
    alert_email = db.Column(db.String(120), nullable=True)
    last_alert_sent = db.Column(db.DateTime, nullable=True)
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by_user = db.relationship('User', foreign_keys=[created_by], backref='created_budgets')
    approved_by_user = db.relationship('User', foreign_keys=[approved_by], backref='approved_budgets')
    transactions = db.relationship('BudgetTransaction', backref='budget', cascade='all, delete-orphan')
    
    def __init__(self, name, total_budget, start_date, end_date, created_by):
        self.name = name
        self.total_budget = total_budget
        self.remaining_amount = total_budget
        self.start_date = start_date
        self.end_date = end_date
        self.created_by = created_by
    
    @property
    def utilization_percentage(self):
        """Get budget utilization percentage"""
        if self.total_budget == 0:
            return 0
        return (float(self.spent_amount) / float(self.total_budget)) * 100
    
    @property
    def is_active(self):
        """Check if budget is currently active"""
        today = date.today()
        return (self.status == self.STATUS_ACTIVE and 
                self.start_date <= today <= self.end_date)
    
    @property
    def is_expired(self):
        """Check if budget period has expired"""
        return date.today() > self.end_date
    
    @property
    def days_remaining(self):
        """Get days remaining in budget period"""
        if self.is_expired:
            return 0
        return (self.end_date - date.today()).days
    
    def allocate_amount(self, amount, description=None):
        """Allocate amount from budget"""
        if amount <= 0:
            return False, "Amount must be positive"
        
        if amount > self.remaining_amount:
            return False, "Insufficient budget remaining"
        
        self.allocated_amount += amount
        self.remaining_amount = self.total_budget - self.allocated_amount
        
        # Create budget transaction
        transaction = BudgetTransaction(
            budget_id=self.id,
            transaction_type='allocation',
            amount=amount,
            description=description or f"Budget allocation - {amount}",
            reference_type='manual'
        )
        db.session.add(transaction)
        db.session.commit()
        
        return True, "Amount allocated successfully"
    
    def spend_amount(self, amount, reference_id=None, reference_type='purchase_order', description=None):
        """Spend amount from budget"""
        if amount <= 0:
            return False, "Amount must be positive"
        
        if amount > self.remaining_amount:
            return False, "Insufficient budget remaining"
        
        self.spent_amount += amount
        self.remaining_amount = self.total_budget - self.spent_amount
        
        # Create budget transaction
        transaction = BudgetTransaction(
            budget_id=self.id,
            transaction_type='spend',
            amount=amount,
            description=description or f"Budget spent - {amount}",
            reference_id=reference_id,
            reference_type=reference_type
        )
        db.session.add(transaction)
        db.session.commit()
        
        # Check if budget should be exhausted
        if self.remaining_amount <= 0:
            self.status = self.STATUS_EXHAUSTED
        
        return True, "Amount spent successfully"
    
    def check_budget_status(self):
        """Check budget status and trigger alerts if needed"""
        utilization = self.utilization_percentage
        
        # Alert if threshold exceeded
        if (utilization >= self.auto_alert_threshold and 
            self.last_alert_sent and 
            (datetime.utcnow() - self.last_alert_sent).days < 7):
            return False, "Alert already sent recently"
        
        if utilization >= self.auto_alert_threshold:
            self.send_alert()
            return True, "Budget alert triggered"
        
        return False, "No action needed"
    
    def send_alert(self):
        """Send budget alert"""
        # Implementation would send email/notification
        self.last_alert_sent = datetime.utcnow()
        db.session.commit()
    
    def get_status_color(self):
        """Get color class for status display"""
        colors = {
            self.STATUS_ACTIVE: 'success',
            self.STATUS_EXHAUSTED: 'danger',
            self.STATUS_SUSPENDED: 'warning',
            self.STATUS_ARCHIVED: 'secondary'
        }
        return colors.get(self.status, 'secondary')
    
    def to_dict(self, include_transactions=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'total_budget': float(self.total_budget),
            'allocated_amount': float(self.allocated_amount),
            'spent_amount': float(self.spent_amount),
            'remaining_amount': float(self.remaining_amount),
            'utilization_percentage': self.utilization_percentage,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'category': self.category,
            'department': self.department,
            'requires_approval': self.requires_approval,
            'approval_limit': float(self.approval_limit) if self.approval_limit else None,
            'max_order_amount': float(self.max_order_amount) if self.max_order_amount else None,
            'auto_alert_threshold': float(self.auto_alert_threshold),
            'created_by': self.created_by,
            'created_by_name': self.created_by_user.username if self.created_by_user else None,
            'approved_by': self.approved_by,
            'approved_by_name': self.approved_by_user.username if self.approved_by_user else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'alert_email': self.alert_email,
            'last_alert_sent': self.last_alert_sent.isoformat() if self.last_alert_sent else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'is_expired': self.is_expired,
            'days_remaining': self.days_remaining,
            'status_color': self.get_status_color()
        }
        
        if include_transactions:
            data['transactions'] = [transaction.to_dict() for transaction in self.transactions]
        
        return data
    
    def __repr__(self):
        return f'<BudgetAllocation {self.name} - ₹{self.remaining_amount} remaining>'


class BudgetTransaction(db.Model):
    """Budget transaction history"""
    __tablename__ = 'budget_transactions'
    
    # Transaction types
    TYPE_ALLOCATION = 'allocation'
    TYPE_SPEND = 'spend'
    TYPE_ADJUSTMENT = 'adjustment'
    TYPE_RETURN = 'return'
    
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budget_allocations.id'), nullable=False)
    
    # Transaction details
    transaction_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Reference information
    reference_id = db.Column(db.Integer, nullable=True)
    reference_type = db.Column(db.String(50), nullable=True)  # purchase_order, invoice, etc.
    
    # User tracking
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    created_by_user = db.relationship('User', backref='budget_transactions')
    
    def __init__(self, budget_id, transaction_type, amount, description=None, reference_id=None, reference_type=None):
        self.budget_id = budget_id
        self.transaction_type = transaction_type
        self.amount = amount
        self.description = description
        self.reference_id = reference_id
        self.reference_type = reference_type
    
    @property
    def formatted_amount(self):
        """Get formatted amount"""
        return f"₹{self.amount:.2f}"
    
    def get_transaction_icon(self):
        """Get icon for transaction type"""
        icons = {
            self.TYPE_ALLOCATION: 'fa-plus-circle',
            self.TYPE_SPEND: 'fa-minus-circle',
            self.TYPE_ADJUSTMENT: 'fa-edit',
            self.TYPE_RETURN: 'fa-undo'
        }
        return icons.get(self.transaction_type, 'fa-circle')
    
    def to_dict(self):
        return {
            'id': self.id,
            'budget_id': self.budget_id,
            'transaction_type': self.transaction_type,
            'amount': float(self.amount),
            'formatted_amount': self.formatted_amount,
            'description': self.description,
            'reference_id': self.reference_id,
            'reference_type': self.reference_type,
            'created_by': self.created_by,
            'created_by_name': self.created_by_user.username if self.created_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'transaction_icon': self.get_transaction_icon()
        }
    
    def __repr__(self):
        return f'<BudgetTransaction {self.transaction_type} - {self.formatted_amount}>'