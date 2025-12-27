"""
Order Modification Routes and API Endpoints
RESTful API for handling order modifications
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
import traceback

from models import db
from models.order import Order, OrderItem
from models.menu_item import MenuItem
from models.user import User
from models.order_modification import OrderModification, OrderItemModification, ModificationRequest
from utils.order_modification_workflow import (
    ModificationWorkflowManager, ModificationCalculator, ModificationValidator,
    create_addition_modification, create_removal_modification, 
    create_quantity_modification, create_cancellation_modification
)
from utils.websocket_manager import websocket_manager

# Create blueprint
order_modification_bp = Blueprint('order_modification', __name__, url_prefix='/api/modifications')


@order_modification_bp.route('/order/<int:order_id>/modify', methods=['POST'])
@login_required
def create_modification_request(order_id):
    """Create a new modification request for an order"""
    try:
        data = request.get_json()
        
        # Validate required fields
        modification_type = data.get('modification_type')
        if not modification_type:
            return jsonify({'error': 'modification_type is required'}), 400
        
        # Validate order exists
        order = Order.query.get_or_404(order_id)
        
        # Check if user can modify this order
        if not _can_user_modify_order(order, current_user):
            return jsonify({'error': 'Insufficient permissions to modify this order'}), 403
        
        # Get modification data
        item_modifications = data.get('item_modifications', [])
        reason = data.get('reason', '')
        customer_reason = data.get('customer_reason', '')
        priority = data.get('priority', 'normal')
        
        # Validate item modifications if provided
        if item_modifications:
            validation_result = _validate_item_modifications(item_modifications, modification_type)
            if not validation_result[0]:
                return jsonify({'error': validation_result[1]}), 400
        
        # Calculate price impact
        price_difference = Decimal('0')
        if item_modifications:
            price_difference = ModificationCalculator.calculate_order_modification_cost(
                order_id, [{'modification_type': modification_type, 'items': item_modifications}]
            )
        
        # Validate modification permissions
        validation_result = ModificationValidator.validate_modification_permissions(
            current_user.id, modification_type, price_difference
        )
        if not validation_result[0]:
            return jsonify({'error': validation_result[1]}), 403
        
        # Create modification request
        workflow_manager = ModificationWorkflowManager()
        success, result = workflow_manager.create_modification_request(
            order_id=order_id,
            modification_type=modification_type,
            requested_by_user_id=current_user.id,
            item_modifications=item_modifications,
            reason=reason,
            customer_reason=customer_reason,
            priority=priority,
            source='manual',
            requires_approval=_requires_approval(current_user, modification_type, price_difference)
        )
        
        if not success:
            return jsonify({'error': result}), 400
        
        # Get modification details
        modification = OrderModification.query.get(result)
        modification_details = workflow_manager.get_modification_status(result)
        
        # Broadcast to kitchen displays
        _broadcast_modification_update(modification, 'created')
        
        return jsonify({
            'message': 'Modification request created successfully',
            'modification': modification_details
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating modification request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/<int:modification_id>/approve', methods=['POST'])
@login_required
def approve_modification(modification_id):
    """Approve a modification request"""
    try:
        modification = OrderModification.query.get_or_404(modification_id)
        
        # Check if user can approve this modification
        workflow_manager = ModificationWorkflowManager()
        if not _can_user_approve_modification(modification, current_user):
            return jsonify({'error': 'Insufficient permissions to approve this modification'}), 403
        
        # Get approval data
        data = request.get_json() or {}
        notes = data.get('notes', '')
        
        # Approve modification
        success, message = workflow_manager.approve_modification(
            modification_id, current_user.id, notes
        )
        
        if not success:
            return jsonify({'error': message}), 400
        
        # Get updated modification details
        modification_details = workflow_manager.get_modification_status(modification_id)
        
        # Broadcast to kitchen displays
        _broadcast_modification_update(modification, 'approved')
        
        # Send notifications
        _send_modification_notification(modification, 'approved', current_user)
        
        return jsonify({
            'message': 'Modification approved successfully',
            'modification': modification_details
        })
        
    except Exception as e:
        current_app.logger.error(f"Error approving modification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/<int:modification_id>/reject', methods=['POST'])
@login_required
def reject_modification(modification_id):
    """Reject a modification request"""
    try:
        modification = OrderModification.query.get_or_404(modification_id)
        
        # Check if user can reject this modification
        workflow_manager = ModificationWorkflowManager()
        if not _can_user_approve_modification(modification, current_user):
            return jsonify({'error': 'Insufficient permissions to reject this modification'}), 403
        
        # Get rejection data
        data = request.get_json() or {}
        reason = data.get('reason', '')
        
        if not reason:
            return jsonify({'error': 'Rejection reason is required'}), 400
        
        # Reject modification
        success, message = workflow_manager.reject_modification(
            modification_id, current_user.id, reason
        )
        
        if not success:
            return jsonify({'error': message}), 400
        
        # Get updated modification details
        modification_details = workflow_manager.get_modification_status(modification_id)
        
        # Broadcast to kitchen displays
        _broadcast_modification_update(modification, 'rejected')
        
        # Send notifications
        _send_modification_notification(modification, 'rejected', current_user, reason)
        
        return jsonify({
            'message': 'Modification rejected successfully',
            'modification': modification_details
        })
        
    except Exception as e:
        current_app.logger.error(f"Error rejecting modification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/<int:modification_id>/implement', methods=['POST'])
@login_required
def implement_modification(modification_id):
    """Implement an approved modification"""
    try:
        modification = OrderModification.query.get_or_404(modification_id)
        
        # Check if user can implement this modification
        if not _can_user_implement_modification(modification, current_user):
            return jsonify({'error': 'Insufficient permissions to implement this modification'}), 403
        
        # Get implementation data
        data = request.get_json() or {}
        implementation_notes = data.get('notes', '')
        
        # Implement modification
        workflow_manager = ModificationWorkflowManager()
        success, message = workflow_manager.implement_modification(
            modification_id, current_user.id, implementation_notes
        )
        
        if not success:
            return jsonify({'error': message}), 400
        
        # Get updated modification details
        modification_details = workflow_manager.get_modification_status(modification_id)
        
        # Broadcast to kitchen displays
        _broadcast_modification_update(modification, 'implemented')
        
        # Send notifications
        _send_modification_notification(modification, 'implemented', current_user)
        
        return jsonify({
            'message': 'Modification implemented successfully',
            'modification': modification_details
        })
        
    except Exception as e:
        current_app.logger.error(f"Error implementing modification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/<int:modification_id>/cancel', methods=['POST'])
@login_required
def cancel_modification(modification_id):
    """Cancel a modification request"""
    try:
        modification = OrderModification.query.get_or_404(modification_id)
        
        # Check if user can cancel this modification
        if not (current_user.is_admin() or modification.requested_by_user_id == current_user.id):
            return jsonify({'error': 'Insufficient permissions to cancel this modification'}), 403
        
        # Get cancellation data
        data = request.get_json() or {}
        reason = data.get('reason', '')
        
        if not reason:
            return jsonify({'error': 'Cancellation reason is required'}), 400
        
        # Cancel modification
        workflow_manager = ModificationWorkflowManager()
        success, message = workflow_manager.cancel_modification(
            modification_id, current_user.id, reason
        )
        
        if not success:
            return jsonify({'error': message}), 400
        
        # Get updated modification details
        modification_details = workflow_manager.get_modification_status(modification_id)
        
        # Broadcast to kitchen displays
        _broadcast_modification_update(modification, 'cancelled')
        
        # Send notifications
        _send_modification_notification(modification, 'cancelled', current_user, reason)
        
        return jsonify({
            'message': 'Modification cancelled successfully',
            'modification': modification_details
        })
        
    except Exception as e:
        current_app.logger.error(f"Error cancelling modification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/<int:modification_id>', methods=['GET'])
@login_required
def get_modification(modification_id):
    """Get modification details"""
    try:
        modification = OrderModification.query.get_or_404(modification_id)
        
        # Check if user can view this modification
        if not _can_user_view_modification(modification, current_user):
            return jsonify({'error': 'Insufficient permissions to view this modification'}), 403
        
        workflow_manager = ModificationWorkflowManager()
        modification_details = workflow_manager.get_modification_status(modification_id)
        
        return jsonify(modification_details)
        
    except Exception as e:
        current_app.logger.error(f"Error getting modification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/order/<int:order_id>', methods=['GET'])
@login_required
def get_order_modifications(order_id):
    """Get all modifications for an order"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Check if user can view modifications for this order
        if not _can_user_view_order_modifications(order, current_user):
            return jsonify({'error': 'Insufficient permissions to view modifications for this order'}), 403
        
        modifications = OrderModification.query.filter_by(order_id=order_id).order_by(
            OrderModification.requested_at.desc()
        ).all()
        
        workflow_manager = ModificationWorkflowManager()
        modification_details = [workflow_manager.get_modification_status(mod.id) for mod in modifications]
        
        return jsonify({
            'order_id': order_id,
            'modifications': modification_details
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting order modifications: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/pending', methods=['GET'])
@login_required
def get_pending_modifications():
    """Get pending modifications that require user action"""
    try:
        workflow_manager = ModificationWorkflowManager()
        modifications = workflow_manager.get_pending_modifications(
            user_id=current_user.id,
            role=current_user.role
        )
        
        modification_details = [workflow_manager.get_modification_status(mod.id) for mod in modifications]
        
        return jsonify({
            'pending_modifications': modification_details,
            'count': len(modification_details)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting pending modifications: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/calculate-impact', methods=['POST'])
@login_required
def calculate_modification_impact():
    """Calculate financial impact of proposed modifications"""
    try:
        data = request.get_json()
        
        order_id = data.get('order_id')
        modifications = data.get('modifications', [])
        
        if not order_id or not modifications:
            return jsonify({'error': 'order_id and modifications are required'}), 400
        
        # Validate order exists
        order = Order.query.get_or_404(order_id)
        
        # Calculate total price difference
        price_difference = ModificationCalculator.calculate_order_modification_cost(
            order_id, modifications
        )
        
        # Calculate GST impact
        original_total = order.grand_total
        new_total = original_total + price_difference
        gst_impact = ModificationCalculator.calculate_gst_impact(
            original_total, new_total, order.discount_amount
        )
        
        # Calculate refund amount if applicable
        refund_amount = abs(price_difference) if price_difference < 0 else Decimal('0')
        
        return jsonify({
            'order_id': order_id,
            'original_total': float(original_total),
            'new_total': float(new_total),
            'price_difference': float(price_difference),
            'gst_impact': float(gst_impact),
            'refund_amount': float(refund_amount),
            'requires_payment': price_difference > 0,
            'requires_refund': price_difference < 0
        })
        
    except Exception as e:
        current_app.logger.error(f"Error calculating modification impact: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/quick/add-item', methods=['POST'])
@login_required
def quick_add_item():
    """Quick endpoint to add a single item to an order"""
    try:
        data = request.get_json()
        
        order_id = data.get('order_id')
        menu_item_id = data.get('menu_item_id')
        quantity = data.get('quantity', 1)
        special_instructions = data.get('special_instructions', '')
        
        if not order_id or not menu_item_id:
            return jsonify({'error': 'order_id and menu_item_id are required'}), 400
        
        # Validate addition
        validation_result = ModificationValidator.validate_addition(menu_item_id, quantity)
        if not validation_result[0]:
            return jsonify({'error': validation_result[1]}), 400
        
        # Create addition modification
        additions = [{
            'menu_item_id': menu_item_id,
            'quantity': quantity,
            'special_instructions': special_instructions
        }]
        
        success, result = create_addition_modification(
            order_id, current_user.id, additions, "Quick item addition"
        )
        
        if not success:
            return jsonify({'error': result}), 400
        
        workflow_manager = ModificationWorkflowManager()
        modification_details = workflow_manager.get_modification_status(result)
        
        return jsonify({
            'message': 'Item addition request created',
            'modification': modification_details
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error in quick add item: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/quick/remove-item', methods=['POST'])
@login_required
def quick_remove_item():
    """Quick endpoint to remove a single item from an order"""
    try:
        data = request.get_json()
        
        order_id = data.get('order_id')
        order_item_id = data.get('order_item_id')
        
        if not order_id or not order_item_id:
            return jsonify({'error': 'order_id and order_item_id are required'}), 400
        
        # Validate removal
        validation_result = ModificationValidator.validate_removal(order_item_id)
        if not validation_result[0]:
            return jsonify({'error': validation_result[1]}), 400
        
        # Create removal modification
        removals = [{'order_item_id': order_item_id}]
        
        success, result = create_removal_modification(
            order_id, current_user.id, removals, "Quick item removal"
        )
        
        if not success:
            return jsonify({'error': result}), 400
        
        workflow_manager = ModificationWorkflowManager()
        modification_details = workflow_manager.get_modification_status(result)
        
        return jsonify({
            'message': 'Item removal request created',
            'modification': modification_details
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error in quick remove item: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/quick/change-quantity', methods=['POST'])
@login_required
def quick_change_quantity():
    """Quick endpoint to change quantity of an item in an order"""
    try:
        data = request.get_json()
        
        order_id = data.get('order_id')
        order_item_id = data.get('order_item_id')
        new_quantity = data.get('new_quantity')
        
        if not order_id or not order_item_id or new_quantity is None:
            return jsonify({'error': 'order_id, order_item_id, and new_quantity are required'}), 400
        
        # Validate quantity change
        validation_result = ModificationValidator.validate_quantity_change(order_item_id, new_quantity)
        if not validation_result[0]:
            return jsonify({'error': validation_result[1]}), 400
        
        # Create quantity change modification
        quantity_changes = [{'order_item_id': order_item_id, 'new_quantity': new_quantity}]
        
        success, result = create_quantity_modification(
            order_id, current_user.id, quantity_changes, "Quick quantity change"
        )
        
        if not success:
            return jsonify({'error': result}), 400
        
        workflow_manager = ModificationWorkflowManager()
        modification_details = workflow_manager.get_modification_status(result)
        
        return jsonify({
            'message': 'Quantity change request created',
            'modification': modification_details
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error in quick change quantity: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/quick/cancel-order', methods=['POST'])
@login_required
def quick_cancel_order():
    """Quick endpoint to cancel an order"""
    try:
        data = request.get_json()
        
        order_id = data.get('order_id')
        reason = data.get('reason', '')
        partial = data.get('partial', False)
        
        if not order_id:
            return jsonify({'error': 'order_id is required'}), 400
        
        # Validate cancellation
        validation_result = ModificationValidator.validate_order_cancellation(order_id, reason)
        if not validation_result[0]:
            return jsonify({'error': validation_result[1]}), 400
        
        # Create cancellation modification
        success, result = create_cancellation_modification(
            order_id, current_user.id, reason, partial
        )
        
        if not success:
            return jsonify({'error': result}), 400
        
        workflow_manager = ModificationWorkflowManager()
        modification_details = workflow_manager.get_modification_status(result)
        
        return jsonify({
            'message': 'Order cancellation request created',
            'modification': modification_details
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error in quick cancel order: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@order_modification_bp.route('/kitchen/notifications', methods=['GET'])
@login_required
def get_kitchen_notifications():
    """Get modification notifications for kitchen displays"""
    try:
        if not current_user.is_kitchen_staff():
            return jsonify({'error': 'Kitchen access required'}), 403
        
        # Get recent modifications that affect kitchen
        recent_modifications = OrderModification.query.filter(
            and_(
                OrderModification.created_at >= datetime.utcnow() - timedelta(hours=24),
                OrderModification.modification_type.in_([
                    'add_items', 'remove_items', 'modify_items', 'kitchen_hold'
                ])
            )
        ).order_by(OrderModification.requested_at.desc()).limit(50).all()
        
        notifications = []
        for mod in recent_modifications:
            notification = {
                'modification_id': mod.modification_id,
                'order_number': mod.order.order_number if mod.order else 'Unknown',
                'modification_type': mod.modification_type,
                'status': mod.status,
                'requested_at': mod.requested_at.isoformat(),
                'requested_by': mod.requested_by.username if mod.requested_by else 'Unknown',
                'reason': mod.reason,
                'priority': mod.priority,
                'requires_kitchen_action': mod.status == 'Approved' and mod.modification_type in [
                    'add_items', 'remove_items', 'modify_items'
                ]
            }
            
            # Add item modification details
            if mod.item_modifications:
                notification['item_changes'] = [
                    {
                        'type': item_mod.modification_type,
                        'item_name': item_mod.get_item_name(),
                        'original_quantity': item_mod.original_quantity,
                        'new_quantity': item_mod.new_quantity,
                        'status': item_mod.status
                    }
                    for item_mod in mod.item_modifications
                ]
            
            notifications.append(notification)
        
        return jsonify({
            'notifications': notifications,
            'total_count': len(notifications)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting kitchen notifications: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# Helper functions
def _can_user_modify_order(order, user):
    """Check if user can modify this order"""
    if user.is_admin() or user.is_super_admin():
        return True
    
    if user.is_manager() and order.created_by == user.id:
        return True
    
    # Waiters can modify orders they created
    if user.is_waiter() and order.created_by == user.id:
        return True
    
    return False


def _can_user_view_modification(modification, user):
    """Check if user can view this modification"""
    if user.is_admin() or user.is_super_admin():
        return True
    
    if modification.requested_by_user_id == user.id:
        return True
    
    if modification.order.created_by == user.id:
        return True
    
    return False


def _can_user_view_order_modifications(order, user):
    """Check if user can view modifications for this order"""
    return _can_user_modify_order(order, user)


def _can_user_approve_modification(modification, user):
    """Check if user can approve this modification"""
    if user.is_admin() or user.is_super_admin():
        return True
    
    if user.is_manager() and abs(modification.price_difference) <= 100:
        return True
    
    if (user.is_head_chef() and 
        modification.modification_type in ['kitchen_hold', 'update_instructions', 'change_item']):
        return True
    
    return False


def _can_user_implement_modification(modification, user):
    """Check if user can implement this modification"""
    if user.is_admin() or user.is_super_admin():
        return True
    
    if user.is_kitchen_staff() and modification.status == 'Approved':
        return True
    
    if modification.requested_by_user_id == user.id and modification.status == 'Approved':
        return True
    
    return False


def _requires_approval(user, modification_type, price_difference):
    """Check if modification requires approval"""
    # Auto-approve for admins and managers for small changes
    if user.is_admin() or user.is_super_admin():
        return abs(price_difference) > 50  # Require approval for changes > ₹50
    
    if user.is_manager():
        return abs(price_difference) > 10  # Require approval for changes > ₹10
    
    # Always require approval for other users
    return True


def _validate_item_modifications(item_modifications, modification_type):
    """Validate item modifications based on type"""
    for item_mod in item_modifications:
        mod_type = item_mod.get('modification_type')
        
        if mod_type == 'add_item':
            menu_item_id = item_mod.get('original_menu_item_id')
            quantity = item_mod.get('new_quantity', 1)
            validation = ModificationValidator.validate_addition(menu_item_id, quantity)
            if not validation[0]:
                return validation
        
        elif mod_type == 'remove_item':
            order_item_id = item_mod.get('order_item_id')
            validation = ModificationValidator.validate_removal(order_item_id)
            if not validation[0]:
                return validation
        
        elif mod_type == 'change_quantity':
            order_item_id = item_mod.get('order_item_id')
            new_quantity = item_mod.get('new_quantity')
            validation = ModificationValidator.validate_quantity_change(order_item_id, new_quantity)
            if not validation[0]:
                return validation
        
        elif mod_type == 'change_item':
            order_item_id = item_mod.get('order_item_id')
            new_menu_item_id = item_mod.get('new_menu_item_id')
            new_quantity = item_mod.get('new_quantity')
            validation = ModificationValidator.validate_item_substitution(
                order_item_id, new_menu_item_id, new_quantity
            )
            if not validation[0]:
                return validation
    
    return True, "All item modifications validated"


def _broadcast_modification_update(modification, action):
    """Broadcast modification update via WebSocket"""
    try:
        from routes.websocket import broadcast_to_kitchen_displays
        
        update_data = {
            'type': 'modification_update',
            'action': action,
            'modification_id': modification.modification_id,
            'order_id': modification.order_id,
            'order_number': modification.order.order_number if modification.order else 'Unknown',
            'modification_type': modification.modification_type,
            'status': modification.status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Broadcast to all kitchen displays
        broadcast_to_kitchen_displays('modification_update', update_data)
        
    except Exception as e:
        current_app.logger.error(f"Error broadcasting modification update: {str(e)}")


def _send_modification_notification(modification, action, user, reason=None):
    """Send notifications for modification events"""
    try:
        # This would integrate with your notification system
        # For now, just log the notification
        message = f"Modification {modification.modification_id} {action} by {user.username}"
        if reason:
            message += f". Reason: {reason}"
        
        current_app.logger.info(message)
        
        # You could send email notifications, push notifications, etc. here
        
    except Exception as e:
        current_app.logger.error(f"Error sending modification notification: {str(e)}")