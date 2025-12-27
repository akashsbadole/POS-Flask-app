import razorpay
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from flask import current_app
from models.payment_gateway import PaymentGateway, PaymentTransaction
from models.payment import Payment
from .exceptions import PaymentGatewayError, WebhookVerificationError

class RazorpayGateway:
    """Razorpay Payment Gateway Integration"""
    
    def __init__(self, gateway_config):
        """
        Initialize Razorpay gateway
        
        Args:
            gateway_config (PaymentGateway): Payment gateway configuration
        """
        self.gateway = gateway_config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Razorpay client"""
        try:
            if not self.gateway.api_key or not self.gateway.secret_key:
                raise PaymentGatewayError("Razorpay API key and secret key are required")
            
            # Create Razorpay client
            self.client = razorpay.Client(auth=(self.gateway.api_key, self.gateway.secret_key))
            
            # Set headers for API calls
            self.client.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to initialize Razorpay client: {str(e)}")
    
    def create_order(self, amount, currency='INR', receipt=None, notes=None):
        """
        Create Razorpay order
        
        Args:
            amount (Decimal): Amount in paise (multiply by 100)
            currency (str): Currency code (default: INR)
            receipt (str): Receipt number
            notes (dict): Additional notes
            
        Returns:
            dict: Order details from Razorpay
        """
        try:
            # Convert amount to paise (Razorpay expects amount in paise)
            amount_paise = int(amount * 100)
            
            # Prepare order data
            order_data = {
                'amount': amount_paise,
                'currency': currency,
                'payment_capture': 1,  # Auto-capture payments
            }
            
            if receipt:
                order_data['receipt'] = receipt
            
            if notes:
                order_data['notes'] = notes
            
            # Add customer info if available
            if notes and 'customer_name' in notes:
                order_data['customer'] = {
                    'name': notes['customer_name']
                }
            
            # Create order via Razorpay
            response = self.client.order.create(data=order_data)
            
            return {
                'order_id': response['id'],
                'amount': amount_paise,
                'currency': response['currency'],
                'amount_due': response['amount_due'],
                'amount_paid': response['amount_paid'],
                'status': response['status'],
                'receipt': response.get('receipt'),
                'created_at': datetime.fromtimestamp(response['created_at']),
                'notes': response.get('notes', {})
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to create Razorpay order: {str(e)}")
    
    def capture_payment(self, payment_id, amount=None):
        """
        Capture Razorpay payment
        
        Args:
            payment_id (str): Razorpay payment ID
            amount (Decimal): Amount to capture (optional, captures full amount if not provided)
            
        Returns:
            dict: Payment capture details
        """
        try:
            capture_data = {}
            
            if amount:
                # Convert amount to paise
                capture_data['amount'] = int(amount * 100)
            
            response = self.client.payment.capture(payment_id, capture_data)
            
            return {
                'payment_id': response['id'],
                'amount': Decimal(response['amount']) / 100,  # Convert from paise
                'currency': response['currency'],
                'status': response['status'],
                'method': response['method'],
                'captured': response.get('captured', False),
                'created_at': datetime.fromtimestamp(response['created_at']),
                'description': response.get('description'),
                'card_id': response.get('card', {}).get('id'),
                'bank': response.get('bank'),
                'wallet': response.get('wallet'),
                'vpa': response.get('vpa'),
                'email': response.get('email'),
                'contact': response.get('contact'),
                'customer_id': response.get('customer_id'),
                'order_id': response.get('order_id')
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to capture Razorpay payment: {str(e)}")
    
    def refund_payment(self, payment_id, amount=None, speed='normal'):
        """
        Refund Razorpay payment
        
        Args:
            payment_id (str): Razorpay payment ID
            amount (Decimal): Amount to refund (optional, refunds full amount if not provided)
            speed (str): Refund speed ('normal' or 'optimum')
            
        Returns:
            dict: Refund details
        """
        try:
            refund_data = {
                'speed': speed
            }
            
            if amount:
                # Convert amount to paise
                refund_data['amount'] = int(amount * 100)
            
            response = self.client.payment.refund(payment_id, refund_data)
            
            return {
                'refund_id': response['id'],
                'payment_id': response['payment_id'],
                'amount': Decimal(response['amount']) / 100,  # Convert from paise
                'currency': response['currency'],
                'status': response['status'],
                'speed': response.get('speed'),
                'created_at': datetime.fromtimestamp(response['created_at']),
                'batch_id': response.get('batch_id'),
                'notes': response.get('notes', {})
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to refund Razorpay payment: {str(e)}")
    
    def get_payment_details(self, payment_id):
        """
        Get Razorpay payment details
        
        Args:
            payment_id (str): Razorpay payment ID
            
        Returns:
            dict: Payment details
        """
        try:
            response = self.client.payment.fetch(payment_id)
            
            return {
                'payment_id': response['id'],
                'amount': Decimal(response['amount']) / 100,  # Convert from paise
                'currency': response['currency'],
                'status': response['status'],
                'method': response['method'],
                'captured': response.get('captured', False),
                'created_at': datetime.fromtimestamp(response['created_at']),
                'description': response.get('description'),
                'card_id': response.get('card', {}).get('id') if response.get('card') else None,
                'bank': response.get('bank'),
                'wallet': response.get('wallet'),
                'vpa': response.get('vpa'),
                'email': response.get('email'),
                'contact': response.get('contact'),
                'customer_id': response.get('customer_id'),
                'order_id': response.get('order_id'),
                'invoice_id': response.get('invoice_id'),
                'international': response.get('international', False),
                'amount_refunded': Decimal(response.get('amount_refunded', 0)) / 100,
                'refund_status': response.get('refund_status'),
                'captured': response.get('captured', False),
                'description': response.get('description'),
                'card': response.get('card', {}),
                'bank_transfer': response.get('bank_transfer', {}),
                'failure_reason': response.get('failure_reason'),
                'acquirer_data': response.get('acquirer_data', {})
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to get Razorpay payment details: {str(e)}")
    
    def verify_webhook_signature(self, payload, signature):
        """
        Verify Razorpay webhook signature
        
        Args:
            payload (str): Raw webhook payload
            signature (str): Webhook signature header
            
        Returns:
            bool: True if signature is valid
            
        Raises:
            WebhookVerificationError: If signature verification fails
        """
        try:
            if not self.gateway.webhook_secret:
                raise WebhookVerificationError("Webhook secret not configured")
            
            # Create expected signature
            expected_signature = hmac.new(
                self.gateway.webhook_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature
            if not hmac.compare_digest(signature, expected_signature):
                raise WebhookVerificationError("Invalid webhook signature")
            
            return True
            
        except Exception as e:
            if isinstance(e, WebhookVerificationError):
                raise
            raise WebhookVerificationError(f"Webhook signature verification failed: {str(e)}")
    
    def process_webhook(self, webhook_data):
        """
        Process Razorpay webhook data
        
        Args:
            webhook_data (dict): Webhook payload data
            
        Returns:
            dict: Processed webhook data
        """
        try:
            event_type = webhook_data.get('event')
            payload = webhook_data.get('payload', {})
            
            if event_type == 'payment.captured':
                # Payment captured successfully
                payment_data = payload.get('payment', {})
                payment_id = payment_data.get('id')
                
                return {
                    'event': event_type,
                    'payment_id': payment_id,
                    'status': 'captured',
                    'amount': Decimal(payment_data.get('amount', 0)) / 100,
                    'currency': payment_data.get('currency'),
                    'method': payment_data.get('method'),
                    'created_at': datetime.fromtimestamp(payment_data.get('created_at')),
                    'order_id': payment_data.get('order_id'),
                    'customer_id': payment_data.get('customer_id'),
                    'data': payment_data
                }
            
            elif event_type == 'payment.failed':
                # Payment failed
                payment_data = payload.get('payment', {})
                payment_id = payment_data.get('id')
                
                return {
                    'event': event_type,
                    'payment_id': payment_id,
                    'status': 'failed',
                    'amount': Decimal(payment_data.get('amount', 0)) / 100,
                    'currency': payment_data.get('currency'),
                    'error_code': payment_data.get('error_code'),
                    'error_description': payment_data.get('error_description'),
                    'error_source': payment_data.get('error_source'),
                    'error_step': payment_data.get('error_step'),
                    'error_reason': payment_data.get('error_reason'),
                    'created_at': datetime.fromtimestamp(payment_data.get('created_at')),
                    'order_id': payment_data.get('order_id'),
                    'data': payment_data
                }
            
            elif event_type == 'refund.processed':
                # Refund processed
                refund_data = payload.get('refund', {})
                refund_id = refund_data.get('id')
                payment_id = refund_data.get('payment_id')
                
                return {
                    'event': event_type,
                    'refund_id': refund_id,
                    'payment_id': payment_id,
                    'status': 'refunded',
                    'amount': Decimal(refund_data.get('amount', 0)) / 100,
                    'currency': refund_data.get('currency'),
                    'speed': refund_data.get('speed'),
                    'created_at': datetime.fromtimestamp(refund_data.get('created_at')),
                    'data': refund_data
                }
            
            elif event_type == 'order.paid':
                # Order paid (when payment is captured)
                order_data = payload.get('order', {})
                order_id = order_data.get('id')
                
                return {
                    'event': event_type,
                    'order_id': order_id,
                    'status': 'paid',
                    'amount': Decimal(order_data.get('amount', 0)) / 100,
                    'currency': order_data.get('currency'),
                    'amount_paid': Decimal(order_data.get('amount_paid', 0)) / 100,
                    'amount_due': Decimal(order_data.get('amount_due', 0)) / 100,
                    'created_at': datetime.fromtimestamp(order_data.get('created_at')),
                    'data': order_data
                }
            
            else:
                # Unhandled event type
                return {
                    'event': event_type,
                    'status': 'unhandled',
                    'data': webhook_data
                }
                
        except Exception as e:
            raise PaymentGatewayError(f"Failed to process Razorpay webhook: {str(e)}")
    
    def get_payment_methods(self):
        """
        Get supported payment methods
        
        Returns:
            dict: Supported payment methods
        """
        try:
            response = self.client.payment_methods.all()
            
            return {
                'card': response.get('card', []),
                'netbanking': response.get('netbanking', []),
                'wallet': response.get('wallet', []),
                'upi': response.get('upi', []),
                'emi': response.get('emi', []),
                'paylater': response.get('paylater', [])
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to get Razorpay payment methods: {str(e)}")
    
    def create_customer(self, name, email=None, contact=None):
        """
        Create Razorpay customer
        
        Args:
            name (str): Customer name
            email (str): Customer email
            contact (str): Customer contact number
            
        Returns:
            dict: Customer details
        """
        try:
            customer_data = {
                'name': name
            }
            
            if email:
                customer_data['email'] = email
            
            if contact:
                customer_data['contact'] = contact
            
            response = self.client.customer.create(data=customer_data)
            
            return {
                'customer_id': response['id'],
                'name': response['name'],
                'email': response.get('email'),
                'contact': response.get('contact'),
                'created_at': datetime.fromtimestamp(response['created_at']),
                'gstin': response.get('gstin'),
                'notes': response.get('notes', {})
            }
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to create Razorpay customer: {str(e)}")
    
    def get_customer_cards(self, customer_id):
        """
        Get customer saved cards
        
        Args:
            customer_id (str): Razorpay customer ID
            
        Returns:
            list: Customer's saved cards
        """
        try:
            response = self.client.customer.fetch(customer_id)
            cards = response.get('notes', {}).get('cards', [])
            
            return [{
                'card_id': card.get('id'),
                'name': card.get('name'),
                'last4': card.get('last4'),
                'network': card.get('network'),
                'type': card.get('type'),
                'issuer': card.get('issuer'),
                'international': card.get('international'),
                'emi': card.get('emi'),
                'sub_type': card.get('sub_type')
            } for card in cards]
            
        except Exception as e:
            raise PaymentGatewayError(f"Failed to get customer cards: {str(e)}")
    
    def __str__(self):
        return f"RazorpayGateway(gateway={self.gateway.name})"