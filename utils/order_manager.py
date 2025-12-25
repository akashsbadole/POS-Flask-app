"""
Advanced Order Management Utilities for Flask POS Application
Handles order merging, splitting, and transferring operations
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from flask import current_app
from models import db, Order, OrderItem, Table, Payment
from decimal import Decimal

class OrderManager:
    """Advanced order operations manager"""
    
    @staticmethod
    def merge_orders(source_order_ids: List[int], target_order_id: int) -> Dict[str, Any]:
        """
        Merge multiple orders into a single order
        
        Args:
            source_order_ids: List of order IDs to merge
            target_order_id: Target order ID to merge into
            
        Returns:
            Dict with operation result
        """
        try:
            # Validate orders
            target_order = Order.query.get(target_order_id)
            if not target_order:
                return {'success': False, 'message': 'Target order not found'}
            
            if target_order.payment_status == 'Paid':
                return {'success': False, 'message': 'Cannot merge into paid order'}
            
            source_orders = Order.query.filter(Order.id.in_(source_order_ids)).all()
            if not source_orders:
                return {'success': False, 'message': 'Source orders not found'}
            
            # Check if all source orders are unpaid
            for order in source_orders:
                if order.payment_status == 'Paid':
                    return {'success': False, 'message': f'Cannot merge paid order {order.order_number}'}
            
            # Merge order items
            merged_items = []
            total_merged_amount = Decimal('0.00')
            
            for source_order in source_orders:
                for item in source_order.items:
                    # Check if item already exists in target order
                    existing_item = next(
                        (mi for mi in target_order.items if mi.menu_item_id == item.menu_item_id),
                        None
                    )
                    
                    if existing_item:
                        # Update quantity
                        existing_item.quantity += item.quantity
                        existing_item.total += item.total
                    else:
                        # Add new item to target order
                        new_item = OrderItem(
                            order_id=target_order.id,
                            menu_item_id=item.menu_item_id,
                            quantity=item.quantity,
                            price=item.price,
                            total=item.total,
                            notes=item.notes
                        )
                        merged_items.append(new_item)
                        db.session.add(new_item)
                    
                    total_merged_amount += item.total
            
            # Update target order totals
            target_order.subtotal += total_merged_amount
            target_order.cgst += total_merged_amount * Decimal('0.025')
            target_order.sgst += total_merged_amount * Decimal('0.025')
            target_order.grand_total += total_merged_amount * Decimal('1.05')
            
            # Mark source orders as merged
            for source_order in source_orders:
                source_order.status = 'Merged'
                source_order.merged_into_order_id = target_order.id
                source_order.merged_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Successfully merged {len(source_orders)} orders',
                'merged_order_id': target_order.id,
                'merged_amount': float(total_merged_amount),
                'target_order_number': target_order.order_number
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error merging orders: {str(e)}")
            return {'success': False, 'message': f'Error merging orders: {str(e)}'}
    
    @staticmethod
    def split_order(order_id: int, split_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Split an order into multiple orders
        
        Args:
            order_id: Original order ID to split
            split_items: List of splits with items and percentages
            
        Returns:
            Dict with operation result
        """
        try:
            original_order = Order.query.get(order_id)
            if not original_order:
                return {'success': False, 'message': 'Order not found'}
            
            if original_order.payment_status == 'Paid':
                return {'success': False, 'message': 'Cannot split paid order'}
            
            new_orders = []
            
            for i, split_data in enumerate(split_items):
                # Create new order
                new_order = Order(
                    order_number=f"{original_order.order_number}-S{i+1}",
                    order_type=original_order.order_type,
                    customer_name=f"{original_order.customer_name} (Split {i+1})",
                    customer_mobile=original_order.customer_mobile,
                    table_id=original_order.table_id,
                    status='Active',
                    payment_status='Pending'
                )
                db.session.add(new_order)
                db.session.flush()  # Get ID for new order
                
                # Add items to new order
                split_subtotal = Decimal('0.00')
                
                for item_info in split_data.get('items', []):
                    item_id = item_info.get('item_id')
                    quantity = item_info.get('quantity', 0)
                    
                    if quantity <= 0:
                        continue
                    
                    # Find original item
                    original_item = next(
                        (oi for oi in original_order.items if oi.id == item_id),
                        None
                    )
                    
                    if not original_item:
                        continue
                    
                    # Create new order item
                    new_item = OrderItem(
                        order_id=new_order.id,
                        menu_item_id=original_item.menu_item_id,
                        quantity=quantity,
                        price=original_item.price,
                        total=original_item.price * Decimal(str(quantity)),
                        notes=original_item.notes
                    )
                    db.session.add(new_item)
                    split_subtotal += new_item.total
                
                # Calculate totals for new order
                new_order.subtotal = split_subtotal
                new_order.cgst = split_subtotal * Decimal('0.025')
                new_order.sgst = split_subtotal * Decimal('0.025')
                new_order.grand_total = split_subtotal * Decimal('1.05')
                
                new_orders.append(new_order)
            
            # Mark original order as split
            original_order.status = 'Split'
            original_order.split_from_order_id = original_order.id
            original_order.split_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Successfully split order into {len(new_orders)} orders',
                'new_orders': [
                    {
                        'id': order.id,
                        'order_number': order.order_number,
                        'subtotal': float(order.subtotal),
                        'grand_total': float(order.grand_total)
                    }
                    for order in new_orders
                ]
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error splitting order: {str(e)}")
            return {'success': False, 'message': f'Error splitting order: {str(e)}'}
    
    @staticmethod
    def transfer_order(order_id: int, from_table_id: int, to_table_id: int) -> Dict[str, Any]:
        """
        Transfer an order from one table to another
        
        Args:
            order_id: Order ID to transfer
            from_table_id: Current table ID
            to_table_id: Target table ID
            
        Returns:
            Dict with operation result
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            from_table = Table.query.get(from_table_id)
            to_table = Table.query.get(to_table_id)
            
            if not from_table or not to_table:
                return {'success': False, 'message': 'Table not found'}
            
            if order.table_id != from_table_id:
                return {'success': False, 'message': 'Order is not on the specified table'}
            
            if order.payment_status == 'Paid':
                return {'success': False, 'message': 'Cannot transfer paid order'}
            
            # Check if target table is available
            if to_table.status != 'Available':
                return {'success': False, 'message': 'Target table is not available'}
            
            # Update order table
            old_table_name = from_table.table_number
            new_table_name = to_table.table_number
            
            order.table_id = to_table_id
            order.transferred_from_table = from_table_id
            order.transferred_at = datetime.utcnow()
            
            # Update table statuses
            from_table.status = 'Available'
            to_table.status = 'Occupied'
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Order {order.order_number} transferred from {old_table_name} to {new_table_name}',
                'order_number': order.order_number,
                'from_table': old_table_name,
                'to_table': new_table_name
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error transferring order: {str(e)}")
            return {'success': False, 'message': f'Error transferring order: {str(e)}'}
    
    @staticmethod
    def split_payment(order_id: int, payment_splits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Split payment for an order among multiple payment methods
        
        Args:
            order_id: Order ID
            payment_splits: List of payment methods and amounts
            
        Returns:
            Dict with operation result
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            total_split_amount = sum(Decimal(str(split.get('amount', 0))) for split in payment_splits)
            
            if total_split_amount != order.grand_total:
                return {
                    'success': False,
                    'message': f'Split amounts ({total_split_amount}) do not match order total ({order.grand_total})'
                }
            
            # Create payment records for each split
            payments = []
            for split in payment_splits:
                payment = Payment(
                    order_id=order_id,
                    payment_method=split.get('method'),
                    amount=Decimal(str(split.get('amount', 0))),
                    transaction_id=split.get('transaction_id'),
                    notes=split.get('notes', '')
                )
                db.session.add(payment)
                payments.append(payment)
            
            # Update order status
            order.payment_status = 'Paid'
            order.paid_at = datetime.utcnow()
            
            # Update table status if dine-in
            if order.order_type == 'Dine-in' and order.table:
                order.table.status = 'Available'
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Payment split successfully processed for order {order.order_number}',
                'payments': [
                    {
                        'method': payment.payment_method,
                        'amount': float(payment.amount),
                        'transaction_id': payment.transaction_id
                    }
                    for payment in payments
                ]
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error splitting payment: {str(e)}")
            return {'success': False, 'message': f'Error processing payment split: {str(e)}'}
    
    @staticmethod
    def get_mergeable_orders(table_id: int = None) -> List[Dict[str, Any]]:
        """
        Get orders that can be merged (unpaid orders on same table or all tables)
        
        Args:
            table_id: Optional table ID to filter by
            
        Returns:
            List of mergeable orders
        """
        try:
            query = Order.query.filter(
                Order.payment_status == 'Pending',
                Order.status.in_(['Active', 'New'])
            )
            
            if table_id:
                query = query.filter(Order.table_id == table_id)
            
            orders = query.order_by(Order.created_at.desc()).all()
            
            return [
                {
                    'id': order.id,
                    'order_number': order.order_number,
                    'customer_name': order.customer_name,
                    'table_name': order.table.table_number if order.table else 'N/A',
                    'subtotal': float(order.subtotal),
                    'grand_total': float(order.grand_total),
                    'items_count': len(order.items),
                    'created_at': order.created_at.isoformat() if order.created_at else None
                }
                for order in orders
            ]
            
        except Exception as e:
            current_app.logger.error(f"Error getting mergeable orders: {str(e)}")
            return []
    
    @staticmethod
    def get_order_items_for_split(order_id: int) -> List[Dict[str, Any]]:
        """
        Get order items formatted for splitting
        
        Args:
            order_id: Order ID
            
        Returns:
            List of order items with split info
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return []
            
            return [
                {
                    'id': item.id,
                    'name': item.menu_item.name if item.menu_item else 'Unknown',
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'total': float(item.total),
                    'remaining_quantity': item.quantity
                }
                for item in order.items
            ]
            
        except Exception as e:
            current_app.logger.error(f"Error getting order items for split: {str(e)}")
            return []
    
    @staticmethod
    def validate_split_items(split_items: List[Dict[str, Any]], original_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate split items against original order items
        
        Args:
            split_items: Proposed split items
            original_items: Original order items
            
        Returns:
            Dict with validation result
        """
        try:
            # Create mapping of original items
            original_map = {item['id']: item['quantity'] for item in original_items}
            
            # Check split quantities
            split_quantities = {}
            for split_group in split_items:
                for item in split_group.get('items', []):
                    item_id = item.get('item_id')
                    quantity = item.get('quantity', 0)
                    
                    if item_id not in split_quantities:
                        split_quantities[item_id] = 0
                    split_quantities[item_id] += quantity
            
            # Validate totals
            for item_id, original_qty in original_map.items():
                split_qty = split_quantities.get(item_id, 0)
                
                if split_qty > original_qty:
                    return {
                        'valid': False,
                        'message': f'Split quantity ({split_qty}) exceeds original quantity ({original_qty}) for item {item_id}'
                    }
            
            total_split_qty = sum(split_quantities.values())
            total_original_qty = sum(original_map.values())
            
            if total_split_qty != total_original_qty:
                return {
                    'valid': False,
                    'message': f'Total split quantity ({total_split_qty}) does not match original quantity ({total_original_qty})'
                }
            
            return {'valid': True, 'message': 'Split validation successful'}
            
        except Exception as e:
            return {'valid': False, 'message': f'Validation error: {str(e)}'}
    
    @staticmethod
    def cancel_order(order_id: int, reason: str = '') -> Dict[str, Any]:
        """
        Cancel an order with reason
        
        Args:
            order_id: Order ID to cancel
            reason: Cancellation reason
            
        Returns:
            Dict with operation result
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            if order.payment_status == 'Paid':
                return {'success': False, 'message': 'Cannot cancel paid order'}
            
            order.status = 'Cancelled'
            order.cancellation_reason = reason
            order.cancelled_at = datetime.utcnow()
            
            # Update table status if dine-in
            if order.order_type == 'Dine-in' and order.table:
                order.table.status = 'Available'
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Order {order.order_number} cancelled successfully',
                'order_number': order.order_number
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error cancelling order: {str(e)}")
            return {'success': False, 'message': f'Error cancelling order: {str(e)}'}
    
    @staticmethod
    def get_order_history(order_id: int) -> List[Dict[str, Any]]:
        """
        Get order history including modifications
        
        Args:
            order_id: Order ID
            
        Returns:
            List of order history events
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return []
            
            history = []
            
            # Original creation
            history.append({
                'event': 'Order Created',
                'timestamp': order.created_at.isoformat() if order.created_at else None,
                'details': f'Order {order.order_number} created with {len(order.items)} items'
            })
            
            # Transfers
            if order.transferred_at:
                from_table = Table.query.get(order.transferred_from_table) if order.transferred_from_table else None
                history.append({
                    'event': 'Order Transferred',
                    'timestamp': order.transferred_at.isoformat(),
                    'details': f'Transferred from {from_table.table_number if from_table else "Unknown"} to {order.table.table_number if order.table else "Unknown"}'
                })
            
            # Splits
            if order.split_at:
                history.append({
                    'event': 'Order Split',
                    'timestamp': order.split_at.isoformat(),
                    'details': f'Order split into multiple orders'
                })
            
            # Merges
            if order.merged_at:
                target_order = Order.query.get(order.merged_into_order_id) if order.merged_into_order_id else None
                history.append({
                    'event': 'Order Merged',
                    'timestamp': order.merged_at.isoformat(),
                    'details': f'Merged into order {target_order.order_number if target_order else "Unknown"}'
                })
            
            # Cancellations
            if order.cancelled_at:
                history.append({
                    'event': 'Order Cancelled',
                    'timestamp': order.cancelled_at.isoformat(),
                    'details': f'Cancelled: {order.cancellation_reason or "No reason provided"}'
                })
            
            # Payment
            if order.paid_at:
                history.append({
                    'event': 'Order Paid',
                    'timestamp': order.paid_at.isoformat(),
                    'details': f'Paid {order.grand_total} via multiple payment methods'
                })
            
            return sorted(history, key=lambda x: x['timestamp'] or '', reverse=True)
            
        except Exception as e:
            current_app.logger.error(f"Error getting order history: {str(e)}")
            return []

# Global order manager instance
order_manager = OrderManager()
