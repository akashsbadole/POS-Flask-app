"""
Advanced Order Workflow Engine for Restaurant POS System

This module provides comprehensive workflow management for order processing
with role-based actions, real-time notifications, and audit logging.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from flask import current_app
from flask_login import current_user
from models import db, Order, OrderItem, MenuItem, User
from utils.permissions import has_permission, get_user_permissions


class OrderWorkflowState(Enum):
    """Order workflow states"""
    NEW = "New"
    IN_KITCHEN = "In Kitchen"
    READY = "Ready"
    SERVED = "Served"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class WorkflowAction(Enum):
    """Available workflow actions"""
    CREATE_ORDER = "create_order"
    SEND_TO_KITCHEN = "send_to_kitchen"
    MARK_READY = "mark_ready"
    SERVE_ORDER = "serve_order"
    COMPLETE_ORDER = "complete_order"
    CANCEL_ORDER = "cancel_order"
    MODIFY_ORDER = "modify_order"


class OrderWorkflowEngine:
    """Core workflow engine for order processing"""
    
    # Define valid state transitions
    VALID_TRANSITIONS = {
        OrderWorkflowState.NEW: [OrderWorkflowState.IN_KITCHEN, OrderWorkflowState.CANCELLED],
        OrderWorkflowState.IN_KITCHEN: [OrderWorkflowState.READY, OrderWorkflowState.CANCELLED],
        OrderWorkflowState.READY: [OrderWorkflowState.SERVED, OrderWorkflowState.CANCELLED],
        OrderWorkflowState.SERVED: [OrderWorkflowState.COMPLETED],
        OrderWorkflowState.COMPLETED: [],
        OrderWorkflowState.CANCELLED: []
    }
    
    # Define role-based permissions for actions
    ROLE_ACTIONS = {
        'waiter': [
            WorkflowAction.CREATE_ORDER,
            WorkflowAction.SEND_TO_KITCHEN,
            WorkflowAction.SERVE_ORDER,
            WorkflowAction.MODIFY_ORDER
        ],
        'kitchen_staff': [
            WorkflowAction.MARK_READY,
            WorkflowAction.MODIFY_ORDER
        ],
        'cashier': [
            WorkflowAction.COMPLETE_ORDER,
            WorkflowAction.CANCEL_ORDER
        ],
        'manager': [
            WorkflowAction.CREATE_ORDER,
            WorkflowAction.SEND_TO_KITCHEN,
            WorkflowAction.MARK_READY,
            WorkflowAction.SERVE_ORDER,
            WorkflowAction.COMPLETE_ORDER,
            WorkflowAction.CANCEL_ORDER,
            WorkflowAction.MODIFY_ORDER
        ],
        'admin': [
            WorkflowAction.CREATE_ORDER,
            WorkflowAction.SEND_TO_KITCHEN,
            WorkflowAction.MARK_READY,
            WorkflowAction.SERVE_ORDER,
            WorkflowAction.COMPLETE_ORDER,
            WorkflowAction.CANCEL_ORDER,
            WorkflowAction.MODIFY_ORDER
        ]
    }
    
    def __init__(self):
        self.audit_logs = []
    
    def can_perform_action(self, user: User, action: WorkflowAction, order: Order) -> Tuple[bool, str]:
        """
        Check if user can perform specific action on order
        
        Args:
            user: User performing the action
            action: Action to perform
            order: Order being acted upon
            
        Returns:
            Tuple of (can_perform, reason)
        """
        # Check if user has permission for this action
        if not self._has_permission(user, action):
            return False, f"Insufficient permissions for {action.value}"
        
        # Check if transition is valid
        if not self._is_valid_transition(order.status, self._get_next_state(action, order)):
            return False, f"Invalid transition from {order.status} for action {action.value}"
        
        # Check business rules
        business_reason = self._check_business_rules(user, action, order)
        if business_reason:
            return False, business_reason
        
        return True, "Action permitted"
    
    def execute_workflow_action(self, user: User, order_id: int, action: WorkflowAction, 
                              data: Dict = None) -> Tuple[bool, str, Dict]:
        """
        Execute workflow action with proper validation and logging
        
        Args:
            user: User performing the action
            order_id: ID of order
            action: Action to perform
            data: Additional action data
            
        Returns:
            Tuple of (success, message, result_data)
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return False, "Order not found", {}
            
            # Check permissions
            can_perform, reason = self.can_perform_action(user, action, order)
            if not can_perform:
                return False, reason, {}
            
            # Execute the action
            result = self._execute_action(user, order, action, data or {})
            
            # Log the action
            self._log_workflow_action(user, order, action, data or {}, result)
            
            # Send notifications
            self._send_notifications(order, action, user)
            
            # Update workflow metrics
            self._update_workflow_metrics(order, action)
            
            db.session.commit()
            
            return True, f"Action {action.value} completed successfully", result
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error executing workflow action: {str(e)}", {}
    
    def _has_permission(self, user: User, action: WorkflowAction) -> bool:
        """Check if user has permission for action"""
        user_role = user.role.lower()
        allowed_actions = self.ROLE_ACTIONS.get(user_role, [])
        return action in allowed_actions
    
    def _is_valid_transition(self, current_state: str, next_state: OrderWorkflowState) -> bool:
        """Check if transition is valid"""
        try:
            current_enum = OrderWorkflowState(current_state)
            return next_state in self.VALID_TRANSITIONS.get(current_enum, [])
        except ValueError:
            return False
    
    def _get_next_state(self, action: WorkflowAction, order: Order) -> OrderWorkflowState:
        """Get next state based on action"""
        state_mapping = {
            WorkflowAction.SEND_TO_KITCHEN: OrderWorkflowState.IN_KITCHEN,
            WorkflowAction.MARK_READY: OrderWorkflowState.READY,
            WorkflowAction.SERVE_ORDER: OrderWorkflowState.SERVED,
            WorkflowAction.COMPLETE_ORDER: OrderWorkflowState.COMPLETED,
            WorkflowAction.CANCEL_ORDER: OrderWorkflowState.CANCELLED
        }
        return state_mapping.get(action, OrderWorkflowState.NEW)
    
    def _check_business_rules(self, user: User, action: WorkflowAction, order: Order) -> Optional[str]:
        """Check business rules for action"""
        # Example business rules
        if action == WorkflowAction.CANCEL_ORDER:
            if order.status == OrderWorkflowState.COMPLETED.value:
                return "Cannot cancel completed order"
            if order.payments:
                return "Cannot cancel order with payments"
        
        if action == WorkflowAction.COMPLETE_ORDER:
            if not order.payments:
                return "Cannot complete order without payment"
            if order.status != OrderWorkflowState.SERVED.value:
                return "Order must be served before completion"
        
        if action == WorkflowAction.SEND_TO_KITCHEN:
            if not order.order_items:
                return "Cannot send empty order to kitchen"
        
        return None
    
    def _execute_action(self, user: User, order: Order, action: WorkflowAction, data: Dict) -> Dict:
        """Execute the specific action"""
        result = {'order_id': order.id, 'action': action.value}
        
        if action == WorkflowAction.CREATE_ORDER:
            return self._create_order(user, data)
        
        elif action == WorkflowAction.SEND_TO_KITCHEN:
            return self._send_to_kitchen(order, user, data)
        
        elif action == WorkflowAction.MARK_READY:
            return self._mark_ready(order, user, data)
        
        elif action == WorkflowAction.SERVE_ORDER:
            return self._serve_order(order, user, data)
        
        elif action == WorkflowAction.COMPLETE_ORDER:
            return self._complete_order(order, user, data)
        
        elif action == WorkflowAction.CANCEL_ORDER:
            return self._cancel_order(order, user, data)
        
        elif action == WorkflowAction.MODIFY_ORDER:
            return self._modify_order(order, user, data)
        
        return result
    
    def _create_order(self, user: User, data: Dict) -> Dict:
        """Create new order"""
        order = Order()
        order.order_number = Order.generate_order_number()
        order.customer_name = data.get('customer_name')
        order.customer_mobile = data.get('customer_mobile')
        order.order_type = data.get('order_type', 'Dine-in')
        order.table_id = data.get('table_id')
        order.special_instructions = data.get('special_instructions', '')
        order.status = OrderWorkflowState.NEW.value
        order.created_by = user.id
        order.created_at = datetime.utcnow()
        
        db.session.add(order)
        db.session.flush()
        
        return {'order_id': order.id, 'order_number': order.order_number}
    
    def _send_to_kitchen(self, order: Order, user: User, data: Dict) -> Dict:
        """Send order to kitchen"""
        order.status = OrderWorkflowState.IN_KITCHEN.value
        order.updated_at = datetime.utcnow()
        
        # Update all order items to In Progress
        for item in order.order_items:
            if item.status == 'Pending':
                item.status = 'In Progress'
                item.updated_at = datetime.utcnow()
        
        # Update table status if dine-in
        if order.table_id:
            from models.table import Table
            table = Table.query.get(order.table_id)
            if table:
                table.status = 'Occupied'
        
        return {'order_id': order.id, 'status': order.status}
    
    def _mark_ready(self, order: Order, user: User, data: Dict) -> Dict:
        """Mark order as ready"""
        order.status = OrderWorkflowState.READY.value
        order.updated_at = datetime.utcnow()
        
        # Update all order items to Ready
        for item in order.order_items:
            if item.status == 'In Progress':
                item.status = 'Ready'
                item.updated_at = datetime.utcnow()
        
        return {'order_id': order.id, 'status': order.status}
    
    def _serve_order(self, order: Order, user: User, data: Dict) -> Dict:
        """Mark order as served"""
        order.status = OrderWorkflowState.SERVED.value
        order.updated_at = datetime.utcnow()
        
        # Update all order items to Completed
        for item in order.order_items:
            if item.status == 'Ready':
                item.status = 'Completed'
                item.updated_at = datetime.utcnow()
        
        return {'order_id': order.id, 'status': order.status}
    
    def _complete_order(self, order: Order, user: User, data: Dict) -> Dict:
        """Complete order"""
        order.status = OrderWorkflowState.COMPLETED.value
        order.completed_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        # Update table status if dine-in
        if order.table_id:
            from models.table import Table
            table = Table.query.get(order.table_id)
            if table:
                table.status = 'Available'
                table.is_available = True
        
        return {'order_id': order.id, 'status': order.status, 'completed_at': order.completed_at}
    
    def _cancel_order(self, order: Order, user: User, data: Dict) -> Dict:
        """Cancel order"""
        order.status = OrderWorkflowState.CANCELLED.value
        order.updated_at = datetime.utcnow()
        
        # Restore stock for all items
        for item in order.order_items:
            menu_item = item.menu_item
            if menu_item:
                menu_item.stock_quantity += item.quantity
        
        # Update table status if dine-in
        if order.table_id:
            from models.table import Table
            table = Table.query.get(order.table_id)
            if table:
                table.status = 'Available'
                table.is_available = True
        
        return {'order_id': order.id, 'status': order.status}
    
    def _modify_order(self, order: Order, user: User, data: Dict) -> Dict:
        """Modify order"""
        # Implementation depends on specific modification requirements
        modifications = data.get('modifications', {})
        
        for field, value in modifications.items():
            if hasattr(order, field):
                setattr(order, field, value)
        
        order.updated_at = datetime.utcnow()
        
        return {'order_id': order.id, 'modifications': modifications}
    
    def _log_workflow_action(self, user: User, order: Order, action: WorkflowAction, 
                           data: Dict, result: Dict):
        """Log workflow action for audit trail"""
        log_entry = {
            'timestamp': datetime.utcnow(),
            'user_id': user.id,
            'username': user.username,
            'order_id': order.id,
            'order_number': order.order_number,
            'action': action.value,
            'from_status': order.status,
            'data': data,
            'result': result
        }
        self.audit_logs.append(log_entry)
    
    def _send_notifications(self, order: Order, action: WorkflowAction, user: User):
        """Send notifications for workflow actions"""
        try:
            # Email notifications
            self._send_email_notification(order, action, user)
            
            # WebSocket notifications
            self._send_websocket_notification(order, action, user)
            
        except Exception as e:
            current_app.logger.error(f"Failed to send notifications: {e}")
    
    def _send_email_notification(self, order: Order, action: WorkflowAction, user: User):
        """Send email notifications"""
        # Implementation for email notifications
        pass
    
    def _send_websocket_notification(self, order: Order, action: WorkflowAction, user: User):
        """Send WebSocket notifications"""
        # Implementation for WebSocket notifications
        pass
    
    def _update_workflow_metrics(self, order: Order, action: WorkflowAction):
        """Update workflow performance metrics"""
        # Implementation for metrics tracking
        pass
    
    def get_order_timeline(self, order_id: int) -> List[Dict]:
        """Get order timeline with all status changes"""
        order = Order.query.get(order_id)
        if not order:
            return []
        
        timeline = []
        
        # Order creation
        timeline.append({
            'timestamp': order.created_at,
            'status': OrderWorkflowState.NEW.value,
            'action': 'Order Created',
            'user': order.created_user.username if order.created_user else 'System',
            'description': f"Order {order.order_number} created"
        })
        
        # Add other status changes from audit logs
        for log in self.audit_logs:
            if log['order_id'] == order_id:
                timeline.append({
                    'timestamp': log['timestamp'],
                    'status': log['from_status'],
                    'action': log['action'],
                    'user': log['username'],
                    'description': f"Status changed via {log['action']}"
                })
        
        return sorted(timeline, key=lambda x: x['timestamp'])
    
    def get_workflow_statistics(self, date_range: Tuple[datetime, datetime] = None) -> Dict:
        """Get workflow performance statistics"""
        query = Order.query
        
        if date_range:
            start_date, end_date = date_range
            query = query.filter(Order.created_at >= start_date, Order.created_at <= end_date)
        
        orders = query.all()
        
        stats = {
            'total_orders': len(orders),
            'by_status': {},
            'average_completion_time': 0,
            'workflow_efficiency': {}
        }
        
        # Status distribution
        for order in orders:
            status = order.status
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
        
        # Calculate average completion time
        completed_orders = [o for o in orders if o.status == OrderWorkflowState.COMPLETED.value and o.completed_at]
        if completed_orders:
            total_time = sum([(o.completed_at - o.created_at).total_seconds() for o in completed_orders])
            stats['average_completion_time'] = total_time / len(completed_orders) / 60  # in minutes
        
        return stats


# Global workflow engine instance
order_workflow = OrderWorkflowEngine()