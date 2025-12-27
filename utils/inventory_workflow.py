"""
Advanced Inventory Workflow Engine for Restaurant POS System

This module provides comprehensive workflow management for inventory operations
with automated alerts, reordering, and supplier management.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from flask import current_app
from flask_login import current_user
from models import db, MenuItem, Order, OrderItem
from decimal import Decimal


class InventoryWorkflowState(Enum):
    """Inventory workflow states"""
    AVAILABLE = "Available"
    LOW_STOCK = "Low Stock"
    OUT_OF_STOCK = "Out of Stock"
    REORDER_PENDING = "Reorder Pending"
    REORDERED = "Reordered"
    RESTOCKED = "Restocked"


class InventoryAction(Enum):
    """Available inventory actions"""
    CHECK_STOCK = "check_stock"
    SET_LOW_STOCK_ALERT = "set_low_stock_alert"
    SET_OUT_OF_STOCK = "set_out_of_stock"
    REQUEST_REORDER = "request_reorder"
    PROCESS_REORDER = "process_reorder"
    UPDATE_STOCK = "update_stock"
    RESTOCK_ITEM = "restock_item"
    MARK_AVAILABLE = "mark_available"


class InventoryWorkflowEngine:
    """Core workflow engine for inventory management"""
    
    # Define stock level thresholds
    LOW_STOCK_THRESHOLD_MULTIPLIER = 1.0  # At or below min_stock_level
    CRITICAL_STOCK_THRESHOLD_MULTIPLIER = 0.5  # At or below 50% of min_stock_level
    
    # Define reorder quantities
    DEFAULT_REORDER_MULTIPLIER = 2.0  # Reorder 2x the min_stock_level
    
    # Notification triggers
    NOTIFICATION_THRESHOLDS = {
        'low_stock': 1.0,
        'critical_stock': 0.5,
        'out_of_stock': 0.0
    }
    
    def __init__(self):
        self.audit_logs = []
        self.alert_handlers = []
    
    def check_stock_levels(self, item_id: int = None) -> Dict:
        """
        Check stock levels and update workflow states
        
        Args:
            item_id: Specific item to check, or None for all items
            
        Returns:
            Dictionary with stock status information
        """
        try:
            if item_id:
                items = [MenuItem.query.get(item_id)]
            else:
                items = MenuItem.query.filter_by(is_active=True).all()
            
            stock_status = {
                'available': [],
                'low_stock': [],
                'out_of_stock': [],
                'critical': [],
                'alerts': []
            }
            
            for item in items:
                if not item:
                    continue
                
                current_stock = item.stock_quantity
                min_level = item.min_stock_level
                
                if current_stock <= 0:
                    status = InventoryWorkflowState.OUT_OF_STOCK
                    stock_status['out_of_stock'].append(item.to_dict())
                    
                elif current_stock <= min_level * self.CRITICAL_STOCK_THRESHOLD_MULTIPLIER:
                    status = InventoryWorkflowState.LOW_STOCK
                    stock_status['critical'].append(item.to_dict())
                    
                elif current_stock <= min_level:
                    status = InventoryWorkflowState.LOW_STOCK
                    stock_status['low_stock'].append(item.to_dict())
                    
                else:
                    status = InventoryWorkflowState.AVAILABLE
                    stock_status['available'].append(item.to_dict())
                
                # Generate alerts if needed
                if status != InventoryWorkflowState.AVAILABLE:
                    alert = self._generate_stock_alert(item, status, current_stock, min_level)
                    if alert:
                        stock_status['alerts'].append(alert)
            
            return stock_status
            
        except Exception as e:
            current_app.logger.error(f"Error checking stock levels: {e}")
            return {'error': str(e)}
    
    def process_inventory_action(self, user, item_id: int, action: InventoryAction, 
                               data: Dict = None) -> Tuple[bool, str, Dict]:
        """
        Process inventory workflow action
        
        Args:
            user: User performing the action
            item_id: ID of inventory item
            action: Action to perform
            data: Additional action data
            
        Returns:
            Tuple of (success, message, result_data)
        """
        try:
            item = MenuItem.query.get(item_id)
            if not item:
                return False, "Item not found", {}
            
            # Execute the action
            result = self._execute_inventory_action(user, item, action, data or {})
            
            # Log the action
            self._log_inventory_action(user, item, action, data or {}, result)
            
            # Check for automated actions
            self._check_automated_actions(item)
            
            # Send notifications
            self._send_inventory_notifications(item, action, user)
            
            db.session.commit()
            
            return True, f"Action {action.value} completed successfully", result
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error processing inventory action: {str(e)}", {}
    
    def request_reorder(self, item_id: int, quantity: int = None, urgency: str = 'normal') -> Dict:
        """
        Request reorder for an item
        
        Args:
            item_id: Item ID
            quantity: Quantity to reorder (defaults to calculated amount)
            urgency: Urgency level (low, normal, high, critical)
            
        Returns:
            Reorder request details
        """
        item = MenuItem.query.get(item_id)
        if not item:
            return {'success': False, 'message': 'Item not found'}
        
        # Calculate reorder quantity if not provided
        if quantity is None:
            quantity = int(item.min_stock_level * self.DEFAULT_REORDER_MULTIPLIER)
        
        # Create reorder request
        reorder_data = {
            'item_id': item.id,
            'item_name': item.name,
            'current_stock': item.stock_quantity,
            'min_stock_level': item.min_stock_level,
            'reorder_quantity': quantity,
            'urgency': urgency,
            'supplier_info': self._get_supplier_info(item),
            'estimated_cost': self._calculate_reorder_cost(item, quantity),
            'requested_at': datetime.utcnow(),
            'status': 'Pending'
        }
        
        # Update item state
        item.stock_state = InventoryWorkflowState.REORDER_PENDING.value
        
        # Log the reorder request
        self._log_reorder_request(reorder_data)
        
        return {
            'success': True,
            'reorder_request': reorder_data,
            'message': f'Reorder request created for {quantity} units of {item.name}'
        }
    
    def process_reorder(self, reorder_id: str, approved: bool, user, 
                       actual_quantity: int = None, supplier_data: Dict = None) -> Dict:
        """
        Process reorder approval/rejection
        
        Args:
            reorder_id: Reorder request ID
            approved: Whether reorder is approved
            user: User processing the reorder
            actual_quantity: Actual quantity received
            supplier_data: Supplier information
            
        Returns:
            Processing result
        """
        try:
            # Find reorder request (implement based on your storage mechanism)
            reorder_request = self._get_reorder_request(reorder_id)
            if not reorder_request:
                return {'success': False, 'message': 'Reorder request not found'}
            
            item = MenuItem.query.get(reorder_request['item_id'])
            if not item:
                return {'success': False, 'message': 'Item not found'}
            
            if approved:
                # Process approved reorder
                actual_qty = actual_quantity or reorder_request['reorder_quantity']
                
                # Update stock
                item.stock_quantity += actual_qty
                item.stock_state = InventoryWorkflowState.RESTOCKED.value
                item.updated_at = datetime.utcnow()
                
                # Log the restocking
                self._log_restocking(item, actual_qty, user, supplier_data)
                
                result = {
                    'success': True,
                    'action': 'approved',
                    'item_id': item.id,
                    'previous_stock': reorder_request['current_stock'],
                    'new_stock': item.stock_quantity,
                    'quantity_added': actual_qty,
                    'supplier_data': supplier_data
                }
            else:
                # Process rejected reorder
                item.stock_state = InventoryWorkflowState.LOW_STOCK.value
                
                result = {
                    'success': True,
                    'action': 'rejected',
                    'item_id': item.id,
                    'reason': 'Reorder rejected by user'
                }
            
            # Update reorder request status
            self._update_reorder_status(reorder_id, 'processed' if approved else 'rejected')
            
            db.session.commit()
            
            return result
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error processing reorder: {str(e)}'}
    
    def _execute_inventory_action(self, user, item: MenuItem, action: InventoryAction, data: Dict) -> Dict:
        """Execute specific inventory action"""
        result = {'item_id': item.id, 'action': action.value}
        
        if action == InventoryAction.CHECK_STOCK:
            result.update(self._check_single_item_stock(item))
            
        elif action == InventoryAction.SET_LOW_STOCK_ALERT:
            result.update(self._set_low_stock_alert(item, data))
            
        elif action == InventoryAction.SET_OUT_OF_STOCK:
            result.update(self._set_out_of_stock(item))
            
        elif action == InventoryAction.UPDATE_STOCK:
            result.update(self._update_stock(item, data))
            
        elif action == InventoryAction.RESTOCK_ITEM:
            result.update(self._restock_item(item, data, user))
            
        elif action == InventoryAction.MARK_AVAILABLE:
            result.update(self._mark_available(item))
        
        return result
    
    def _check_single_item_stock(self, item: MenuItem) -> Dict:
        """Check stock for single item"""
        current_stock = item.stock_quantity
        min_level = item.min_stock_level
        
        if current_stock <= 0:
            status = InventoryWorkflowState.OUT_OF_STOCK
        elif current_stock <= min_level:
            status = InventoryWorkflowState.LOW_STOCK
        else:
            status = InventoryWorkflowState.AVAILABLE
        
        return {
            'current_stock': current_stock,
            'min_stock_level': min_level,
            'status': status.value,
            'needs_reorder': current_stock <= min_level
        }
    
    def _set_low_stock_alert(self, item: MenuItem, data: Dict) -> Dict:
        """Set low stock alert"""
        alert_level = data.get('alert_level', item.min_stock_level)
        item.min_stock_level = alert_level
        item.updated_at = datetime.utcnow()
        
        return {
            'previous_min_level': item.min_stock_level,
            'new_min_level': alert_level,
            'alert_set': True
        }
    
    def _set_out_of_stock(self, item: MenuItem) -> Dict:
        """Set item as out of stock"""
        item.stock_quantity = 0
        item.is_available = False
        item.stock_state = InventoryWorkflowState.OUT_OF_STOCK.value
        item.updated_at = datetime.utcnow()
        
        return {
            'previous_stock': item.stock_quantity,
            'new_stock': 0,
            'available': False,
            'status': InventoryWorkflowState.OUT_OF_STOCK.value
        }
    
    def _update_stock(self, item: MenuItem, data: Dict) -> Dict:
        """Update stock quantity"""
        new_quantity = data.get('quantity', 0)
        reason = data.get('reason', 'Manual update')
        
        old_quantity = item.stock_quantity
        item.stock_quantity = max(0, new_quantity)
        item.updated_at = datetime.utcnow()
        
        # Update availability
        item.is_available = item.stock_quantity > 0
        
        return {
            'previous_stock': old_quantity,
            'new_stock': item.stock_quantity,
            'change': item.stock_quantity - old_quantity,
            'reason': reason,
            'available': item.is_available
        }
    
    def _restock_item(self, item: MenuItem, data: Dict, user) -> Dict:
        """Restock an item"""
        quantity = data.get('quantity', 0)
        supplier_info = data.get('supplier_info', {})
        cost = data.get('cost', 0)
        
        old_quantity = item.stock_quantity
        item.stock_quantity += quantity
        item.is_available = True
        item.stock_state = InventoryWorkflowState.RESTOCKED.value
        item.updated_at = datetime.utcnow()
        
        # Log restocking
        self._log_restocking(item, quantity, user, supplier_info, cost)
        
        return {
            'previous_stock': old_quantity,
            'new_stock': item.stock_quantity,
            'quantity_added': quantity,
            'supplier_info': supplier_info,
            'cost': cost,
            'available': True
        }
    
    def _mark_available(self, item: MenuItem) -> Dict:
        """Mark item as available"""
        item.is_available = True
        item.stock_state = InventoryWorkflowState.AVAILABLE.value
        item.updated_at = datetime.utcnow()
        
        return {
            'available': True,
            'status': InventoryWorkflowState.AVAILABLE.value
        }
    
    def _check_automated_actions(self, item: MenuItem):
        """Check for automated actions based on stock levels"""
        current_stock = item.stock_quantity
        min_level = item.min_stock_level
        
        if current_stock <= 0 and item.stock_state != InventoryWorkflowState.OUT_OF_STOCK.value:
            # Auto-set to out of stock
            item.stock_state = InventoryWorkflowState.OUT_OF_STOCK.value
            item.is_available = False
            
        elif current_stock <= min_level and item.stock_state == InventoryWorkflowState.AVAILABLE.value:
            # Auto-set to low stock and request reorder
            item.stock_state = InventoryWorkflowState.LOW_STOCK.value
            
            # Auto-request reorder for critical items
            if current_stock <= min_level * self.CRITICAL_STOCK_THRESHOLD_MULTIPLIER:
                self._auto_request_reorder(item)
    
    def _auto_request_reorder(self, item: MenuItem):
        """Automatically request reorder for critical items"""
        reorder_data = {
            'item_id': item.id,
            'item_name': item.name,
            'current_stock': item.stock_quantity,
            'min_stock_level': item.min_stock_level,
            'reorder_quantity': int(item.min_stock_level * self.DEFAULT_REORDER_MULTIPLIER),
            'urgency': 'high',
            'auto_generated': True,
            'requested_at': datetime.utcnow()
        }
        
        item.stock_state = InventoryWorkflowState.REORDER_PENDING.value
        
        self._log_auto_reorder_request(reorder_data)
    
    def _get_supplier_info(self, item: MenuItem) -> Dict:
        """Get supplier information for item"""
        # This would be implemented based on your supplier management system
        return {
            'primary_supplier': 'Default Supplier',
            'contact_info': 'supplier@example.com',
            'lead_time_days': 3,
            'last_order_date': None
        }
    
    def _calculate_reorder_cost(self, item: MenuItem, quantity: int) -> float:
        """Calculate estimated reorder cost"""
        # This would use actual supplier pricing
        estimated_unit_cost = float(item.price) * 0.6  # Assume 60% of selling price
        return estimated_unit_cost * quantity
    
    def _generate_stock_alert(self, item: MenuItem, status: InventoryWorkflowState, 
                            current_stock: int, min_level: int) -> Dict:
        """Generate stock alert"""
        return {
            'item_id': item.id,
            'item_name': item.name,
            'current_stock': current_stock,
            'min_stock_level': min_level,
            'status': status.value,
            'alert_level': self._get_alert_level(current_stock, min_level),
            'timestamp': datetime.utcnow(),
            'requires_action': status != InventoryWorkflowState.AVAILABLE
        }
    
    def _get_alert_level(self, current_stock: int, min_level: int) -> str:
        """Get alert level based on stock"""
        if current_stock <= 0:
            return 'critical'
        elif current_stock <= min_level * self.CRITICAL_STOCK_THRESHOLD_MULTIPLIER:
            return 'high'
        elif current_stock <= min_level:
            return 'medium'
        else:
            return 'low'
    
    def _log_inventory_action(self, user, item: MenuItem, action: InventoryAction, 
                            data: Dict, result: Dict):
        """Log inventory action for audit trail"""
        log_entry = {
            'timestamp': datetime.utcnow(),
            'user_id': user.id if user else None,
            'username': user.username if user else 'System',
            'item_id': item.id,
            'item_name': item.name,
            'action': action.value,
            'data': data,
            'result': result
        }
        self.audit_logs.append(log_entry)
    
    def _log_reorder_request(self, reorder_data: Dict):
        """Log reorder request"""
        # Implementation depends on storage mechanism
        pass
    
    def _log_restocking(self, item: MenuItem, quantity: int, user, 
                       supplier_info: Dict = None, cost: float = None):
        """Log restocking event"""
        log_entry = {
            'timestamp': datetime.utcnow(),
            'user_id': user.id if user else None,
            'item_id': item.id,
            'item_name': item.name,
            'quantity_added': quantity,
            'supplier_info': supplier_info,
            'cost': cost,
            'action': 'restocking'
        }
        self.audit_logs.append(log_entry)
    
    def _log_auto_reorder_request(self, reorder_data: Dict):
        """Log automatically generated reorder request"""
        # Implementation depends on storage mechanism
        pass
    
    def _get_reorder_request(self, reorder_id: str) -> Dict:
        """Get reorder request by ID"""
        # Implementation depends on storage mechanism
        return {}
    
    def _update_reorder_status(self, reorder_id: str, status: str):
        """Update reorder request status"""
        # Implementation depends on storage mechanism
        pass
    
    def _send_inventory_notifications(self, item: MenuItem, action: InventoryAction, user):
        """Send notifications for inventory actions"""
        try:
            # WebSocket notifications for real-time updates
            self._send_websocket_notification(item, action, user)
            
            # Email notifications for critical alerts
            if self._is_critical_alert(item):
                self._send_critical_alert_email(item, action, user)
                
        except Exception as e:
            current_app.logger.error(f"Failed to send inventory notifications: {e}")
    
    def _send_websocket_notification(self, item: MenuItem, action: InventoryAction, user):
        """Send WebSocket notification"""
        # Implementation for WebSocket notifications
        pass
    
    def _send_critical_alert_email(self, item: MenuItem, action: InventoryAction, user):
        """Send critical alert email"""
        # Implementation for email notifications
        pass
    
    def _is_critical_alert(self, item: MenuItem) -> bool:
        """Check if item requires critical alert"""
        return (item.stock_quantity <= item.min_stock_level * self.CRITICAL_STOCK_THRESHOLD_MULTIPLIER or 
                item.stock_quantity == 0)
    
    def get_inventory_workflow_statistics(self, date_range: Tuple[datetime, datetime] = None) -> Dict:
        """Get inventory workflow statistics"""
        query = MenuItem.query.filter_by(is_active=True)
        
        if date_range:
            start_date, end_date = date_range
            query = query.filter(MenuItem.updated_at >= start_date, MenuItem.updated_at <= end_date)
        
        items = query.all()
        
        stats = {
            'total_items': len(items),
            'by_stock_status': {},
            'low_stock_count': 0,
            'out_of_stock_count': 0,
            'reorder_requests': 0,
            'restock_events': 0
        }
        
        for item in items:
            # Stock status distribution
            if item.stock_quantity <= 0:
                status = 'out_of_stock'
                stats['out_of_stock_count'] += 1
            elif item.stock_quantity <= item.min_stock_level:
                status = 'low_stock'
                stats['low_stock_count'] += 1
            else:
                status = 'available'
            
            stats['by_stock_status'][status] = stats['by_stock_status'].get(status, 0) + 1
        
        return stats


# Global inventory workflow engine instance
inventory_workflow = InventoryWorkflowEngine()