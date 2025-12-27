import json
from datetime import datetime, timedelta
from decimal import Decimal
from flask import current_app
from models.payment_gateway import PaymentGateway, PaymentTransaction
from models.payment import Payment
from models.order import Order
from .razorpay import RazorpayGateway
from .stripe import StripeGateway
from .exceptions import (
    PaymentGatewayError, PaymentProcessingError, PaymentValidationError,
    WebhookVerificationError, GatewayConfigurationError
)

class PaymentProcessor:
    """Unified Payment Processor for Multiple Gateways"""
    
    def __init__(self):
        """Initialize payment processor"""
        self.gateways = {}
        self._loaded = False
    
    def _load_gateways(self):
        """Load all configured payment gateways"""
        if self._loaded:
            return
        
        try:
            gateways = PaymentGateway.get_enabled_gateways()
            for gateway in gateways:
                try:
                    self.gateways[gateway.name] = self._initialize_gateway(gateway)
                except Exception as e:
                    print(f"Failed to initialize gateway {gateway.name}: {str(e)}")
            self._loaded = True
        except Exception as e:
            print(f"Failed to load payment gateways: {str(e)}")
    
    def _initialize_gateway(self, gateway_config):
        """Initialize specific gateway instance"""
        if gateway_config.name == 'razorpay':
            return RazorpayGateway(gateway_config)
        elif gateway_config.name == 'stripe':
            return StripeGateway(gateway_config)
        else:
            raise GatewayConfigurationError(f"Unsupported gateway: {gateway_config.name}")
    
    def get_gateway(self, gateway_name):
        """Get gateway instance by name"""
        self._load_gateways()  # Ensure gateways are loaded
        gateway_name = gateway_name.lower()
        if gateway_name not in self.gateways:
            raise GatewayConfigurationError(f"Gateway {gateway_name} not found or not enabled")
        return self.gateways[gateway_name]
    
    def get_available_gateways(self):
        """Get list of available payment gateways"""
        self._load_gateways()  # Ensure gateways are loaded
        return [
            {
                'name': gateway.name,
                'display_name': gateway.display_name,
                'is_test_mode': gateway.is_test_mode,
                'supported_currencies': gateway.get_supported_currencies(),
                'supported_payment_methods': gateway.get_supported_payment_methods(),
                'transaction_fee_percentage': float(gateway.transaction_fee_percentage),
                'transaction_fee_fixed': float(gateway.transaction_fee_fixed),
                'min_amount': float(gateway.min_amount) if gateway.min_amount else None,
                'max_amount': float(gateway.max_amount) if gateway.max_amount else None
            }
            for gateway in self.gateways.values()
        ]
    
    def process_payment(self, order_id, gateway_name, payment_method_type=None, 
                       payment_method_details=None, customer_details=None, **kwargs):
        """
        Process payment for an order
        
        Args:
            order_id (int): Order ID
            gateway_name (str): Payment gateway name
            payment_method_type (str): Payment method type
            payment_method_details (dict): Payment method details
            customer_details (dict): Customer details
            **kwargs: Additional payment parameters
            
        Returns:
            dict: Payment processing result
        """
        try:
            # Get order
            order = Order.get_by_id(order_id)
            if not order:
                raise PaymentValidationError("Order not found")
            
            if not order.order_items:
                raise PaymentValidationError("Order has no items")
            
            # Get gateway
            gateway = self.get_gateway(gateway_name)
            
            # Validate gateway configuration
            is_valid, error_message = gateway.gateway.check_transaction_limits(order.grand_total)
            if not is_valid:
                raise PaymentValidationError(error_message)
            
            # Create payment record
            payment = Payment.create_gateway_payment(
                order_id=order_id,
                payment_mode=gateway.gateway.display_name,
                amount=order.grand_total,
                gateway_id=gateway.gateway.id,
                processed_by=kwargs.get('processed_by'),
                payment_method_type=payment_method_type,
                payment_method_details=payment_method_details
            )
            
            # Create transaction record
            transaction = PaymentTransaction.create_transaction(
                payment_id=payment.id,
                gateway_id=gateway.gateway.id,
                amount=order.grand_total,
                currency='INR'
            )
            
            # Set metadata
            metadata = {
                'order_id': order_id,
                'order_number': order.order_number,
                'customer_name': order.customer_name_decrypted,
                'customer_mobile': order.customer_mobile_decrypted,
                'processed_by': kwargs.get('processed_by')
            }
            
            if customer_details:
                metadata.update(customer_details)
            
            transaction.metadata = metadata
            db.session.commit()
            
            # Process payment based on gateway
            if gateway_name.lower() == 'razorpay':
                return self._process_razorpay_payment(payment, transaction, gateway, metadata, **kwargs)
            elif gateway_name.lower() == 'stripe':
                return self._process_stripe_payment(payment, transaction, gateway, metadata, **kwargs)
            else:
                raise PaymentProcessingError(f"Unsupported gateway: {gateway_name}")
                
        except Exception as e:
            current_app.logger.error(f"Payment processing failed: {str(e)}")
            # Update payment and transaction status to failed
            if 'payment' in locals():
                payment.mark_failed()
            if 'transaction' in locals():
                transaction.mark_failed(error_message=str(e))
            raise PaymentProcessingError(f"Payment processing failed: {str(e)}")
    
    def _process_razorpay_payment(self, payment, transaction, gateway, metadata, **kwargs):
        """Process Razorpay payment"""
        try:
            # Create Razorpay order
            receipt = f"ORD_{payment.order.order_number}_{payment.id}"
            order_response = gateway.create_order(
                amount=payment.amount,
                currency='INR',
                receipt=receipt,
                notes=metadata
            )
            
            # Update payment and transaction with gateway details
            payment.update_gateway_transaction(
                gateway_order_id=order_response['order_id'],
                gateway_response=order_response
            )
            
            transaction.gateway_order_id = order_response['order_id']
            transaction.gateway_transaction_id = order_response.get('gateway_transaction_id')
            transaction.status = 'pending'
            db.session.commit()
            
            return {
                'success': True,
                'payment_id': payment.id,
                'transaction_id': transaction.id,
                'gateway': 'razorpay',
                'order_id': order_response['order_id'],
                'amount': float(payment.amount),
                'currency': order_response['currency'],
                'status': 'pending',
                'client_config': {
                    'key': gateway.gateway.api_key,
                    'order_id': order_response['order_id'],
                    'amount': int(payment.amount * 100),  # Razorpay expects paise
                    'currency': order_response['currency'],
                    'name': 'Restaurant POS',
                    'description': f'Order {payment.order.order_number}',
                    'image': '/static/images/pos-logo.png',
                    'prefill': {
                        'name': payment.order.customer_name_decrypted,
                        'email': kwargs.get('customer_email'),
                        'contact': payment.order.customer_mobile_decrypted
                    },
                    'notes': metadata
                }
            }
            
        except Exception as e:
            transaction.mark_failed(error_message=str(e))
            raise PaymentProcessingError(f"Razorpay payment failed: {str(e)}")
    
    def _process_stripe_payment(self, payment, transaction, gateway, metadata, **kwargs):
        """Process Stripe payment"""
        try:
            # Create Stripe payment intent
            intent_response = gateway.create_payment_intent(
                amount=payment.amount,
                currency='inr',
                metadata=metadata,
                capture_method='automatic'
            )
            
            # Update payment and transaction with gateway details
            payment.update_gateway_transaction(
                gateway_order_id=intent_response['payment_intent_id'],
                gateway_response=intent_response
            )
            
            transaction.gateway_order_id = intent_response['payment_intent_id']
            transaction.status = 'pending'
            db.session.commit()
            
            return {
                'success': True,
                'payment_id': payment.id,
                'transaction_id': transaction.id,
                'gateway': 'stripe',
                'payment_intent_id': intent_response['payment_intent_id'],
                'client_secret': intent_response['client_secret'],
                'amount': float(payment.amount),
                'currency': intent_response['currency'],
                'status': 'pending'
            }
            
        except Exception as e:
            transaction.mark_failed(error_message=str(e))
            raise PaymentProcessingError(f"Stripe payment failed: {str(e)}")
    
    def confirm_payment(self, payment_id, gateway_transaction_id=None, **kwargs):
        """
        Confirm payment after customer completion
        
        Args:
            payment_id (int): Payment ID
            gateway_transaction_id (str): Gateway transaction ID
            **kwargs: Additional confirmation parameters
            
        Returns:
            dict: Payment confirmation result
        """
        try:
            payment = Payment.get_by_id(payment_id)
            if not payment:
                raise PaymentValidationError("Payment not found")
            
            transaction = PaymentTransaction.get_by_payment(payment_id)[-1]  # Get latest transaction
            gateway = self.get_gateway(payment.gateway.name)
            
            if payment.gateway.name == 'razorpay':
                return self._confirm_razorpay_payment(payment, transaction, gateway, **kwargs)
            elif payment.gateway.name == 'stripe':
                return self._confirm_stripe_payment(payment, transaction, gateway, **kwargs)
            else:
                raise PaymentProcessingError(f"Unsupported gateway: {payment.gateway.name}")
                
        except Exception as e:
            current_app.logger.error(f"Payment confirmation failed: {str(e)}")
            raise PaymentProcessingError(f"Payment confirmation failed: {str(e)}")
    
    def _confirm_razorpay_payment(self, payment, transaction, gateway, **kwargs):
        """Confirm Razorpay payment"""
        try:
            payment_id = kwargs.get('razorpay_payment_id')
            if not payment_id:
                raise PaymentValidationError("Razorpay payment ID is required")
            
            # Get payment details from Razorpay
            payment_details = gateway.get_payment_details(payment_id)
            
            if payment_details['status'] == 'captured':
                # Payment successful
                payment.mark_completed()
                transaction.mark_succeeded(gateway_status=payment_details['status'])
                
                # Update payment with transaction details
                payment.update_gateway_transaction(
                    gateway_transaction_id=payment_id,
                    gateway_response=payment_details,
                    status='Completed'
                )
                
                # Update transaction with payment method details
                transaction.gateway_transaction_id = payment_id
                transaction.payment_method_type = payment_details.get('method')
                transaction.payment_method_details = {
                    'method': payment_details.get('method'),
                    'card_id': payment_details.get('card_id'),
                    'bank': payment_details.get('bank'),
                    'wallet': payment_details.get('wallet'),
                    'vpa': payment_details.get('vpa')
                }
                
                db.session.commit()
                
                return {
                    'success': True,
                    'payment_id': payment.id,
                    'transaction_id': transaction.id,
                    'status': 'completed',
                    'gateway_transaction_id': payment_id,
                    'amount': float(payment.amount),
                    'payment_method': payment_details.get('method'),
                    'transaction_fee': float(transaction.transaction_fee)
                }
            
            elif payment_details['status'] == 'failed':
                # Payment failed
                payment.mark_failed()
                transaction.mark_failed(
                    error_code=payment_details.get('error_code'),
                    error_message=payment_details.get('error_description')
                )
                
                return {
                    'success': False,
                    'payment_id': payment.id,
                    'status': 'failed',
                    'error_code': payment_details.get('error_code'),
                    'error_message': payment_details.get('error_description')
                }
            
            else:
                # Payment pending or requires action
                transaction.status = 'processing'
                db.session.commit()
                
                return {
                    'success': False,
                    'payment_id': payment.id,
                    'status': payment_details['status'],
                    'requires_action': True
                }
                
        except Exception as e:
            transaction.mark_failed(error_message=str(e))
            raise PaymentProcessingError(f"Razorpay payment confirmation failed: {str(e)}")
    
    def _confirm_stripe_payment(self, payment, transaction, gateway, **kwargs):
        """Confirm Stripe payment"""
        try:
            payment_intent_id = kwargs.get('stripe_payment_intent_id') or transaction.gateway_order_id
            
            # Get payment intent details from Stripe
            intent_details = gateway.get_payment_intent(payment_intent_id)
            
            if intent_details['status'] == 'succeeded':
                # Payment successful
                payment.mark_completed()
                transaction.mark_succeeded(gateway_status=intent_details['status'])
                
                # Update payment with transaction details
                payment.update_gateway_transaction(
                    gateway_transaction_id=payment_intent_id,
                    gateway_response=intent_details,
                    status='Completed'
                )
                
                # Update transaction with payment method details
                if intent_details.get('charges'):
                    charge = intent_details['charges'][0]  # Get first charge
                    transaction.payment_method_type = charge.get('payment_method_details', {}).get('type')
                    transaction.payment_method_details = charge.get('payment_method_details', {})
                
                db.session.commit()
                
                return {
                    'success': True,
                    'payment_id': payment.id,
                    'transaction_id': transaction.id,
                    'status': 'completed',
                    'payment_intent_id': payment_intent_id,
                    'amount': float(payment.amount),
                    'payment_method': transaction.payment_method_type,
                    'transaction_fee': float(transaction.transaction_fee)
                }
            
            elif intent_details['status'] == 'payment_failed':
                # Payment failed
                payment.mark_failed()
                transaction.mark_failed(
                    error_code=intent_details.get('error_code'),
                    error_message=intent_details.get('error_message')
                )
                
                return {
                    'success': False,
                    'payment_id': payment.id,
                    'status': 'failed',
                    'error_code': intent_details.get('error_code'),
                    'error_message': intent_details.get('error_message')
                }
            
            else:
                # Payment requires action or is processing
                transaction.status = 'processing'
                db.session.commit()
                
                return {
                    'success': False,
                    'payment_id': payment.id,
                    'status': intent_details['status'],
                    'requires_action': intent_details.get('next_action') is not None
                }
                
        except Exception as e:
            transaction.mark_failed(error_message=str(e))
            raise PaymentProcessingError(f"Stripe payment confirmation failed: {str(e)}")
    
    def process_webhook(self, gateway_name, payload, signature, timestamp=None):
        """
        Process webhook from payment gateway
        
        Args:
            gateway_name (str): Gateway name
            payload (str): Webhook payload
            signature (str): Webhook signature
            timestamp (int): Timestamp (for Stripe)
            
        Returns:
            dict: Webhook processing result
        """
        try:
            gateway = self.get_gateway(gateway_name)
            
            # Verify webhook signature
            if gateway_name.lower() == 'razorpay':
                gateway.verify_webhook_signature(payload, signature)
                webhook_data = json.loads(payload)
            elif gateway_name.lower() == 'stripe':
                webhook_data = gateway.verify_webhook_signature(payload, signature, timestamp)
            else:
                raise WebhookVerificationError(f"Unsupported gateway: {gateway_name}")
            
            # Process webhook data
            processed_data = gateway.process_webhook(webhook_data)
            
            # Update payment and transaction based on webhook
            if processed_data['status'] in ['captured', 'succeeded']:
                return self._handle_successful_webhook(gateway_name, processed_data)
            elif processed_data['status'] in ['failed', 'canceled']:
                return self._handle_failed_webhook(gateway_name, processed_data)
            elif processed_data['status'] == 'refunded':
                return self._handle_refunded_webhook(gateway_name, processed_data)
            else:
                return {
                    'success': True,
                    'message': f"Webhook processed for {processed_data['event']}",
                    'status': processed_data['status']
                }
                
        except Exception as e:
            current_app.logger.error(f"Webhook processing failed: {str(e)}")
            raise PaymentProcessingError(f"Webhook processing failed: {str(e)}")
    
    def _handle_successful_webhook(self, gateway_name, processed_data):
        """Handle successful payment webhook"""
        try:
            # Find payment by gateway transaction ID
            transaction = None
            
            if gateway_name.lower() == 'razorpay':
                transaction = PaymentTransaction.get_by_gateway_transaction_id(processed_data['payment_id'])
            elif gateway_name.lower() == 'stripe':
                transaction = PaymentTransaction.get_by_gateway_transaction_id(processed_data['payment_intent_id'])
            
            if not transaction:
                return {
                    'success': False,
                    'message': 'Transaction not found for webhook'
                }
            
            # Update transaction and payment
            transaction.mark_succeeded()
            transaction.payment.mark_completed()
            transaction.set_webhook_data(processed_data)
            
            return {
                'success': True,
                'message': 'Payment webhook processed successfully',
                'payment_id': transaction.payment_id,
                'transaction_id': transaction.id
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to handle successful webhook: {str(e)}")
            return {
                'success': False,
                'message': f'Webhook processing failed: {str(e)}'
            }
    
    def _handle_failed_webhook(self, gateway_name, processed_data):
        """Handle failed payment webhook"""
        try:
            # Find payment by gateway transaction ID
            transaction = None
            
            if gateway_name.lower() == 'razorpay':
                transaction = PaymentTransaction.get_by_gateway_transaction_id(processed_data['payment_id'])
            elif gateway_name.lower() == 'stripe':
                transaction = PaymentTransaction.get_by_gateway_transaction_id(processed_data['payment_intent_id'])
            
            if not transaction:
                return {
                    'success': False,
                    'message': 'Transaction not found for webhook'
                }
            
            # Update transaction and payment
            transaction.mark_failed(
                error_code=processed_data.get('error_code'),
                error_message=processed_data.get('error_message') or processed_data.get('error_description')
            )
            transaction.payment.mark_failed()
            transaction.set_webhook_data(processed_data)
            
            return {
                'success': True,
                'message': 'Payment failure webhook processed successfully',
                'payment_id': transaction.payment_id,
                'transaction_id': transaction.id
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to handle failed webhook: {str(e)}")
            return {
                'success': False,
                'message': f'Webhook processing failed: {str(e)}'
            }
    
    def _handle_refunded_webhook(self, gateway_name, processed_data):
        """Handle refunded payment webhook"""
        try:
            # Find payment by gateway transaction ID
            transaction = None
            
            if gateway_name.lower() == 'razorpay':
                transaction = PaymentTransaction.get_by_gateway_transaction_id(processed_data['payment_id'])
            elif gateway_name.lower() == 'stripe':
                transaction = PaymentTransaction.get_by_gateway_transaction_id(processed_data['payment_intent_id'])
            
            if not transaction:
                return {
                    'success': False,
                    'message': 'Transaction not found for webhook'
                }
            
            # Process refund
            refund_amount = processed_data.get('amount', transaction.amount)
            success, message = transaction.payment.process_refund(
                refund_amount=refund_amount,
                refund_reason='Gateway refund processed'
            )
            
            if success:
                transaction.mark_refunded()
                transaction.set_webhook_data(processed_data)
                
                return {
                    'success': True,
                    'message': 'Refund webhook processed successfully',
                    'payment_id': transaction.payment_id,
                    'transaction_id': transaction.id,
                    'refund_amount': float(refund_amount)
                }
            else:
                return {
                    'success': False,
                    'message': f'Refund processing failed: {message}'
                }
            
        except Exception as e:
            current_app.logger.error(f"Failed to handle refunded webhook: {str(e)}")
            return {
                'success': False,
                'message': f'Webhook processing failed: {str(e)}'
            }
    
    def refund_payment(self, payment_id, amount=None, reason=None, gateway_refund_id=None):
        """
        Process refund for a payment
        
        Args:
            payment_id (int): Payment ID
            amount (Decimal): Refund amount (optional)
            reason (str): Refund reason
            gateway_refund_id (str): Gateway refund ID
            
        Returns:
            dict: Refund processing result
        """
        try:
            payment = Payment.get_by_id(payment_id)
            if not payment:
                raise PaymentValidationError("Payment not found")
            
            if not payment.is_gateway_payment:
                raise PaymentValidationError("Can only refund gateway payments")
            
            if payment.is_fully_refunded:
                raise PaymentValidationError("Payment is already fully refunded")
            
            # Get gateway
            gateway = self.get_gateway(payment.gateway.name)
            
            # Determine refund amount
            refund_amount = amount or payment.pending_refund_amount
            
            if payment.gateway.name == 'razorpay':
                return self._process_razorpay_refund(payment, gateway, refund_amount, reason)
            elif payment.gateway.name == 'stripe':
                return self._process_stripe_refund(payment, gateway, refund_amount, reason)
            else:
                raise PaymentProcessingError(f"Unsupported gateway: {payment.gateway.name}")
                
        except Exception as e:
            current_app.logger.error(f"Refund processing failed: {str(e)}")
            raise PaymentProcessingError(f"Refund processing failed: {str(e)}")
    
    def _process_razorpay_refund(self, payment, gateway, refund_amount, reason):
        """Process Razorpay refund"""
        try:
            # Create refund in Razorpay
            refund_response = gateway.refund_payment(
                payment_id=payment.gateway_transaction_id,
                amount=refund_amount
            )
            
            # Update payment
            success, message = payment.process_refund(
                refund_amount=refund_amount,
                refund_reason=reason,
                gateway_refund_id=refund_response['refund_id']
            )
            
            if not success:
                raise PaymentProcessingError(message)
            
            # Update transaction
            transactions = PaymentTransaction.get_by_payment(payment.id)
            for transaction in transactions:
                if transaction.gateway_transaction_id == payment.gateway_transaction_id:
                    transaction.mark_refunded()
                    break
            
            return {
                'success': True,
                'payment_id': payment.id,
                'refund_id': refund_response['refund_id'],
                'refund_amount': float(refund_amount),
                'status': refund_response['status'],
                'message': 'Refund processed successfully'
            }
            
        except Exception as e:
            raise PaymentProcessingError(f"Razorpay refund failed: {str(e)}")
    
    def _process_stripe_refund(self, payment, gateway, refund_amount, reason):
        """Process Stripe refund"""
        try:
            # Create refund in Stripe
            refund_response = gateway.create_refund(
                payment_intent_id=payment.gateway_order_id,
                amount=refund_amount,
                reason='requested_by_customer' if reason else None
            )
            
            # Update payment
            success, message = payment.process_refund(
                refund_amount=refund_amount,
                refund_reason=reason,
                gateway_refund_id=refund_response['refund_id']
            )
            
            if not success:
                raise PaymentProcessingError(message)
            
            # Update transaction
            transactions = PaymentTransaction.get_by_payment(payment.id)
            for transaction in transactions:
                if transaction.gateway_order_id == payment.gateway_order_id:
                    transaction.mark_refunded()
                    break
            
            return {
                'success': True,
                'payment_id': payment.id,
                'refund_id': refund_response['refund_id'],
                'refund_amount': float(refund_amount),
                'status': refund_response['status'],
                'message': 'Refund processed successfully'
            }
            
        except Exception as e:
            raise PaymentProcessingError(f"Stripe refund failed: {str(e)}")
    
    def get_payment_status(self, payment_id):
        """Get current payment status"""
        try:
            payment = Payment.get_by_id(payment_id)
            if not payment:
                raise PaymentValidationError("Payment not found")
            
            return {
                'payment_id': payment.id,
                'order_id': payment.order_id,
                'order_number': payment.order.order_number,
                'status': payment.status,
                'amount': float(payment.amount),
                'refunded_amount': float(payment.refunded_amount),
                'pending_refund_amount': float(payment.pending_refund_amount),
                'gateway': payment.gateway.name if payment.gateway else None,
                'gateway_transaction_id': payment.gateway_transaction_id,
                'gateway_order_id': payment.gateway_order_id,
                'created_at': payment.created_at.isoformat() if payment.created_at else None,
                'updated_at': payment.updated_at.isoformat() if payment.updated_at else None
            }
            
        except Exception as e:
            raise PaymentProcessingError(f"Failed to get payment status: {str(e)}")


# Global payment processor instance (initialized lazily)
_payment_processor = None

def get_payment_processor():
    """Get or create payment processor instance"""
    global _payment_processor
    if _payment_processor is None:
        _payment_processor = PaymentProcessor()
    return _payment_processor