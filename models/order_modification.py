"""
Order Modification Models
Comprehensive models for handling order modifications in the restaurant POS system
"""

from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from . import db
import json


class OrderModification(db.Model):
    """Main order modification tracking model"""
    __tablename__ = 'order_modifications'
    
    id = db.Column(db.Integer, primary_key=True)
    modification_id = db.Column(db.String(50), unique=True, nullable=False)
    
    # Order relationship
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    
    # Modification details
    modification_type = db.Column(db.String(50), nullable=False)  # add_items, remove_items, modify_items, cancel_order, partial_cancel, kitchen_hold
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected, In Progress, Completed, Failed, Cancelled
    
    # Financial tracking
    original_total = db.Column(db.Numeric(10, 2), nullable=False)
    modified_total = db.Column(db.Numeric(10, 2), nullable=False)
    price_difference = db.Column(db.Numeric(10, 2), default=0)  # positive = additional charge, negative = refund
    refund_amount = db.Column(db.Numeric(10, 2), default=0)
    
    # Request details
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=True)
    customer_reason = db.Column(db.Text, nullable=True)  # Reason from customer perspective
    
    # Approval workflow
    requires_approval = db.Column(db.Boolean, default=True)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_notes = db.Column(db.Text, nullable=True)
    auto_approved = db.Column(db.Boolean, default=False)
    
    # Implementation details
    implemented_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    implemented_at = db.Column(db.DateTime, nullable=True)
    implementation_notes = db.Column(db.Text, nullable=True)
    
    # Time tracking
    request_time = db.Column(db.DateTime, default=datetime.utcnow)
    response_time = db.Column(db.DateTime, nullable=True)  # Time taken to respond to request
    completion_time = db.Column(db.DateTime, nullable=True)  # Time taken to complete
    
    # Metadata
    source = db.Column(db.String(50), default='manual')  # manual, kitchen, customer, automated
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, critical
    
    # Relationships
    order = db.relationship('Order', backref='modifications')
    requested_by = db.relationship('User', foreign_keys=[requested_by_user_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_user_id])
    implemented_by = db.relationship('User', foreign_keys=[implemented_by_user_id])
    
    # Child modifications
    item_modifications = db.relationship('OrderItemModification', backref='order_modification', 
                                       lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, order_id, modification_type, requested_by_user_id, reason=None, source='manual'):
        self.modification_id = self.generate_modification_id()
        self.order_id = order_id
        self.modification_type = modification_type
        self.requested_by_user_id = requested_by_user_id
        self.reason = reason
        self.source = source
        self.original_total = self._get_order_total()
    
    @staticmethod
    def generate_modification_id():
        """Generate unique modification ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = str(uuid.uuid4())[:8].upper()
        return f"MOD{date_str}{random_str}"
    
    def _get_order_total(self):
        """Get current order total"""
        order = db.session.query(Order).get(self.order_id)
        return order.grand_total if order else Decimal('0')
    
    def approve(self, approved_by_user_id, notes=None):
        """Approve modification request"""
        if self.status != 'Pending':
            return False, "Modification is not in pending status"
        
        self.status = 'Approved'
        self.approved_by_user_id = approved_by_user_id
        self.approved_at = datetime.utcnow()
        self.approval_notes = notes
        self.response_time = self.approved_at - self.request_time
        self.auto_approved = (approved_by_user_id == self.requested_by_user_id)
        
        db.session.commit()
        return True, "Modification approved successfully"
    
    def reject(self, rejected_by_user_id, reason):
        """Reject modification request"""
        if self.status != 'Pending':
            return False, "Modification is not in pending status"
        
        self.status = 'Rejected'
        self.approved_by_user_id = rejected_by_user_id  # Using same field for rejection tracking
        self.approved_at = datetime.utcnow()
        self.approval_notes = reason
        self.response_time = self.approved_at - self.request_time
        
        db.session.commit()
        return True, "Modification rejected successfully"
    
    def start_implementation(self, implemented_by_user_id):
        """Start implementing the approved modification"""
        if self.status != 'Approved':
            return False, "Modification must be approved before implementation"
        
        self.status = 'In Progress'
        self.implemented_by_user_id = implemented_by_user_id
        self.implemented_at = datetime.utcnow()
        
        db.session.commit()
        return True, "Modification implementation started"
    
    def complete_implementation(self, implementation_notes=None, new_total=None):
        """Complete modification implementation"""
        if self.status != 'In Progress':
            return False, "Modification must be in progress to complete"
        
        self.status = 'Completed'
        self.completion_time = datetime.utcnow() - self.implemented_at
        self.implementation_notes = implementation_notes
        
        if new_total is not None:
            self.modified_total = Decimal(str(new_total))
            self.price_difference = self.modified_total - self.original_total
        
        db.session.commit()
        return True, "Modification completed successfully"
    
    def cancel(self, cancelled_by_user_id, reason):
        """Cancel modification request"""
        if self.status in ['Completed', 'Failed']:
            return False, "Cannot cancel completed or failed modifications"
        
        self.status = 'Cancelled'
        self.implemented_by_user_id = cancelled_by_user_id
        self.implementation_notes = reason
        db.session.commit()
        return True, "Modification cancelled successfully"
    
    def mark_failed(self, reason):
        """Mark modification as failed"""
        if self.status not in ['In Progress', 'Approved']:
            return False, "Modification must be in progress or approved to be marked as failed"
        
        self.status = 'Failed'
        self.implementation_notes = reason
        db.session.commit()
        return True, "Modification marked as failed"
    
    def calculate_total_time(self):
        """Calculate total time taken for modification"""
        if self.status == 'Completed':
            return self.request_time - self.completion_time
        elif self.response_time:
            return self.response_time
        else:
            return datetime.utcnow() - self.request_time
    
    def get_price_impact(self):
        """Get formatted price impact information"""
        if self.price_difference > 0:
            return f"+₹{self.price_difference:.2f} (Additional Charge)"
        elif self.price_difference < 0:
            return f"-₹{abs(self.price_difference):.2f} (Refund)"
        else:
            return "₹0.00 (No Change)"
    
    def to_dict(self):
        """Convert modification to dictionary"""
        return {
            'id': self.id,
            'modification_id': self.modification_id,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else None,
            'modification_type': self.modification_type,
            'status': self.status,
            'original_total': float(self.original_total),
            'modified_total': float(self.modified_total),
            'price_difference': float(self.price_difference),
            'price_impact': self.get_price_impact(),
            'refund_amount': float(self.refund_amount),
            'requested_by_user_id': self.requested_by_user_id,
            'requested_by_username': self.requested_by.username if self.requested_by else None,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'reason': self.reason,
            'customer_reason': self.customer_reason,
            'requires_approval': self.requires_approval,
            'approved_by_user_id': self.approved_by_user_id,
            'approved_by_username': self.approved_by.username if self.approved_by else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approval_notes': self.approval_notes,
            'auto_approved': self.auto_approved,
            'implemented_by_user_id': self.implemented_by_user_id,
            'implemented_by_username': self.implemented_by.username if self.implemented_by else None,
            'implemented_at': self.implemented_at.isoformat() if self.implemented_at else None,
            'implementation_notes': self.implementation_notes,
            'source': self.source,
            'priority': self.priority,
            'response_time_minutes': self.response_time.total_seconds() / 60 if self.response_time else None,
            'completion_time_minutes': self.completion_time.total_seconds() / 60 if self.completion_time else None
        }
    
    def __repr__(self):
        return f'<OrderModification {self.modification_id} ({self.modification_type})>'


class OrderItemModification(db.Model):
    """Individual item modifications within an order modification"""
    __tablename__ = 'order_item_modifications'
    
    id = db.Column(db.Integer, primary_key=True)
    modification_id = db.Column(db.Integer, db.ForeignKey('order_modifications.id'), nullable=False)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=True)
    
    # Item details
    original_menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    new_menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=True)  # For substitutions
    
    # Quantity changes
    original_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    
    # Price changes
    original_price = db.Column(db.Numeric(10, 2), nullable=False)
    new_price = db.Column(db.Numeric(10, 2), nullable=True)  # For price changes/substitutions
    price_difference = db.Column(db.Numeric(10, 2), default=0)
    
    # Modification type
    modification_type = db.Column(db.String(50), nullable=False)  # add_item, remove_item, change_quantity, change_item, update_instructions
    
    # Item details
    original_instructions = db.Column(db.Text, nullable=True)
    new_instructions = db.Column(db.Text, nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='Pending')  # Pending, Applied, Failed
    
    # Implementation
    applied_at = db.Column(db.DateTime, nullable=True)
    applied_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    failure_reason = db.Column(db.Text, nullable=True)
    
    # Relationships
    original_item = db.relationship('MenuItem', foreign_keys=[original_menu_item_id])
    new_item = db.relationship('MenuItem', foreign_keys=[new_menu_item_id])
    order_item = db.relationship('OrderItem', backref='modifications')
    applied_by = db.relationship('User', foreign_keys=[applied_by_user_id])
    
    def __init__(self, modification_id, modification_type, original_menu_item_id, 
                 original_quantity, original_price, order_item_id=None):
        self.modification_id = modification_id
        self.modification_type = modification_type
        self.original_menu_item_id = original_menu_item_id
        self.original_quantity = original_quantity
        self.original_price = Decimal(str(original_price))
        self.order_item_id = order_item_id
        self.new_quantity = original_quantity
        self.new_price = original_price
    
    def apply(self, applied_by_user_id):
        """Apply the item modification"""
        try:
            if self.status != 'Pending':
                return False, "Item modification is not in pending status"
            
            # Apply different types of modifications
            if self.modification_type == 'add_item':
                return self._apply_add_item(applied_by_user_id)
            elif self.modification_type == 'remove_item':
                return self._apply_remove_item(applied_by_user_id)
            elif self.modification_type == 'change_quantity':
                return self._apply_quantity_change(applied_by_user_id)
            elif self.modification_type == 'change_item':
                return self._apply_item_change(applied_by_user_id)
            elif self.modification_type == 'update_instructions':
                return self._apply_instruction_update(applied_by_user_id)
            else:
                return False, f"Unknown modification type: {self.modification_type}"
                
        except Exception as e:
            self.status = 'Failed'
            self.failure_reason = str(e)
            db.session.commit()
            return False, f"Failed to apply modification: {str(e)}"
    
    def _apply_add_item(self, applied_by_user_id):
        """Apply add item modification"""
        from .order import OrderItem
        
        # Create new order item
        new_order_item = OrderItem(
            order_id=self.order_modification.order_id,
            menu_item_id=self.original_menu_item_id,
            quantity=self.new_quantity,
            price=self.new_price
        )
        
        if self.new_instructions:
            new_order_item.special_instructions = self.new_instructions
        
        db.session.add(new_order_item)
        
        self.status = 'Applied'
        self.applied_at = datetime.utcnow()
        self.applied_by_user_id = applied_by_user_id
        
        db.session.commit()
        return True, "Item added successfully"
    
    def _apply_remove_item(self, applied_by_user_id):
        """Apply remove item modification"""
        if not self.order_item_id:
            return False, "No order item specified for removal"
        
        order_item = db.session.query(OrderItem).get(self.order_item_id)
        if not order_item:
            return False, "Order item not found"
        
        # Mark item as cancelled
        order_item.status = 'Cancelled'
        self.status = 'Applied'
        self.applied_at = datetime.utcnow()
        self.applied_by_user_id = applied_by_user_id
        
        db.session.commit()
        return True, "Item removed successfully"
    
    def _apply_quantity_change(self, applied_by_user_id):
        """Apply quantity change modification"""
        if not self.order_item_id:
            return False, "No order item specified for quantity change"
        
        order_item = db.session.query(OrderItem).get(self.order_item_id)
        if not order_item:
            return False, "Order item not found"
        
        # Update quantity and total
        order_item.quantity = self.new_quantity
        order_item.total = self.new_price * self.new_quantity
        
        self.status = 'Applied'
        self.applied_at = datetime.utcnow()
        self.applied_by_user_id = applied_by_user_id
        
        db.session.commit()
        return True, "Quantity updated successfully"
    
    def _apply_item_change(self, applied_by_user_id):
        """Apply item change/substitution modification"""
        if not self.order_item_id:
            return False, "No order item specified for item change"
        
        order_item = db.session.query(OrderItem).get(self.order_item_id)
        if not order_item:
            return False, "Order item not found"
        
        # Update item and price
        order_item.menu_item_id = self.new_menu_item_id
        order_item.price = self.new_price
        order_item.total = self.new_price * order_item.quantity
        
        if self.new_instructions:
            order_item.special_instructions = self.new_instructions
        
        self.status = 'Applied'
        self.applied_at = datetime.utcnow()
        self.applied_by_user_id = applied_by_user_id
        
        db.session.commit()
        return True, "Item changed successfully"
    
    def _apply_instruction_update(self, applied_by_user_id):
        """Apply instruction update modification"""
        if not self.order_item_id:
            return False, "No order item specified for instruction update"
        
        order_item = db.session.query(OrderItem).get(self.order_item_id)
        if not order_item:
            return False, "Order item not found"
        
        # Update instructions
        order_item.special_instructions = self.new_instructions
        
        self.status = 'Applied'
        self.applied_at = datetime.utcnow()
        self.applied_by_user_id = applied_by_user_id
        
        db.session.commit()
        return True, "Instructions updated successfully"
    
    def get_item_name(self):
        """Get current item name"""
        if self.new_item:
            return self.new_item.name
        elif self.original_item:
            return self.original_item.name
        return "Unknown Item"
    
    def calculate_price_difference(self):
        """Calculate price difference for this item modification"""
        original_total = self.original_price * self.original_quantity
        new_total = self.new_price * self.new_quantity
        return new_total - original_total
    
    def to_dict(self):
        """Convert item modification to dictionary"""
        return {
            'id': self.id,
            'modification_id': self.modification_id,
            'order_item_id': self.order_item_id,
            'original_menu_item_id': self.original_menu_item_id,
            'new_menu_item_id': self.new_menu_item_id,
            'original_quantity': self.original_quantity,
            'new_quantity': self.new_quantity,
            'original_price': float(self.original_price),
            'new_price': float(self.new_price) if self.new_price else None,
            'price_difference': float(self.price_difference),
            'modification_type': self.modification_type,
            'original_instructions': self.original_instructions,
            'new_instructions': self.new_instructions,
            'status': self.status,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'applied_by_user_id': self.applied_by_user_id,
            'applied_by_username': self.applied_by.username if self.applied_by else None,
            'failure_reason': self.failure_reason,
            'item_name': self.get_item_name(),
            'original_total': float(self.original_price * self.original_quantity),
            'new_total': float(self.new_price * self.new_quantity) if self.new_price else None
        }
    
    def __repr__(self):
        return f'<OrderItemModification {self.modification_type} for item {self.get_item_name()}>'


class ModificationRequest(db.Model):
    """Modification request queue for pending approvals"""
    __tablename__ = 'modification_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(50), unique=True, nullable=False)
    
    # Links to main modification
    modification_id = db.Column(db.Integer, db.ForeignKey('order_modifications.id'), nullable=False)
    
    # Request details
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    request_type = db.Column(db.String(50), nullable=False)  # customer_request, kitchen_request, manager_initiated
    
    # Priority and urgency
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, critical
    estimated_completion_time = db.Column(db.Integer, nullable=True)  # minutes
    
    # Approval workflow
    current_approver_role = db.Column(db.String(50), nullable=True)  # manager, head_chef, admin
    auto_approval_enabled = db.Column(db.Boolean, default=False)
    auto_approval_criteria = db.Column(db.Text, nullable=True)  # JSON criteria for auto-approval
    
    # Time tracking
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_at = db.Column(db.DateTime, nullable=True)
    escalation_at = db.Column(db.DateTime, nullable=True)
    
    # Status and outcomes
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected, Expired, Escalated
    
    # Notification tracking
    notifications_sent = db.Column(db.Integer, default=0)
    last_notification_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    modification = db.relationship('OrderModification', backref='modification_request')
    order = db.relationship('Order', backref='modification_requests')
    
    def __init__(self, modification_id, order_id, request_type, priority='normal'):
        self.request_id = self.generate_request_id()
        self.modification_id = modification_id
        self.order_id = order_id
        self.request_type = request_type
        self.priority = priority
        self.due_at = datetime.utcnow() + timedelta(minutes=self._get_estimated_time())
    
    @staticmethod
    def generate_request_id():
        """Generate unique request ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = str(uuid.uuid4())[:6].upper()
        return f"REQ{date_str}{random_str}"
    
    def _get_estimated_time(self):
        """Get estimated completion time based on priority and type"""
        time_map = {
            'low': 60,
            'normal': 30,
            'high': 15,
            'critical': 5
        }
        return time_map.get(self.priority, 30)
    
    def is_overdue(self):
        """Check if request is overdue"""
        return datetime.utcnow() > self.due_at
    
    def escalate(self):
        """Escalate request to higher authority"""
        self.status = 'Escalated'
        self.escalation_at = datetime.utcnow()
        self.current_approver_role = self._get_next_approver_role()
        db.session.commit()
        return True
    
    def _get_next_approver_role(self):
        """Get next approver role in escalation chain"""
        role_chain = ['manager', 'head_chef', 'admin']
        current_index = role_chain.index(self.current_approver_role) if self.current_approver_role in role_chain else -1
        if current_index + 1 < len(role_chain):
            return role_chain[current_index + 1]
        return 'admin'
    
    def should_auto_approve(self):
        """Check if request should be auto-approved"""
        if not self.auto_approval_enabled:
            return False
        
        # Parse auto-approval criteria
        try:
            criteria = json.loads(self.auto_approval_criteria) if self.auto_approval_criteria else {}
            
            # Check time-based auto-approval
            if criteria.get('auto_approve_after_minutes'):
                if (datetime.utcnow() - self.submitted_at).total_seconds() / 60 >= criteria['auto_approve_after_minutes']:
                    return True
            
            # Check value-based auto-approval
            if criteria.get('max_price_difference'):
                price_diff = self.modification.price_difference
                if abs(price_diff) <= criteria['max_price_difference']:
                    return True
            
            # Check type-based auto-approval
            if criteria.get('allowed_types'):
                if self.modification.modification_type in criteria['allowed_types']:
                    return True
                    
        except (json.JSONDecodeError, AttributeError):
            pass
        
        return False
    
    def approve(self, approver_user_id, notes=None):
        """Approve modification request"""
        self.status = 'Approved'
        return self.modification.approve(approver_user_id, notes)
    
    def reject(self, approver_user_id, reason):
        """Reject modification request"""
        self.status = 'Rejected'
        return self.modification.reject(approver_user_id, reason)
    
    def expire(self):
        """Mark request as expired"""
        self.status = 'Expired'
        db.session.commit()
        return True
    
    def send_notification(self):
        """Send notification about this request"""
        self.notifications_sent += 1
        self.last_notification_at = datetime.utcnow()
        db.session.commit()
        
        # This would integrate with your notification system
        # For now, just increment counter
        return True
    
    def to_dict(self):
        """Convert request to dictionary"""
        return {
            'id': self.id,
            'request_id': self.request_id,
            'modification_id': self.modification_id,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else None,
            'request_type': self.request_type,
            'priority': self.priority,
            'estimated_completion_time': self.estimated_completion_time,
            'current_approver_role': self.current_approver_role,
            'auto_approval_enabled': self.auto_approval_enabled,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'due_at': self.due_at.isoformat() if self.due_at else None,
            'escalation_at': self.escalation_at.isoformat() if self.escalation_at else None,
            'status': self.status,
            'is_overdue': self.is_overdue(),
            'notifications_sent': self.notifications_sent,
            'last_notification_at': self.last_notification_at.isoformat() if self.last_notification_at else None,
            'should_auto_approve': self.should_auto_approve()
        }
    
    def __repr__(self):
        return f'<ModificationRequest {self.request_id} ({self.request_type})>'