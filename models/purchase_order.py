from datetime import datetime, date
from decimal import Decimal
from . import db
import uuid
import json

class PurchaseOrder(db.Model):
    """Purchase Order model for comprehensive order tracking"""
    __tablename__ = 'purchase_orders'
    
    # Purchase order status workflow
    STATUS_DRAFT = 'draft'
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_ORDERED = 'ordered'
    STATUS_PARTIALLY_RECEIVED = 'partially_received'
    STATUS_RECEIVED = 'received'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    
    # Priority levels
    PRIORITY_LOW = 'low'
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    
    # Order details
    order_date = db.Column(db.Date, nullable=False, default=date.today)
    expected_delivery_date = db.Column(db.Date, nullable=True)
    actual_delivery_date = db.Column(db.Date, nullable=True)
    delivery_address = db.Column(db.Text, nullable=True)
    
    # Status and workflow
    status = db.Column(db.String(30), default=STATUS_DRAFT)
    priority = db.Column(db.String(20), default=PRIORITY_NORMAL)
    
    # Financial details
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    other_charges = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    total_amount = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(3), default='INR')
    
    # Payment information
    payment_terms = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(20), default='pending')  # pending, partial, paid, overdue
    payment_due_date = db.Column(db.Date, nullable=True)
    paid_amount = db.Column(db.Numeric(12, 2), default=0)
    payment_reference = db.Column(db.String(100), nullable=True)
    
    # Quality and delivery tracking
    quality_check_required = db.Column(db.Boolean, default=True)
    quality_check_passed = db.Column(db.Boolean, nullable=True)
    quality_check_date = db.Column(db.DateTime, nullable=True)
    quality_check_notes = db.Column(db.Text, nullable=True)
    
    # Delivery performance
    on_time_delivery = db.Column(db.Boolean, nullable=True)
    delivery_performance_notes = db.Column(db.Text, nullable=True)
    actual_delivery_time = db.Column(db.Integer, nullable=True)  # in hours
    has_quality_issues = db.Column(db.Boolean, default=False)
    
    # Approval workflow
    requires_approval = db.Column(db.Boolean, default=True)
    approval_level = db.Column(db.Integer, default=1)  # 1=Manager, 2=Senior Manager, 3=Director
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_notes = db.Column(db.Text, nullable=True)
    
    # Auto-generation and templates
    is_auto_generated = db.Column(db.Boolean, default=False)
    template_id = db.Column(db.Integer, db.ForeignKey('purchase_order_templates.id'), nullable=True)
    
    # Additional information
    reference_number = db.Column(db.String(100), nullable=True)  # External reference
    special_instructions = db.Column(db.Text, nullable=True)
    internal_notes = db.Column(db.Text, nullable=True)
    
    # Tracking
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by_user = db.relationship('User', foreign_keys=[created_by], backref='created_purchase_orders')
    approved_by_user = db.relationship('User', foreign_keys=[approved_by], backref='approved_purchase_orders')
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy=True, cascade='all, delete-orphan')
    approvals = db.relationship('PurchaseOrderApproval', backref='purchase_order', lazy=True, cascade='all, delete-orphan')
    receipts = db.relationship('PurchaseOrderReceipt', backref='purchase_order', lazy=True, cascade='all, delete-orphan')
    ratings = db.relationship('SupplierRating', backref='purchase_order', lazy=True)
    
    def __init__(self, supplier_id, created_by, po_number=None):
        self.supplier_id = supplier_id
        self.created_by = created_by
        self.po_number = po_number or self.generate_po_number()
    
    @staticmethod
    def generate_po_number():
        """Generate unique purchase order number"""
        prefix = "PO"
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = str(uuid.uuid4())[:6].upper()
        return f"{prefix}{date_str}{random_str}"
    
    @property
    def is_draft(self):
        """Check if PO is in draft status"""
        return self.status == self.STATUS_DRAFT
    
    @property
    def is_pending_approval(self):
        """Check if PO is pending approval"""
        return self.status == self.STATUS_PENDING
    
    @property
    def is_approved(self):
        """Check if PO is approved"""
        return self.status == self.STATUS_APPROVED
    
    @property
    def is_ordered(self):
        """Check if PO is ordered"""
        return self.status == self.STATUS_ORDERED
    
    @property
    def is_received(self):
        """Check if PO is received"""
        return self.status in [self.STATUS_RECEIVED, self.STATUS_COMPLETED]
    
    @property
    def is_completed(self):
        """Check if PO is completed"""
        return self.status == self.STATUS_COMPLETED
    
    @property
    def is_cancelled(self):
        """Check if PO is cancelled"""
        return self.status == self.STATUS_CANCELLED
    
    @property
    def formatted_subtotal(self):
        """Get formatted subtotal"""
        return f"₹{self.subtotal:.2f}"
    
    @property
    def formatted_total(self):
        """Get formatted total amount"""
        return f"₹{self.total_amount:.2f}"
    
    @property
    def formatted_tax(self):
        """Get formatted tax amount"""
        return f"₹{self.tax_amount:.2f}"
    
    @property
    def formatted_shipping(self):
        """Get formatted shipping cost"""
        return f"₹{self.shipping_cost:.2f}"
    
    @property
    def days_until_due(self):
        """Get days until payment due"""
        if not self.payment_due_date:
            return None
        return (self.payment_due_date - date.today()).days
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        if not self.payment_due_date or self.payment_status == 'paid':
            return False
        return date.today() > self.payment_due_date
    
    @property
    def total_items(self):
        """Get total number of items"""
        return sum(item.quantity for item in self.items if item.status != 'Cancelled')
    
    @property
    def received_items(self):
        """Get total number of received items"""
        return sum(item.received_quantity for item in self.items if item.received_quantity > 0)
    
    @property
    def pending_items(self):
        """Get total number of pending items"""
        return self.total_items - self.received_items
    
    @property
    def is_fully_received(self):
        """Check if all items are fully received"""
        return self.received_items >= self.total_items
    
    @property
    def is_partially_received(self):
        """Check if some items are received but not all"""
        return 0 < self.received_items < self.total_items
    
    def calculate_totals(self):
        """Calculate purchase order totals"""
        # Calculate subtotal from items
        self.subtotal = sum(item.total_price for item in self.items if item.status != 'Cancelled')
        
        # Calculate tax (assume 5% GST)
        taxable_amount = self.subtotal - self.discount_amount
        self.tax_amount = taxable_amount * Decimal('0.05')  # 5% GST
        
        # Calculate total
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost + self.other_charges - self.discount_amount
        
        db.session.commit()
    
    def update_status(self, new_status, user_id=None, notes=None):
        """Update purchase order status with validation"""
        valid_statuses = [
            self.STATUS_DRAFT, self.STATUS_PENDING, self.STATUS_APPROVED,
            self.STATUS_ORDERED, self.STATUS_PARTIALLY_RECEIVED, 
            self.STATUS_RECEIVED, self.STATUS_COMPLETED, self.STATUS_CANCELLED
        ]
        
        if new_status not in valid_statuses:
            return False, "Invalid status"
        
        old_status = self.status
        self.status = new_status
        
        # Handle status-specific logic
        if new_status == self.STATUS_APPROVED and user_id:
            self.approved_by = user_id
            self.approved_at = datetime.utcnow()
            if notes:
                self.approval_notes = notes
        
        elif new_status == self.STATUS_COMPLETED:
            if not self.actual_delivery_date:
                self.actual_delivery_date = date.today()
            
            # Check if delivery was on time
            if self.expected_delivery_date:
                self.on_time_delivery = self.actual_delivery_date <= self.expected_delivery_date
                if self.on_time_delivery and self.expected_delivery_date:
                    delivery_diff = self.actual_delivery_date - self.expected_delivery_date
                    self.actual_delivery_time = delivery_diff.days * 24  # Convert to hours
        
        elif new_status == self.STATUS_CANCELLED:
            # Cancel all pending items
            for item in self.items:
                if item.status not in ['Received', 'Completed']:
                    item.status = 'Cancelled'
        
        if notes:
            self.internal_notes = (self.internal_notes or "") + f"\n{date.today()}: {notes}"
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        
        return True, f"Status updated from {old_status} to {new_status}"
    
    def approve(self, user_id, notes=None):
        """Approve purchase order"""
        return self.update_status(self.STATUS_APPROVED, user_id, notes)
    
    def cancel(self, user_id, reason=None):
        """Cancel purchase order"""
        notes = f"Cancelled by user {user_id}"
        if reason:
            notes += f". Reason: {reason}"
        return self.update_status(self.STATUS_CANCELLED, notes=notes)
    
    def mark_received(self, user_id, delivery_date=None, notes=None):
        """Mark purchase order as received"""
        if not delivery_date:
            delivery_date = date.today()
        self.actual_delivery_date = delivery_date
        
        # Update status based on received quantity
        if self.is_fully_received:
            new_status = self.STATUS_COMPLETED
        elif self.is_partially_received:
            new_status = self.STATUS_PARTIALLY_RECEIVED
        else:
            new_status = self.STATUS_RECEIVED
        
        return self.update_status(new_status, notes=notes)
    
    def get_status_color(self):
        """Get color class for status display"""
        status_colors = {
            self.STATUS_DRAFT: 'secondary',
            self.STATUS_PENDING: 'warning',
            self.STATUS_APPROVED: 'info',
            self.STATUS_ORDERED: 'primary',
            self.STATUS_PARTIALLY_RECEIVED: 'warning',
            self.STATUS_RECEIVED: 'success',
            self.STATUS_COMPLETED: 'success',
            self.STATUS_CANCELLED: 'danger'
        }
        return status_colors.get(self.status, 'secondary')
    
    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'po_number': self.po_number,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'supplier_code': self.supplier.supplier_code if self.supplier else None,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'actual_delivery_date': self.actual_delivery_date.isoformat() if self.actual_delivery_date else None,
            'delivery_address': self.delivery_address,
            'status': self.status,
            'priority': self.priority,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'formatted_subtotal': self.formatted_subtotal,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'formatted_tax': self.formatted_tax,
            'shipping_cost': float(self.shipping_cost) if self.shipping_cost else 0,
            'formatted_shipping': self.formatted_shipping,
            'other_charges': float(self.other_charges) if self.other_charges else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'formatted_total': self.formatted_total,
            'currency': self.currency,
            'payment_terms': self.payment_terms,
            'payment_status': self.payment_status,
            'payment_due_date': self.payment_due_date.isoformat() if self.payment_due_date else None,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0,
            'payment_reference': self.payment_reference,
            'days_until_due': self.days_until_due,
            'is_overdue': self.is_overdue,
            'quality_check_required': self.quality_check_required,
            'quality_check_passed': self.quality_check_passed,
            'quality_check_date': self.quality_check_date.isoformat() if self.quality_check_date else None,
            'quality_check_notes': self.quality_check_notes,
            'on_time_delivery': self.on_time_delivery,
            'delivery_performance_notes': self.delivery_performance_notes,
            'actual_delivery_time': self.actual_delivery_time,
            'has_quality_issues': self.has_quality_issues,
            'requires_approval': self.requires_approval,
            'approval_level': self.approval_level,
            'approved_by': self.approved_by,
            'approved_by_name': self.approved_by_user.username if self.approved_by_user else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approval_notes': self.approval_notes,
            'is_auto_generated': self.is_auto_generated,
            'template_id': self.template_id,
            'reference_number': self.reference_number,
            'special_instructions': self.special_instructions,
            'internal_notes': self.internal_notes,
            'created_by': self.created_by,
            'created_by_name': self.created_by_user.username if self.created_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'total_items': self.total_items,
            'received_items': self.received_items,
            'pending_items': self.pending_items,
            'is_fully_received': self.is_fully_received,
            'is_partially_received': self.is_partially_received,
            'status_color': self.get_status_color(),
            'is_draft': self.is_draft,
            'is_pending_approval': self.is_pending_approval,
            'is_approved': self.is_approved,
            'is_ordered': self.is_ordered,
            'is_received': self.is_received,
            'is_completed': self.is_completed,
            'is_cancelled': self.is_cancelled
        }
        
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
        
        return data
    
    def __repr__(self):
        return f'<PurchaseOrder {self.po_number} ({self.status})>'


class PurchaseOrderItem(db.Model):
    """Individual items within a purchase order"""
    __tablename__ = 'purchase_order_items'
    
    # Item status
    STATUS_PENDING = 'pending'
    STATUS_ORDERED = 'ordered'
    STATUS_PARTIALLY_RECEIVED = 'partially_received'
    STATUS_RECEIVED = 'received'
    STATUS_CANCELLED = 'cancelled'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=True)
    
    # Item details
    item_name = db.Column(db.String(200), nullable=False)  # Snapshot of item name
    description = db.Column(db.Text, nullable=True)
    item_code = db.Column(db.String(100), nullable=True)
    unit_of_measure = db.Column(db.String(20), default='pcs')
    
    # Quantities
    quantity_ordered = db.Column(db.Numeric(10, 3), nullable=False)
    quantity_received = db.Column(db.Numeric(10, 3), default=0)
    rejected_quantity = db.Column(db.Numeric(10, 3), default=0)
    
    # Pricing
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 2), default=0)  # Percentage
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_rate = db.Column(db.Numeric(5, 2), default=0)  # Percentage
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    
    # Status and quality
    status = db.Column(db.String(30), default=STATUS_PENDING)
    quality_check_passed = db.Column(db.Boolean, nullable=True)
    quality_check_date = db.Column(db.DateTime, nullable=True)
    quality_check_notes = db.Column(db.Text, nullable=True)
    received_date = db.Column(db.Date, nullable=True)
    
    # Delivery tracking
    expected_delivery_date = db.Column(db.Date, nullable=True)
    delivery_notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    inventory_item = db.relationship('MenuItem', backref='purchase_order_items')
    receipts = db.relationship('PurchaseOrderReceipt', backref='item', lazy=True)
    
    def __init__(self, purchase_order_id, item_name, quantity_ordered, unit_price, inventory_item_id=None):
        self.purchase_order_id = purchase_order_id
        self.item_name = item_name
        self.quantity_ordered = quantity_ordered
        self.unit_price = unit_price
        self.inventory_item_id = inventory_item_id
        self.calculate_totals()
    
    @property
    def received_quantity(self):
        """Get total received quantity"""
        return float(self.quantity_received or 0)
    
    @property
    def pending_quantity(self):
        """Get pending quantity to receive"""
        return float(self.quantity_ordered) - self.received_quantity
    
    @property
    def is_fully_received(self):
        """Check if item is fully received"""
        return self.received_quantity >= float(self.quantity_ordered)
    
    @property
    def is_partially_received(self):
        """Check if item is partially received"""
        return 0 < self.received_quantity < float(self.quantity_ordered)
    
    @property
    def formatted_unit_price(self):
        """Get formatted unit price"""
        return f"₹{self.unit_price:.2f}"
    
    @property
    def formatted_total_price(self):
        """Get formatted total price"""
        return f"₹{self.total_price:.2f}"
    
    @property
    def formatted_quantity(self):
        """Get formatted quantity"""
        return f"{float(self.quantity_ordered):.2f} {self.unit_of_measure}"
    
    @property
    def formatted_received_quantity(self):
        """Get formatted received quantity"""
        return f"{self.received_quantity:.2f} {self.unit_of_measure}"
    
    def calculate_totals(self):
        """Calculate item totals"""
        base_total = float(self.quantity_ordered) * float(self.unit_price)
        
        # Calculate discount
        self.discount_amount = base_total * (float(self.discount_rate) / 100)
        taxable_amount = base_total - self.discount_amount
        
        # Calculate tax
        self.tax_amount = taxable_amount * (float(self.tax_rate) / 100)
        
        # Calculate final total
        self.total_price = taxable_amount + self.tax_amount
        
        # Update status based on received quantity
        if self.received_quantity >= float(self.quantity_ordered):
            self.status = self.STATUS_RECEIVED
        elif self.received_quantity > 0:
            self.status = self.STATUS_PARTIALLY_RECEIVED
        
        db.session.commit()
    
    def receive_quantity(self, quantity, quality_passed=True, notes=None, received_date=None):
        """Receive quantity for this item"""
        if quantity <= 0:
            return False, "Invalid quantity"
        
        new_received = self.received_quantity + quantity
        
        if new_received > float(self.quantity_ordered):
            return False, "Cannot receive more than ordered quantity"
        
        self.quantity_received = new_received
        
        # Update quality check
        if quality_passed is not None:
            self.quality_check_passed = quality_passed
            if quality_passed:
                self.quality_check_date = datetime.utcnow()
                if notes:
                    self.quality_check_notes = notes
        
        # Update received date
        if not received_date:
            received_date = date.today()
        self.received_date = received_date
        
        # Update status
        if self.is_fully_received:
            self.status = self.STATUS_RECEIVED
        elif self.is_partially_received:
            self.status = self.STATUS_PARTIALLY_RECEIVED
        
        # Update inventory if linked
        if self.inventory_item_id:
            from .menu_item import MenuItem
            inventory_item = MenuItem.query.get(self.inventory_item_id)
            if inventory_item and quality_passed:
                inventory_item.update_stock(quantity)
        
        db.session.commit()
        return True, f"Received {quantity} units"
    
    def reject_quantity(self, quantity, reason=None):
        """Reject quantity due to quality issues"""
        if quantity <= 0:
            return False, "Invalid quantity"
        
        if quantity > self.received_quantity:
            return False, "Cannot reject more than received quantity"
        
        self.rejected_quantity += quantity
        self.quality_check_passed = False
        
        if reason:
            self.quality_check_notes = (self.quality_check_notes or "") + f"\\nRejected: {reason}"
        
        db.session.commit()
        return True, f"Rejected {quantity} units"
    
    def to_dict(self):
        return {
            'id': self.id,
            'purchase_order_id': self.purchase_order_id,
            'inventory_item_id': self.inventory_item_id,
            'item_name': self.item_name,
            'description': self.description,
            'item_code': self.item_code,
            'unit_of_measure': self.unit_of_measure,
            'quantity_ordered': float(self.quantity_ordered),
            'quantity_received': self.received_quantity,
            'rejected_quantity': float(self.rejected_quantity),
            'pending_quantity': self.pending_quantity,
            'unit_price': float(self.unit_price),
            'formatted_unit_price': self.formatted_unit_price,
            'total_price': float(self.total_price),
            'formatted_total_price': self.formatted_total_price,
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'discount_rate': float(self.discount_rate),
            'discount_amount': float(self.discount_amount),
            'status': self.status,
            'quality_check_passed': self.quality_check_passed,
            'quality_check_date': self.quality_check_date.isoformat() if self.quality_check_date else None,
            'quality_check_notes': self.quality_check_notes,
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'delivery_notes': self.delivery_notes,
            'is_fully_received': self.is_fully_received,
            'is_partially_received': self.is_partially_received,
            'formatted_quantity': self.formatted_quantity,
            'formatted_received_quantity': self.formatted_received_quantity
        }
    
    def __repr__(self):
        return f'<PurchaseOrderItem {self.item_name} x{self.quantity_ordered}>'


class PurchaseOrderApproval(db.Model):
    """Multi-level approval system for purchase orders"""
    __tablename__ = 'purchase_order_approvals'
    
    # Approval status
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_DELEGATED = 'delegated'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    
    # Approval details
    approval_level = db.Column(db.Integer, nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approver_name = db.Column(db.String(120), nullable=True)
    
    # Approval workflow
    status = db.Column(db.String(20), default=STATUS_PENDING)
    amount_limit = db.Column(db.Numeric(12, 2), nullable=True)  # Maximum amount this approver can approve
    is_required = db.Column(db.Boolean, default=True)
    
    # Approval decision
    decision_date = db.Column(db.DateTime, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    delegation_reason = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    approver = db.relationship('User', backref='purchase_order_approvals', foreign_keys=[approver_id])
    
    def __init__(self, purchase_order_id, approval_level, approver_id, amount_limit=None):
        self.purchase_order_id = purchase_order_id
        self.approval_level = approval_level
        self.approver_id = approver_id
        self.amount_limit = amount_limit
    
    def approve(self, comments=None):
        """Approve at this level"""
        self.status = self.STATUS_APPROVED
        self.decision_date = datetime.utcnow()
        if comments:
            self.comments = comments
        db.session.commit()
    
    def reject(self, comments=None):
        """Reject at this level"""
        self.status = self.STATUS_REJECTED
        self.decision_date = datetime.utcnow()
        if comments:
            self.comments = comments
        db.session.commit()
    
    def delegate(self, delegated_to_id, reason=None):
        """Delegate approval to another user"""
        self.status = self.STATUS_DELEGATED
        self.decision_date = datetime.utcnow()
        self.delegation_reason = reason
        # Note: In a full implementation, you'd create a new approval record for the delegated user
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'purchase_order_id': self.purchase_order_id,
            'approval_level': self.approval_level,
            'approver_id': self.approver_id,
            'approver_name': self.approver_name or (self.approver.username if self.approver else None),
            'status': self.status,
            'amount_limit': float(self.amount_limit) if self.amount_limit else None,
            'is_required': self.is_required,
            'decision_date': self.decision_date.isoformat() if self.decision_date else None,
            'comments': self.comments,
            'delegation_reason': self.delegation_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<PurchaseOrderApproval Level {self.approval_level} - {self.status}>'


class PurchaseOrderReceipt(db.Model):
    """Purchase order receipt tracking"""
    __tablename__ = 'purchase_order_receipts'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    purchase_order_item_id = db.Column(db.Integer, db.ForeignKey('purchase_order_items.id'), nullable=False)
    
    # Receipt details
    receipt_number = db.Column(db.String(50), nullable=False)
    received_quantity = db.Column(db.Numeric(10, 3), nullable=False)
    received_date = db.Column(db.Date, nullable=False, default=date.today)
    
    # Quality and condition
    quality_status = db.Column(db.String(20), default='pending')  # pending, passed, failed
    condition_notes = db.Column(db.Text, nullable=True)
    batch_number = db.Column(db.String(100), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    
    # Receiving details
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Warehouse/storage
    storage_location = db.Column(db.String(100), nullable=True)
    storage_temperature = db.Column(db.String(20), nullable=True)  # Room temp, refrigerated, frozen
    
    # Relationships
    received_by_user = db.relationship('User', backref='purchase_order_receipts', foreign_keys=[received_by])
    
    def __init__(self, purchase_order_id, purchase_order_item_id, received_quantity, received_by):
        self.purchase_order_id = purchase_order_id
        self.purchase_order_item_id = purchase_order_item_id
        self.received_quantity = received_quantity
        self.received_by = received_by
        self.receipt_number = self.generate_receipt_number()
    
    @staticmethod
    def generate_receipt_number():
        """Generate unique receipt number"""
        prefix = "RCPT"
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = str(uuid.uuid4())[:6].upper()
        return f"{prefix}{date_str}{random_str}"
    
    def mark_quality_passed(self, notes=None):
        """Mark receipt as quality passed"""
        self.quality_status = 'passed'
        if notes:
            self.condition_notes = (self.condition_notes or "") + f"\\nQuality Check Passed: {notes}"
        db.session.commit()
    
    def mark_quality_failed(self, notes=None):
        """Mark receipt as quality failed"""
        self.quality_status = 'failed'
        if notes:
            self.condition_notes = (self.condition_notes or "") + f"\\nQuality Check Failed: {notes}"
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'purchase_order_id': self.purchase_order_id,
            'purchase_order_item_id': self.purchase_order_item_id,
            'receipt_number': self.receipt_number,
            'received_quantity': float(self.received_quantity),
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'quality_status': self.quality_status,
            'condition_notes': self.condition_notes,
            'batch_number': self.batch_number,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'received_by': self.received_by,
            'received_by_name': self.received_by_user.username if self.received_by_user else None,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'storage_location': self.storage_location,
            'storage_temperature': self.storage_temperature
        }
    
    def __repr__(self):
        return f'<PurchaseOrderReceipt {self.receipt_number}>'


class PurchaseOrderTemplate(db.Model):
    """Template for recurring purchase orders"""
    __tablename__ = 'purchase_order_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Template configuration
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    auto_generate = db.Column(db.Boolean, default=False)
    generation_frequency = db.Column(db.String(20), nullable=True)  # daily, weekly, monthly
    
    # Default values
    default_delivery_address = db.Column(db.Text, nullable=True)
    default_payment_terms = db.Column(db.String(50), nullable=True)
    default_priority = db.Column(db.String(20), default='normal')
    default_expected_days = db.Column(db.Integer, default=3)
    
    # Schedule
    next_generation_date = db.Column(db.Date, nullable=True)
    last_generated_date = db.Column(db.Date, nullable=True)
    
    # Template items (JSON storage for flexibility)
    template_items = db.Column(db.Text, default='[]')  # JSON array of items
    
    # Usage tracking
    usage_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supplier = db.relationship('Supplier', backref='po_templates')
    created_by_user = db.relationship('User', backref='created_po_templates')
    generated_orders = db.relationship('PurchaseOrder', backref='template', foreign_keys='PurchaseOrder.template_id')
    
    def __init__(self, name, supplier_id, created_by):
        self.name = name
        self.supplier_id = supplier_id
        self.created_by = created_by
    
    def get_template_items(self):
        """Get template items as list"""
        try:
            return json.loads(self.template_items) if self.template_items else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_template_items(self, items):
        """Set template items from list"""
        self.template_items = json.dumps(items)
    
    def generate_purchase_order(self, created_by, custom_items=None):
        """Generate purchase order from template"""
        from .order import Order  # Avoid circular import
        
        # Create new purchase order
        po = PurchaseOrder(self.supplier_id, created_by)
        db.session.add(po)
        db.session.flush()  # Get PO ID
        
        # Get items to use (custom or template)
        items_data = custom_items or self.get_template_items()
        
        # Create purchase order items
        for item_data in items_data:
            po_item = PurchaseOrderItem(
                po.id,
                item_data.get('item_name'),
                item_data.get('quantity', 1),
                item_data.get('unit_price', 0),
                item_data.get('inventory_item_id')
            )
            db.session.add(po_item)
        
        # Set default values
        po.delivery_address = self.default_delivery_address
        po.payment_terms = self.default_payment_terms
        po.priority = self.default_priority
        
        if self.default_expected_days:
            from datetime import timedelta
            po.expected_delivery_date = date.today() + timedelta(days=self.default_expected_days)
        
        # Calculate totals
        po.calculate_totals()
        
        # Update template usage
        self.usage_count += 1
        self.last_generated_date = date.today()
        
        db.session.commit()
        
        return po
    
    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'is_active': self.is_active,
            'auto_generate': self.auto_generate,
            'generation_frequency': self.generation_frequency,
            'default_delivery_address': self.default_delivery_address,
            'default_payment_terms': self.default_payment_terms,
            'default_priority': self.default_priority,
            'default_expected_days': self.default_expected_days,
            'next_generation_date': self.next_generation_date.isoformat() if self.next_generation_date else None,
            'last_generated_date': self.last_generated_date.isoformat() if self.last_generated_date else None,
            'template_items': self.get_template_items(),
            'usage_count': self.usage_count,
            'created_by': self.created_by,
            'created_by_name': self.created_by_user.username if self.created_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_items:
            data['template_items_list'] = self.get_template_items()
        
        return data
    
    def __repr__(self):
        return f'<PurchaseOrderTemplate {self.name}>'


class SupplierPriceHistory(db.Model):
    """Price history tracking for suppliers"""
    __tablename__ = 'supplier_price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=True)
    
    # Price information
    item_name = db.Column(db.String(200), nullable=False)  # Snapshot of item name
    item_code = db.Column(db.String(100), nullable=True)
    unit_of_measure = db.Column(db.String(20), default='pcs')
    
    # Price details
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    minimum_quantity = db.Column(db.Numeric(10, 3), default=1)
    maximum_quantity = db.Column(db.Numeric(10, 3), nullable=True)
    
    # Pricing details
    currency = db.Column(db.String(3), default='INR')
    price_valid_from = db.Column(db.Date, nullable=False, default=date.today)
    price_valid_until = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, default=True)
    
    # Additional pricing info
    bulk_discount_rate = db.Column(db.Numeric(5, 2), default=0)
    seasonal_price_adjustment = db.Column(db.Numeric(5, 2), default=0)
    special_conditions = db.Column(db.Text, nullable=True)
    
    # Source information
    source_type = db.Column(db.String(20), default='manual')  # manual, quotation, contract, market
    source_reference = db.Column(db.String(100), nullable=True)  # Quote number, contract reference
    
    # Metadata
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    inventory_item = db.relationship('MenuItem', backref='supplier_price_histories')
    recorded_by_user = db.relationship('User', backref='supplier_price_history_records')
    
    def __init__(self, supplier_id, item_name, unit_price, recorded_by, inventory_item_id=None):
        self.supplier_id = supplier_id
        self.item_name = item_name
        self.unit_price = unit_price
        self.recorded_by = recorded_by
        self.inventory_item_id = inventory_item_id
    
    @property
    def formatted_price(self):
        """Get formatted unit price"""
        return f"₹{self.unit_price:.2f}"
    
    @property
    def is_expired(self):
        """Check if price is expired"""
        if not self.price_valid_until:
            return False
        return date.today() > self.price_valid_until
    
    @property
    def is_active(self):
        """Check if price is currently active"""
        if not self.is_current:
            return False
        if self.is_expired:
            return False
        return True
    
    def deactivate(self):
        """Deactivate this price record"""
        self.is_current = False
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'inventory_item_id': self.inventory_item_id,
            'item_name': self.item_name,
            'item_code': self.item_code,
            'unit_of_measure': self.unit_of_measure,
            'unit_price': float(self.unit_price),
            'formatted_price': self.formatted_price,
            'minimum_quantity': float(self.minimum_quantity),
            'maximum_quantity': float(self.maximum_quantity) if self.maximum_quantity else None,
            'currency': self.currency,
            'price_valid_from': self.price_valid_from.isoformat() if self.price_valid_from else None,
            'price_valid_until': self.price_valid_until.isoformat() if self.price_valid_until else None,
            'is_current': self.is_current,
            'is_expired': self.is_expired,
            'is_active': self.is_active,
            'bulk_discount_rate': float(self.bulk_discount_rate),
            'seasonal_price_adjustment': float(self.seasonal_price_adjustment),
            'special_conditions': self.special_conditions,
            'source_type': self.source_type,
            'source_reference': self.source_reference,
            'recorded_by': self.recorded_by,
            'recorded_by_name': self.recorded_by_user.username if self.recorded_by_user else None,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<SupplierPriceHistory {self.supplier.name} - {self.item_name} - ₹{self.unit_price}>'