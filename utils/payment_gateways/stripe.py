import stripe
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from flask import current_app
from models.payment_gateway import PaymentGateway, PaymentTransaction
from models.payment import Payment
from .exceptions import PaymentGatewayError, WebhookVerificationError

class StripeGateway:
    """Stripe Payment Gateway Integration"""
    
    def __init__(self, gateway_config):
        """
        Initialize Stripe gateway
        
        Args:
            gateway_config (PaymentGateway): Payment gateway configuration
        """
        self.gateway = gateway_config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Stripe client"""
        try:
            if not self.gateway.api_key:
                raise PaymentGatewayError("Stripe API key is required")
            
            # Set Stripe API key
            stripe.api_key = self.gateway.api_key
            
            # Set API version for consistency
            stripe.api_version = '2023-10-16'
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to initialize Stripe client: {str(e)}")
    
    def create_payment_intent(self, amount, currency='inr', metadata=None, capture_method='automatic'):
        """
        Create Stripe payment intent
        
        Args:
            amount (Decimal): Amount in smallest currency unit (paise for INR)
            currency (str): Currency code (default: inr)
            metadata (dict): Additional metadata
            capture_method (str): 'automatic' or 'manual'
            
        Returns:
            dict: Payment intent details
        """
        try:
            # Convert amount to smallest currency unit (paise for INR)
            amount_in_smallest_unit = int(amount * 100)
            
            # Prepare payment intent data
            intent_data = {
                'amount': amount_in_smallest_unit,
                'currency': currency.lower(),
                'capture_method': capture_method,
                'automatic_payment_methods': {
                    'enabled': True
                }
            }
            
            if metadata:
                intent_data['metadata'] = metadata
            
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(**intent_data)
            
            return {
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'amount': amount_in_smallest_unit,
                'currency': payment_intent.currency,
                'status': payment_intent.status,
                'created': datetime.fromtimestamp(payment_intent.created),
                'capture_method': payment_intent.capture_method,
                'metadata': payment_intent.metadata
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to create Stripe payment intent: {str(e)}")
    
    def confirm_payment_intent(self, payment_intent_id, payment_method_id=None, return_url=None):
        """
        Confirm Stripe payment intent
        
        Args:
            payment_intent_id (str): Stripe payment intent ID
            payment_method_id (str): Payment method ID (optional)
            return_url (str): Return URL for 3D Secure (optional)
            
        Returns:
            dict: Confirmed payment intent details
        """
        try:
            confirm_data = {}
            
            if payment_method_id:
                confirm_data['payment_method'] = payment_method_id
            
            if return_url:
                confirm_data['return_url'] = return_url
            
            payment_intent = stripe.PaymentIntent.confirm(payment_intent_id, **confirm_data)
            
            return {
                'payment_intent_id': payment_intent.id,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'payment_method': payment_intent.payment_method,
                'created': datetime.fromtimestamp(payment_intent.created),
                'next_action': payment_intent.next_action,
                'charges': payment_intent.charges.data if payment_intent.charges else [],
                'metadata': payment_intent.metadata
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to confirm Stripe payment intent: {str(e)}")
    
    def capture_payment_intent(self, payment_intent_id, amount_to_capture=None):
        """
        Capture Stripe payment intent
        
        Args:
            payment_intent_id (str): Stripe payment intent ID
            amount_to_capture (Decimal): Amount to capture (optional)
            
        Returns:
            dict: Captured payment intent details
        """
        try:
            capture_data = {}
            
            if amount_to_capture:
                capture_data['amount_to_capture'] = int(amount_to_capture * 100)
            
            payment_intent = stripe.PaymentIntent.capture(payment_intent_id, **capture_data)
            
            return {
                'payment_intent_id': payment_intent.id,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'amount_capturable': payment_intent.amount_capturable,
                'amount_received': payment_intent.amount_received,
                'currency': payment_intent.currency,
                'captured': payment_intent.status == 'succeeded',
                'charges': payment_intent.charges.data if payment_intent.charges else []
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to capture Stripe payment intent: {str(e)}")
    
    def create_refund(self, payment_intent_id, amount=None, reason=None, metadata=None):
        """
        Create Stripe refund
        
        Args:
            payment_intent_id (str): Stripe payment intent ID
            amount (Decimal): Amount to refund (optional)
            reason (str): Refund reason
            metadata (dict): Additional metadata
            
        Returns:
            dict: Refund details
        """
        try:
            refund_data = {
                'payment_intent': payment_intent_id
            }
            
            if amount:
                refund_data['amount'] = int(amount * 100)
            
            if reason:
                refund_data['reason'] = reason
            
            if metadata:
                refund_data['metadata'] = metadata
            
            refund = stripe.Refund.create(**refund_data)
            
            return {
                'refund_id': refund.id,
                'payment_intent_id': refund.payment_intent,
                'amount': Decimal(refund.amount) / 100,  # Convert from smallest unit
                'currency': refund.currency,
                'status': refund.status,
                'reason': refund.reason,
                'created': datetime.fromtimestamp(refund.created),
                'metadata': refund.metadata
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to create Stripe refund: {str(e)}")
    
    def get_payment_intent(self, payment_intent_id):
        """
        Get Stripe payment intent details
        
        Args:
            payment_intent_id (str): Stripe payment intent ID
            
        Returns:
            dict: Payment intent details
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                'payment_intent_id': payment_intent.id,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'amount_capturable': payment_intent.amount_capturable,
                'amount_received': payment_intent.amount_received,
                'payment_method': payment_intent.payment_method,
                'created': datetime.fromtimestamp(payment_intent.created),
                'captured': payment_intent.status == 'succeeded',
                'charges': payment_intent.charges.data if payment_intent.charges else [],
                'next_action': payment_intent.next_action,
                'metadata': payment_intent.metadata
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to get Stripe payment intent: {str(e)}")
    
    def verify_webhook_signature(self, payload, signature, timestamp=None):
        """
        Verify Stripe webhook signature
        
        Args:
            payload (str): Raw webhook payload
            signature (str): Webhook signature header
            timestamp (int): Timestamp from header (optional)
            
        Returns:
            dict: Verified webhook data
            
        Raises:
            WebhookVerificationError: If signature verification fails
        """
        try:
            if not self.gateway.webhook_secret:
                raise WebhookVerificationError("Webhook secret not configured")
            
            # Parse signature header
            signature_elements = {}
            for element in signature.split(','):
                key, value = element.split('=', 1)
                signature_elements[key] = value
            
            # Verify timestamp to prevent replay attacks
            if timestamp is None:
                timestamp = int(signature_elements.get('t', 0))
            
            # Check if timestamp is too old (5 minutes)
            if abs(datetime.utcnow().timestamp() - timestamp) > 300:
                raise WebhookVerificationError("Webhook timestamp too old")
            
            # Create expected signature
            signed_payload = f"{timestamp}.{payload}"
            expected_signature = hmac.new(
                self.gateway.webhook_secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature
            if not hmac.compare_digest(signature_elements.get('v1'), expected_signature):
                raise WebhookVerificationError("Invalid webhook signature")
            
            return json.loads(payload)
            
        except Exception as e:
            if isinstance(e, WebhookVerificationError):
                raise
            raise WebhookVerificationError(f"Webhook signature verification failed: {str(e)}")
    
    def process_webhook(self, webhook_data):
        """
        Process Stripe webhook data
        
        Args:
            webhook_data (dict): Webhook payload data
            
        Returns:
            dict: Processed webhook data
        """
        try:
            event_type = webhook_data.get('type')
            data = webhook_data.get('data', {})
            object_data = data.get('object', {})
            
            if event_type == 'payment_intent.succeeded':
                # Payment intent succeeded
                payment_intent_id = object_data.get('id')
                
                return {
                    'event': event_type,
                    'payment_intent_id': payment_intent_id,
                    'status': 'succeeded',
                    'amount': Decimal(object_data.get('amount', 0)) / 100,
                    'currency': object_data.get('currency'),
                    'payment_method': object_data.get('payment_method'),
                    'created': datetime.fromtimestamp(object_data.get('created')),
                    'charges': object_data.get('charges', {}).get('data', []),
                    'metadata': object_data.get('metadata', {})
                }
            
            elif event_type == 'payment_intent.payment_failed':
                # Payment intent failed
                payment_intent_id = object_data.get('id')
                last_payment_error = object_data.get('last_payment_error')
                
                return {
                    'event': event_type,
                    'payment_intent_id': payment_intent_id,
                    'status': 'failed',
                    'amount': Decimal(object_data.get('amount', 0)) / 100,
                    'currency': object_data.get('currency'),
                    'error_code': last_payment_error.get('code') if last_payment_error else None,
                    'error_message': last_payment_error.get('message') if last_payment_error else None,
                    'error_type': last_payment_error.get('type') if last_payment_error else None,
                    'created': datetime.fromtimestamp(object_data.get('created')),
                    'metadata': object_data.get('metadata', {})
                }
            
            elif event_type == 'payment_intent.canceled':
                # Payment intent canceled
                payment_intent_id = object_data.get('id')
                
                return {
                    'event': event_type,
                    'payment_intent_id': payment_intent_id,
                    'status': 'canceled',
                    'amount': Decimal(object_data.get('amount', 0)) / 100,
                    'currency': object_data.get('currency'),
                    'created': datetime.fromtimestamp(object_data.get('created')),
                    'cancellation_reason': object_data.get('cancellation_reason'),
                    'metadata': object_data.get('metadata', {})
                }
            
            elif event_type == 'charge.refunded':
                # Charge refunded
                charge_id = object_data.get('id')
                payment_intent_id = object_data.get('payment_intent')
                
                return {
                    'event': event_type,
                    'charge_id': charge_id,
                    'payment_intent_id': payment_intent_id,
                    'status': 'refunded',
                    'amount': Decimal(object_data.get('amount', 0)) / 100,
                    'currency': object_data.get('currency'),
                    'amount_refunded': Decimal(object_data.get('amount_refunded', 0)) / 100,
                    'created': datetime.fromtimestamp(object_data.get('created')),
                    'refunds': object_data.get('refunds', {}).get('data', []),
                    'metadata': object_data.get('metadata', {})
                }
            
            elif event_type == 'refund.created':
                # Refund created
                refund_id = object_data.get('id')
                payment_intent_id = object_data.get('payment_intent')
                
                return {
                    'event': event_type,
                    'refund_id': refund_id,
                    'payment_intent_id': payment_intent_id,
                    'status': 'refunded',
                    'amount': Decimal(object_data.get('amount', 0)) / 100,
                    'currency': object_data.get('currency'),
                    'reason': object_data.get('reason'),
                    'created': datetime.fromtimestamp(object_data.get('created')),
                    'metadata': object_data.get('metadata', {})
                }
            
            else:
                # Unhandled event type
                return {
                    'event': event_type,
                    'status': 'unhandled',
                    'object': object_data,
                    'data': webhook_data
                }
                
        except Exception as e:
            raise PaymentGatewayError(f"Failed to process Stripe webhook: {str(e)}")
    
    def create_customer(self, name, email=None, phone=None, metadata=None):
        """
        Create Stripe customer
        
        Args:
            name (str): Customer name
            email (str): Customer email
            phone (str): Customer phone
            metadata (dict): Additional metadata
            
        Returns:
            dict: Customer details
        """
        try:
            customer_data = {
                'name': name
            }
            
            if email:
                customer_data['email'] = email
            
            if phone:
                customer_data['phone'] = phone
            
            if metadata:
                customer_data['metadata'] = metadata
            
            customer = stripe.Customer.create(**customer_data)
            
            return {
                'customer_id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'created': datetime.fromtimestamp(customer.created),
                'metadata': customer.metadata
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to create Stripe customer: {str(e)}")
    
    def attach_payment_method(self, payment_method_id, customer_id):
        """
        Attach payment method to customer
        
        Args:
            payment_method_id (str): Payment method ID
            customer_id (str): Customer ID
            
        Returns:
            dict: Payment method details
        """
        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            
            return {
                'payment_method_id': payment_method.id,
                'type': payment_method.type,
                'customer': payment_method.customer,
                'created': datetime.fromtimestamp(payment_method.created),
                'card': payment_method.card.to_dict() if payment_method.card else None,
                'metadata': payment_method.metadata
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to attach payment method: {str(e)}")
    
    def list_payment_methods(self, customer_id, type='card'):
        """
        List customer's payment methods
        
        Args:
            customer_id (str): Customer ID
            type (str): Payment method type
            
        Returns:
            list: Customer's payment methods
        """
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=type
            )
            
            return [{
                'payment_method_id': pm.id,
                'type': pm.type,
                'created': datetime.fromtimestamp(pm.created),
                'customer': pm.customer,
                'card': pm.card.to_dict() if pm.card else None,
                'metadata': pm.metadata
            } for pm in payment_methods.data]
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to list payment methods: {str(e)}")
    
    def get_payment_method(self, payment_method_id):
        """
        Get payment method details
        
        Args:
            payment_method_id (str): Payment method ID
            
        Returns:
            dict: Payment method details
        """
        try:
            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
            
            return {
                'payment_method_id': payment_method.id,
                'type': payment_method.type,
                'created': datetime.fromtimestamp(payment_method.created),
                'customer': payment_method.customer,
                'card': payment_method.card.to_dict() if payment_method.card else None,
                'metadata': payment_method.metadata
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to get payment method: {str(e)}")
    
    def create_setup_intent(self, customer_id, payment_method_types=None, usage='off_session'):
        """
        Create setup intent for saving payment method
        
        Args:
            customer_id (str): Customer ID
            payment_method_types (list): Payment method types
            usage (str): Usage type
            
        Returns:
            dict: Setup intent details
        """
        try:
            setup_data = {
                'customer': customer_id,
                'usage': usage
            }
            
            if payment_method_types:
                setup_data['payment_method_types'] = payment_method_types
            
            setup_intent = stripe.SetupIntent.create(**setup_data)
            
            return {
                'setup_intent_id': setup_intent.id,
                'client_secret': setup_intent.client_secret,
                'customer': setup_intent.customer,
                'status': setup_intent.status,
                'created': datetime.fromtimestamp(setup_intent.created),
                'payment_method_types': setup_intent.payment_method_types,
                'usage': setup_intent.usage,
                'metadata': setup_intent.metadata
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to create setup intent: {str(e)}")
    
    def __str__(self):
        return f"StripeGateway(gateway={self.gateway.name})"