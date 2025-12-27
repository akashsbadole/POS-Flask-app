"""
Payment Integration for Order Modifications
Handles refunds and additional charges for order modifications
"""

from decimal import Decimal
from datetime import datetime
from sqlalchemy import and_, or_
from models import db
from models.order import Order, OrderItem
from models.payment import Payment, PaymentTransaction
from models.order_modification import OrderModification
from utils.payment_gateways.processor import get_payment_processor
from utils.payment_gateways.exceptions import PaymentGatewayError, PaymentValidationError
import logging

logger = logging.getLogger(__name__)


class ModificationPaymentManager:
    """Manages payment processing for order modifications"""
    
    def __init__(self):
        self.payment_processor = get_payment_processor()
    
    def process_modification_payment(self, modification, payment_method='manual', processed_by=None):
        """Process payment for modification (additional charges or refunds)"""
        try:
            # Get order and original payment
            order = modification.order
            if not order:
                raise PaymentValidationError("Order not found")
            
            original_payment = Payment.query.filter_by(order_id=order.id, status='completed').first()
            if not original_payment:
                raise PaymentValidationError("Original payment not found")
            
            price_difference = modification.price_difference
            
            # Handle different scenarios
            if price_difference > 0:
                # Additional charge required
                return self._process_additional_charge(modification, original_payment, price_difference, payment_method, processed_by)
            elif price_difference < 0:
                # Refund required
                return self._process_refund(modification, original_payment, abs(price_difference), processed_by)
            else:
                # No payment required
                return {
                    'success': True,
                    'message': 'No payment required - no price difference',
                    'action': 'no_action',
                    'amount': 0
                }
                
        except Exception as e:
            logger.error(f"Error processing modification payment: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action': 'error'
            }
    
    def _process_additional_charge(self, modification, original_payment, amount, payment_method, processed_by):
        """Process additional charge for modification"""
        try:
            # Create new payment record for additional charge
            additional_payment = Payment(
                order_id=original_payment.order_id,
                amount=Decimal(str(amount)),
                payment_method_type=payment_method,
                status='pending',
                gateway_id=original_payment.gateway_id,
                created_by=processed_by
            )
            
            db.session.add(additional_payment)
            db.session.flush()  # Get the ID
            
            # Create transaction record
            transaction = PaymentTransaction(
                payment_id=additional_payment.id,
                gateway_id=original_payment.gateway_id,
                transaction_type='modification_charge',
                amount=Decimal(str(amount)),
                status='initiated',
                gateway_transaction_id=f"MOD_{modification.modification_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                modification_id=modification.id
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            # Update modification record
            modification.refund_amount = Decimal('0')
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Additional charge initiated',
                'action': 'additional_charge',
                'payment_id': additional_payment.id,
                'transaction_id': transaction.id,
                'amount': float(amount),
                'payment_method': payment_method
            }
            
        except Exception as e:
            db.session.rollback()
            raise PaymentGatewayError(f"Failed to process additional charge: {str(e)}")
    
    def _process_refund(self, modification, original_payment, refund_amount, processed_by):
        """Process refund for modification"""
        try:
            # Validate refund amount
            if refund_amount > original_payment.amount:
                raise PaymentValidationError("Refund amount cannot exceed original payment")
            
            # Check if refund is already processed
            existing_refund = PaymentTransaction.query.filter_by(
                modification_id=modification.id,
                transaction_type='refund',
                status='completed'
            ).first()
            
            if existing_refund:
                return {
                    'success': True,
                    'message': 'Refund already processed',
                    'action': 'refund_already_processed',
                    'refund_id': existing_refund.id,
                    'amount': float(existing_refund.amount)
                }
            
            # Create refund transaction
            refund_transaction = PaymentTransaction(
                payment_id=original_payment.id,
                gateway_id=original_payment.gateway_id,
                transaction_type='refund',
                amount=Decimal(str(refund_amount)) * -1,  # Negative for refund
                status='initiated',
                gateway_transaction_id=f"REF_{modification.modification_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                modification_id=modification.id,
                refund_reason=f"Order modification: {modification.modification_type}",
                processed_by=processed_by
            )
            
            db.session.add(refund_transaction)
            db.session.flush()
            
            # Process refund through payment gateway
            try:
                refund_result = self.payment_processor.refund_payment(
                    payment_id=original_payment.id,
                    amount=Decimal(str(refund_amount)),
                    reason=f"Order modification {modification.modification_id}: {modification.reason or 'Customer request'}",
                    refund_transaction_id=refund_transaction.id
                )
                
                # Update transaction status
                if refund_result.get('success'):
                    refund_transaction.status = 'completed'
                    refund_transaction.gateway_refund_id = refund_result.get('gateway_refund_id')
                    refund_transaction.completed_at = datetime.utcnow()
                    
                    # Update modification record
                    modification.refund_amount = Decimal(str(refund_amount))
                    
                    # Create audit log
                    self._create_refund_audit_log(modification, refund_transaction, 'completed')
                    
                else:
                    refund_transaction.status = 'failed'
                    refund_transaction.failure_reason = refund_result.get('error_message', 'Unknown error')
                    
                    # Create audit log for failure
                    self._create_refund_audit_log(modification, refund_transaction, 'failed')
                
                db.session.commit()
                
                return {
                    'success': refund_result.get('success', False),
                    'message': refund_result.get('error_message', 'Refund processed successfully') if not refund_result.get('success') else 'Refund processed successfully',
                    'action': 'refund',
                    'refund_id': refund_transaction.id,
                    'amount': float(refund_amount),
                    'gateway_refund_id': refund_result.get('gateway_refund_id'),
                    'refund_status': refund_transaction.status
                }
                
            except Exception as gateway_error:
                # Gateway refund failed
                refund_transaction.status = 'failed'
                refund_transaction.failure_reason = str(gateway_error)
                db.session.commit()
                
                # Create audit log for failure
                self._create_refund_audit_log(modification, refund_transaction, 'gateway_failed')
                
                raise PaymentGatewayError(f"Gateway refund failed: {str(gateway_error)}")
                
        except Exception as e:
            db.session.rollback()
            raise PaymentGatewayError(f"Failed to process refund: {str(e)}")
    
    def cancel_modification_payment(self, modification, cancelled_by, reason):
        """Cancel payment for modification"""
        try:
            # Find pending payment transactions for this modification
            pending_transactions = PaymentTransaction.query.filter_by(
                modification_id=modification.id,
                transaction_type='modification_charge',
                status='initiated'
            ).all()
            
            cancelled_transactions = []
            
            for transaction in pending_transactions:
                # Update transaction status
                transaction.status = 'cancelled'
                transaction.cancelled_at = datetime.utcnow()
                transaction.cancellation_reason = reason
                transaction.cancelled_by = cancelled_by
                
                cancelled_transactions.append(transaction.id)
                
                # Create audit log
                self._create_cancellation_audit_log(modification, transaction, cancelled_by, reason)
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Cancelled {len(cancelled_transactions)} pending transactions',
                'cancelled_transactions': cancelled_transactions
            }
            
        except Exception as e:
            db.session.rollback()
            raise PaymentGatewayError(f"Failed to cancel modification payment: {str(e)}")
    
    def get_modification_payment_summary(self, modification):
        """Get payment summary for a modification"""
        try:
            transactions = PaymentTransaction.query.filter_by(modification_id=modification.id).all()
            
            summary = {
                'modification_id': modification.id,
                'total_additional_charges': 0,
                'total_refunds': 0,
                'net_amount': float(modification.price_difference),
                'transactions': []
            }
            
            for transaction in transactions:
                transaction_data = {
                    'id': transaction.id,
                    'type': transaction.transaction_type,
                    'amount': float(transaction.amount),
                    'status': transaction.status,
                    'created_at': transaction.created_at.isoformat(),
                    'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None,
                    'gateway_transaction_id': transaction.gateway_transaction_id,
                    'gateway_refund_id': transaction.gateway_refund_id,
                    'failure_reason': transaction.failure_reason
                }
                
                summary['transactions'].append(transaction_data)
                
                # Calculate totals
                if transaction.transaction_type == 'modification_charge' and transaction.status == 'completed':
                    summary['total_additional_charges'] += float(transaction.amount)
                elif transaction.transaction_type == 'refund' and transaction.status == 'completed':
                    summary['total_refunds'] += abs(float(transaction.amount))
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting modification payment summary: {str(e)}")
            return None
    
    def validate_refund_eligibility(self, modification):
        """Validate if modification is eligible for refund"""
        try:
            # Get original payment
            original_payment = Payment.query.filter_by(
                order_id=modification.order_id,
                status='completed'
            ).first()
            
            if not original_payment:
                return False, "No completed payment found for this order"
            
            # Check refund amount doesn't exceed original payment
            refund_amount = abs(modification.price_difference)
            if refund_amount > original_payment.amount:
                return False, "Refund amount exceeds original payment"
            
            # Check if modification has already been fully refunded
            existing_refunds = PaymentTransaction.query.filter_by(
                modification_id=modification.id,
                transaction_type='refund',
                status='completed'
            ).all()
            
            total_refunded = sum(abs(float(t.amount)) for t in existing_refunds)
            
            if total_refunded >= refund_amount:
                return False, "Modification has already been fully refunded"
            
            return True, "Eligible for refund"
            
        except Exception as e:
            logger.error(f"Error validating refund eligibility: {str(e)}")
            return False, f"Error validating refund eligibility: {str(e)}"
    
    def _create_refund_audit_log(self, modification, transaction, status):
        """Create audit log for refund processing"""
        try:
            audit_data = {
                'modification_id': modification.id,
                'transaction_id': transaction.id,
                'refund_amount': float(abs(transaction.amount)),
                'status': status,
                'gateway_transaction_id': transaction.gateway_transaction_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Log to file (in production, you might want to use a proper audit system)
            logger.info(f"Refund audit: {audit_data}")
            
        except Exception as e:
            logger.error(f"Error creating refund audit log: {str(e)}")
    
    def _create_cancellation_audit_log(self, modification, transaction, cancelled_by, reason):
        """Create audit log for payment cancellation"""
        try:
            audit_data = {
                'modification_id': modification.id,
                'transaction_id': transaction.id,
                'cancelled_by': cancelled_by,
                'cancelled_at': datetime.utcnow().isoformat(),
                'reason': reason
            }
            
            # Log to file
            logger.info(f"Payment cancellation audit: {audit_data}")
            
        except Exception as e:
            logger.error(f"Error creating cancellation audit log: {str(e)}")
    
    def get_pending_modification_payments(self, order_id=None):
        """Get pending payments for modifications"""
        try:
            query = PaymentTransaction.query.filter(
                and_(
                    PaymentTransaction.transaction_type.in_(['modification_charge', 'refund']),
                    PaymentTransaction.status == 'initiated'
                )
            )
            
            if order_id:
                query = query.join(Payment).filter(Payment.order_id == order_id)
            
            transactions = query.order_by(PaymentTransaction.created_at.desc()).all()
            
            pending_payments = []
            for transaction in transactions:
                payment_data = {
                    'id': transaction.id,
                    'modification_id': transaction.modification_id,
                    'order_id': transaction.payment.order_id,
                    'order_number': transaction.payment.order.order_number,
                    'transaction_type': transaction.transaction_type,
                    'amount': float(abs(transaction.amount)),
                    'status': transaction.status,
                    'created_at': transaction.created_at.isoformat(),
                    'gateway_transaction_id': transaction.gateway_transaction_id
                }
                
                if transaction.modification:
                    payment_data['modification_type'] = transaction.modification.modification_type
                    payment_data['requested_by'] = transaction.modification.requested_by.username if transaction.modification.requested_by else 'Unknown'
                
                pending_payments.append(payment_data)
            
            return pending_payments
            
        except Exception as e:
            logger.error(f"Error getting pending modification payments: {str(e)}")
            return []


# Global instance
modification_payment_manager = ModificationPaymentManager()


def process_modification_payment(modification, payment_method='manual', processed_by=None):
    """Helper function to process modification payment"""
    return modification_payment_manager.process_modification_payment(
        modification, payment_method, processed_by
    )


def validate_modification_refund(modification):
    """Helper function to validate refund eligibility"""
    return modification_payment_manager.validate_refund_eligibility(modification)


def get_modification_payment_summary(modification):
    """Helper function to get payment summary"""
    return modification_payment_manager.get_modification_payment_summary(modification)


def get_pending_modification_payments(order_id=None):
    """Helper function to get pending payments"""
    return modification_payment_manager.get_pending_modification_payments(order_id)