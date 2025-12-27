"""
Order Modification Business Logic and Workflow
Core business logic for handling different types of order modifications
"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_

# Import from models package instead of utils
from models import db
from models.order import Order, OrderItem
from models.menu_item import MenuItem
from models.order_modification import OrderModification, OrderItemModification, ModificationRequest
from models.user import User


class ModificationWorkflowManager:
    """Manages the complete order modification workflow"""
    
    def __init__(self):
        self.supported_modification_types = [
            'add_items',
            'remove_items', 
            'modify_items',
            'cancel_order',
            'partial_cancel',
            'kitchen_hold'
        ]
    
    def create_modification_request(self, order_id, modification_type, requested_by_user_id, 
                                  item_modifications=None, reason=None, customer_reason=None,
                                  priority='normal', source='manual', requires_approval=True):
        """Create a new modification request"""
        try:
            # Validate order exists and is modifiable
            order = db.session.query(Order).get(order_id)
            if not order:
                return False, "Order not found"
            
            if not self._can_modify_order(order):
                return False, "Order cannot be modified in its current status"
            
            # Validate modification type
            if modification_type not in self.supported_modification_types:
                return False, f"Unsupported modification type: {modification_type}"
            
            # Create main modification record
            modification = OrderModification(
                order_id=order_id,
                modification_type=modification_type,
                requested_by_user_id=requested_by_user_id,
                reason=reason,
                customer_reason=customer_reason,
                requires_approval=requires_approval,
                source=source,
                priority=priority
            )
            
            # Create item modifications if provided
            if item_modifications:
                for item_mod_data in item_modifications:
                    item_mod = self._create_item_modification(modification, item_mod_data)
                    if not item_mod:
                        return False, f"Failed to create item modification: {item_mod_data}"
            
            # Create modification request for approval workflow
            modification_request = ModificationRequest(
                modification_id=modification.id,
                order_id=order_id,
                request_type='customer_request' if source == 'customer' else 'manager_initiated',
                priority=priority
            )
            
            db.session.add(modification)
            db.session.add(modification_request)
            db.session.commit()
            
            # Send notifications based on approval requirements
            if requires_approval:
                self._send_modification_notification(modification, modification_request)
            
            # Auto-approve if criteria met
            if modification_request.should_auto_approve():
                self._auto_approve_modification(modification, modification_request)
            
            return True, modification.id
            
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to create modification request: {str(e)}"
    
    def _can_modify_order(self, order):
        """Check if order can be modified based on status and timing"""
        # Cannot modify completed or cancelled orders
        if order.status in ['Completed', 'Cancelled']:
            return False
        
        # Check time-based modification limits
        if order.status == 'In Progress':
            # Allow modifications within reasonable time after order starts
            time_elapsed = datetime.utcnow() - order.updated_at
            if time_elapsed > timedelta(minutes=30):  # 30 minutes limit
                return False
        
        return True
    
    def _create_item_modification(self, modification, item_mod_data):
        """Create an individual item modification"""
        try:
            modification_type = item_mod_data.get('modification_type')
            original_menu_item_id = item_mod_data.get('original_menu_item_id')
            original_quantity = item_mod_data.get('original_quantity', 1)
            original_price = item_mod_data.get('original_price', 0)
            
            item_modification = OrderItemModification(
                modification_id=modification.id,
                modification_type=modification_type,
                original_menu_item_id=original_menu_item_id,
                original_quantity=original_quantity,
                original_price=original_price,
                order_item_id=item_mod_data.get('order_item_id')
            )
            
            # Set additional fields based on modification type
            if modification_type == 'add_item':
                item_modification.new_quantity = item_mod_data.get('new_quantity', original_quantity)
                item_modification.new_price = item_mod_data.get('new_price', original_price)
            elif modification_type == 'change_quantity':
                item_modification.new_quantity = item_mod_data.get('new_quantity')
                item_modification.new_price = original_price
            elif modification_type == 'change_item':
                item_modification.new_menu_item_id = item_mod_data.get('new_menu_item_id')
                item_modification.new_price = item_mod_data.get('new_price')
                item_modification.new_quantity = original_quantity
            elif modification_type in ['remove_item', 'update_instructions']:
                item_modification.new_quantity = 0 if modification_type == 'remove_item' else original_quantity
                item_modification.new_price = original_price
            
            # Set instructions if provided
            if 'new_instructions' in item_mod_data:
                item_modification.new_instructions = item_mod_data['new_instructions']
            if 'original_instructions' in item_mod_data:
                item_modification.original_instructions = item_mod_data['original_instructions']
            
            # Calculate price difference
            item_modification.price_difference = item_modification.calculate_price_difference()
            
            db.session.add(item_modification)
            return item_modification
            
        except Exception as e:
            print(f"Error creating item modification: {e}")
            return None
    
    def _send_modification_notification(self, modification, modification_request):
        """Send notifications about modification request"""
        # This would integrate with your notification system
        # For now, just log the notification
        print(f"Sending modification notification for {modification.modification_id}")
        
        # Update notification tracking
        modification_request.send_notification()
    
    def _auto_approve_modification(self, modification, modification_request):
        """Auto-approve modification based on criteria"""
        try:
            # Auto-approve for small changes
            if abs(modification.price_difference) <= 10:  # ₹10 or less
                modification.approve(modification.requested_by_user_id, "Auto-approved: Small value change")
                modification_request.status = 'Approved'
                db.session.commit()
                return True
            
            # Auto-approve for specific modification types
            if modification.modification_type in ['update_instructions']:
                modification.approve(modification.requested_by_user_id, "Auto-approved: Instruction change")
                modification_request.status = 'Approved'
                db.session.commit()
                return True
            
            return False
            
        except Exception as e:
            print(f"Auto-approval failed: {e}")
            return False
    
    def approve_modification(self, modification_id, approved_by_user_id, notes=None):
        """Approve a modification request"""
        try:
            modification = db.session.query(OrderModification).get(modification_id)
            if not modification:
                return False, "Modification not found"
            
            # Check permissions
            approved_by = db.session.query(User).get(approved_by_user_id)
            if not self._can_approve_modification(modification, approved_by):
                return False, "Insufficient permissions to approve this modification"
            
            # Approve modification
            success, message = modification.approve(approved_by_user_id, notes)
            if success:
                # Update related request
                modification_request = modification.modification_request
                if modification_request:
                    modification_request.status = 'Approved'
                
                # Start implementation if auto-approved
                if modification.auto_approved:
                    self._start_modification_implementation(modification)
                
                db.session.commit()
                
                # Send notifications
                self._send_approval_notification(modification, approved_by)
                
            return success, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to approve modification: {str(e)}"
    
    def reject_modification(self, modification_id, rejected_by_user_id, reason):
        """Reject a modification request"""
        try:
            modification = db.session.query(OrderModification).get(modification_id)
            if not modification:
                return False, "Modification not found"
            
            # Check permissions
            rejected_by = db.session.query(User).get(rejected_by_user_id)
            if not self._can_approve_modification(modification, rejected_by):
                return False, "Insufficient permissions to reject this modification"
            
            # Reject modification
            success, message = modification.reject(rejected_by_user_id, reason)
            if success:
                # Update related request
                modification_request = modification.modification_request
                if modification_request:
                    modification_request.status = 'Rejected'
                
                db.session.commit()
                
                # Send notifications
                self._send_rejection_notification(modification, rejected_by, reason)
                
            return success, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to reject modification: {str(e)}"
    
    def _can_approve_modification(self, modification, approver):
        """Check if user can approve this modification"""
        if not approver:
            return False
        
        # Super admin and admin can approve anything
        if approver.is_super_admin() or approver.is_admin():
            return True
        
        # Manager can approve modifications under ₹100
        if approver.is_manager() and abs(modification.price_difference) <= 100:
            return True
        
        # Head chef can approve kitchen-related modifications
        if (approver.is_head_chef() and 
            modification.modification_type in ['kitchen_hold', 'update_instructions', 'change_item']):
            return True
        
        return False
    
    def _start_modification_implementation(self, modification):
        """Start implementing an approved modification"""
        # Assign to appropriate user based on modification type
        if modification.modification_type in ['add_items', 'remove_items', 'modify_items']:
            # Assign to kitchen staff
            kitchen_staff = User.query.filter(User.role.in_(['chef', 'head_chef', 'kitchen_staff'])).first()
            if kitchen_staff:
                modification.start_implementation(kitchen_staff.id)
    
    def implement_modification(self, modification_id, implemented_by_user_id, implementation_notes=None):
        """Implement an approved modification"""
        try:
            modification = db.session.query(OrderModification).get(modification_id)
            if not modification:
                return False, "Modification not found"
            
            if modification.status != 'Approved':
                return False, "Modification must be approved before implementation"
            
            # Start implementation
            modification.start_implementation(implemented_by_user_id)
            
            # Apply item modifications
            success_count = 0
            error_messages = []
            
            for item_mod in modification.item_modifications:
                try:
                    success, message = item_mod.apply(implemented_by_user_id)
                    if success:
                        success_count += 1
                    else:
                        error_messages.append(f"Item {item_mod.id}: {message}")
                except Exception as e:
                    error_messages.append(f"Item {item_mod.id}: {str(e)}")
            
            # Calculate new total
            order = modification.order
            order.calculate_totals()
            new_total = order.grand_total
            
            # Complete modification
            if error_messages:
                modification.mark_failed(f"Implementation completed with errors: {'; '.join(error_messages)}")
                return False, f"Implementation completed with {len(error_messages)} errors"
            else:
                modification.complete_implementation(implementation_notes, new_total)
                
                # Update order status if needed
                if modification.modification_type == 'cancel_order':
                    order.update_status('Cancelled')
                elif modification.modification_type == 'kitchen_hold':
                    order.status = 'New'  # Reset to new for kitchen
                
                db.session.commit()
                
                # Send notifications
                self._send_completion_notification(modification)
                
                return True, f"Modification implemented successfully ({success_count} items modified)"
                
        except Exception as e:
            db.session.rollback()
            modification.mark_failed(f"Implementation failed: {str(e)}")
            return False, f"Failed to implement modification: {str(e)}"
    
    def cancel_modification(self, modification_id, cancelled_by_user_id, reason):
        """Cancel a modification request"""
        try:
            modification = db.session.query(OrderModification).get(modification_id)
            if not modification:
                return False, "Modification not found"
            
            # Check if user can cancel
            cancelled_by = db.session.query(User).get(cancelled_by_user_id)
            if not (cancelled_by.is_admin() or modification.requested_by_user_id == cancelled_by_user_id):
                return False, "Insufficient permissions to cancel this modification"
            
            # Cancel modification
            success, message = modification.cancel(cancelled_by_user_id, reason)
            if success:
                # Update related request
                modification_request = modification.modification_request
                if modification_request:
                    modification_request.status = 'Cancelled'
                
                db.session.commit()
                
                # Send notifications
                self._send_cancellation_notification(modification, cancelled_by, reason)
                
            return success, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to cancel modification: {str(e)}"
    
    def _send_approval_notification(self, modification, approver):
        """Send notification when modification is approved"""
        print(f"Modification {modification.modification_id} approved by {approver.username}")
    
    def _send_rejection_notification(self, modification, rejector, reason):
        """Send notification when modification is rejected"""
        print(f"Modification {modification.modification_id} rejected by {rejector.username}: {reason}")
    
    def _send_completion_notification(self, modification):
        """Send notification when modification is completed"""
        print(f"Modification {modification.modification_id} completed successfully")
    
    def _send_cancellation_notification(self, modification, canceller, reason):
        """Send notification when modification is cancelled"""
        print(f"Modification {modification.modification_id} cancelled by {canceller.username}: {reason}")
    
    def get_modification_status(self, modification_id):
        """Get detailed status of a modification"""
        modification = db.session.query(OrderModification).get(modification_id)
        if not modification:
            return None
        
        status_info = modification.to_dict()
        
        # Add item modification details
        status_info['item_modifications'] = [item_mod.to_dict() for item_mod in modification.item_modifications]
        
        # Add request details if exists
        if modification.modification_request:
            status_info['request_info'] = modification.modification_request.to_dict()
        
        return status_info
    
    def get_pending_modifications(self, user_id=None, role=None):
        """Get pending modifications for a user or role"""
        query = db.session.query(OrderModification).filter(
            OrderModification.status == 'Pending'
        )
        
        if user_id:
            query = query.filter(OrderModification.requested_by_user_id != user_id)
        
        if role:
            # Filter based on approval permissions
            if role in ['admin', 'super_admin']:
                pass  # Can see all pending modifications
            elif role == 'manager':
                query = query.filter(OrderModification.price_difference <= 100)
            elif role == 'head_chef':
                query = query.filter(OrderModification.modification_type.in_([
                    'kitchen_hold', 'update_instructions', 'change_item'
                ]))
        
        return query.order_by(OrderModification.requested_at.desc()).all()


class ModificationCalculator:
    """Calculates financial impact of modifications"""
    
    @staticmethod
    def calculate_addition_cost(additions):
        """Calculate cost of adding items"""
        total_cost = Decimal('0')
        
        for addition in additions:
            menu_item = db.session.query(MenuItem).get(addition['menu_item_id'])
            if menu_item:
                item_cost = Decimal(str(addition['quantity'])) * menu_item.price
                total_cost += item_cost
        
        return total_cost
    
    @staticmethod
    def calculate_removal_refund(removals):
        """Calculate refund for removed items"""
        total_refund = Decimal('0')
        
        for removal in removals:
            order_item = db.session.query(OrderItem).get(removal['order_item_id'])
            if order_item:
                item_refund = order_item.total
                total_refund += item_refund
        
        return total_refund
    
    @staticmethod
    def calculate_quantity_change_cost(order_item_id, new_quantity):
        """Calculate cost difference for quantity changes"""
        order_item = db.session.query(OrderItem).get(order_item_id)
        if not order_item:
            return Decimal('0')
        
        original_total = order_item.total
        new_total = Decimal(str(new_quantity)) * order_item.price
        
        return new_total - original_total
    
    @staticmethod
    def calculate_item_substitution_cost(order_item_id, new_menu_item_id, new_quantity=None):
        """Calculate cost difference for item substitutions"""
        order_item = db.session.query(OrderItem).get(order_item_id)
        new_menu_item = db.session.query(MenuItem).get(new_menu_item_id)
        
        if not order_item or not new_menu_item:
            return Decimal('0')
        
        original_total = order_item.total
        quantity = new_quantity or order_item.quantity
        new_total = Decimal(str(quantity)) * new_menu_item.price
        
        return new_total - original_total
    
    @staticmethod
    def calculate_order_modification_cost(order_id, modifications):
        """Calculate total cost impact of multiple modifications"""
        order = db.session.query(Order).get(order_id)
        if not order:
            return Decimal('0')
        
        total_difference = Decimal('0')
        
        for mod in modifications:
            mod_type = mod.get('modification_type')
            
            if mod_type == 'add_items':
                total_difference += ModificationCalculator.calculate_addition_cost(mod.get('items', []))
            elif mod_type == 'remove_items':
                total_difference -= ModificationCalculator.calculate_removal_refund(mod.get('items', []))
            elif mod_type == 'change_quantity':
                for item_change in mod.get('items', []):
                    cost_diff = ModificationCalculator.calculate_quantity_change_cost(
                        item_change['order_item_id'], 
                        item_change['new_quantity']
                    )
                    total_difference += cost_diff
            elif mod_type == 'change_item':
                for item_change in mod.get('items', []):
                    cost_diff = ModificationCalculator.calculate_item_substitution_cost(
                        item_change['order_item_id'],
                        item_change['new_menu_item_id'],
                        item_change.get('new_quantity')
                    )
                    total_difference += cost_diff
        
        return total_difference
    
    @staticmethod
    def calculate_gst_impact(original_amount, new_amount, discount_amount=Decimal('0')):
        """Calculate GST impact of modification"""
        # GST calculation for the difference
        original_taxable = original_amount - discount_amount
        new_taxable = new_amount - discount_amount
        
        gst_rate = Decimal('0.05')  # 5% total GST (2.5% CGST + 2.5% SGST)
        
        original_gst = original_taxable * gst_rate
        new_gst = new_taxable * gst_rate
        
        return new_gst - original_gst


class ModificationValidator:
    """Validates modification requests for business rules"""
    
    @staticmethod
    def validate_addition(menu_item_id, quantity):
        """Validate item addition"""
        menu_item = db.session.query(MenuItem).get(menu_item_id)
        if not menu_item:
            return False, "Menu item not found"
        
        if not menu_item.is_active or not menu_item.is_available:
            return False, "Menu item is not available"
        
        if menu_item.stock_quantity < quantity:
            return False, f"Insufficient stock. Available: {menu_item.stock_quantity}"
        
        return True, "Addition validated"
    
    @staticmethod
    def validate_removal(order_item_id):
        """Validate item removal"""
        order_item = db.session.query(OrderItem).get(order_item_id)
        if not order_item:
            return False, "Order item not found"
        
        if order_item.status in ['Completed', 'Cancelled']:
            return False, "Cannot remove completed or cancelled items"
        
        return True, "Removal validated"
    
    @staticmethod
    def validate_quantity_change(order_item_id, new_quantity):
        """Validate quantity change"""
        if new_quantity <= 0:
            return False, "Quantity must be positive"
        
        order_item = db.session.query(OrderItem).get(order_item_id)
        if not order_item:
            return False, "Order item not found"
        
        menu_item = order_item.menu_item
        if not menu_item:
            return False, "Menu item not found"
        
        # Check stock for increases
        if new_quantity > order_item.quantity:
            stock_needed = new_quantity - order_item.quantity
            if menu_item.stock_quantity < stock_needed:
                return False, f"Insufficient stock. Available: {menu_item.stock_quantity}"
        
        return True, "Quantity change validated"
    
    @staticmethod
    def validate_item_substitution(order_item_id, new_menu_item_id, new_quantity=None):
        """Validate item substitution"""
        order_item = db.session.query(OrderItem).get(order_item_id)
        new_menu_item = db.session.query(MenuItem).get(new_menu_item_id)
        
        if not order_item:
            return False, "Order item not found"
        
        if not new_menu_item:
            return False, "New menu item not found"
        
        if not new_menu_item.is_active or not new_menu_item.is_available:
            return False, "New menu item is not available"
        
        # Check stock for the new item
        quantity = new_quantity or order_item.quantity
        if new_menu_item.stock_quantity < quantity:
            return False, f"Insufficient stock for new item. Available: {new_menu_item.stock_quantity}"
        
        return True, "Item substitution validated"
    
    @staticmethod
    def validate_order_cancellation(order_id, reason):
        """Validate order cancellation"""
        order = db.session.query(Order).get(order_id)
        if not order:
            return False, "Order not found"
        
        if order.status in ['Completed', 'Cancelled']:
            return False, "Order is already completed or cancelled"
        
        if not reason or len(reason.strip()) < 5:
            return False, "Cancellation reason must be provided (minimum 5 characters)"
        
        return True, "Order cancellation validated"
    
    @staticmethod
    def validate_modification_permissions(user_id, modification_type, price_difference):
        """Validate user permissions for modification"""
        user = db.session.query(User).get(user_id)
        if not user:
            return False, "User not found"
        
        # Check role-based permissions
        if user.is_super_admin() or user.is_admin():
            return True, "Full permissions granted"
        
        if user.is_manager():
            # Manager can approve modifications under ₹100
            if abs(price_difference) <= 100:
                return True, "Manager permissions granted"
            else:
                return False, "Modification exceeds manager approval limit"
        
        if user.is_head_chef():
            # Head chef can handle kitchen-related modifications
            kitchen_modifications = ['kitchen_hold', 'update_instructions', 'change_item']
            if modification_type in kitchen_modifications:
                return True, "Head chef permissions granted"
        
        return False, "Insufficient permissions for this modification type"


# Convenience functions for common modification scenarios
def create_addition_modification(order_id, user_id, additions, reason=None):
    """Create a modification request for adding items"""
    workflow = ModificationWorkflowManager()
    
    item_modifications = []
    for addition in additions:
        item_modifications.append({
            'modification_type': 'add_item',
            'original_menu_item_id': addition['menu_item_id'],
            'original_quantity': 0,
            'original_price': 0,
            'new_quantity': addition['quantity'],
            'new_price': addition.get('price', 0),
            'new_instructions': addition.get('special_instructions')
        })
    
    return workflow.create_modification_request(
        order_id=order_id,
        modification_type='add_items',
        requested_by_user_id=user_id,
        item_modifications=item_modifications,
        reason=reason,
        source='customer'
    )


def create_removal_modification(order_id, user_id, removals, reason=None):
    """Create a modification request for removing items"""
    workflow = ModificationWorkflowManager()
    
    item_modifications = []
    for removal in removals:
        order_item = db.session.query(OrderItem).get(removal['order_item_id'])
        if order_item:
            item_modifications.append({
                'modification_type': 'remove_item',
                'original_menu_item_id': order_item.menu_item_id,
                'original_quantity': order_item.quantity,
                'original_price': order_item.price,
                'order_item_id': removal['order_item_id']
            })
    
    return workflow.create_modification_request(
        order_id=order_id,
        modification_type='remove_items',
        requested_by_user_id=user_id,
        item_modifications=item_modifications,
        reason=reason,
        source='customer'
    )


def create_quantity_modification(order_id, user_id, quantity_changes, reason=None):
    """Create a modification request for changing quantities"""
    workflow = ModificationWorkflowManager()
    
    item_modifications = []
    for change in quantity_changes:
        order_item = db.session.query(OrderItem).get(change['order_item_id'])
        if order_item:
            item_modifications.append({
                'modification_type': 'change_quantity',
                'original_menu_item_id': order_item.menu_item_id,
                'original_quantity': order_item.quantity,
                'original_price': order_item.price,
                'order_item_id': change['order_item_id'],
                'new_quantity': change['new_quantity']
            })
    
    return workflow.create_modification_request(
        order_id=order_id,
        modification_type='modify_items',
        requested_by_user_id=user_id,
        item_modifications=item_modifications,
        reason=reason,
        source='customer'
    )


def create_cancellation_modification(order_id, user_id, reason, partial=False):
    """Create a modification request for order cancellation"""
    workflow = ModificationWorkflowManager()
    
    modification_type = 'partial_cancel' if partial else 'cancel_order'
    
    return workflow.create_modification_request(
        order_id=order_id,
        modification_type=modification_type,
        requested_by_user_id=user_id,
        item_modifications=None,  # For cancellations, no individual item mods needed
        reason=reason,
        source='customer',
        requires_approval=True
    )