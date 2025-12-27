"""
Comprehensive Payment Gateway Integration Tests
Tests Razorpay and Stripe integration with the restaurant POS system
"""

import unittest
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# Import Flask app and models
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Order, OrderItem, MenuItem, Category, Table, Payment
from models.payment_gateway import PaymentGateway, PaymentTransaction
from models.payment import Payment as EnhancedPayment
from utils.payment_gateways.razorpay import RazorpayGateway
from utils.payment_gateways.stripe import StripeGateway
from utils.payment_gateways.processor import PaymentProcessor
from utils.payment_gateways.exceptions import PaymentGatewayError, WebhookVerificationError
from utils.payment_security import PaymentSecurityManager

class PaymentGatewayTestCase(unittest.TestCase):
    """Test case for payment gateway integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test user
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            mobile='+919876543210',
            role='admin'
        )
        self.test_user.set_password('testpass123')
        db.session.add(self.test_user)
        
        # Create test data
        self.create_test_data()
        db.session.commit()
        
        # Initialize payment processor
        self.processor = PaymentProcessor()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def create_test_data(self):
        """Create test menu items, categories, and tables"""
        # Create test category
        self.test_category = Category(
            name='Test Category',
            description='Test category for payment testing',
            is_active=True
        )
        db.session.add(self.test_category)
        db.session.flush()
        
        # Create test menu items
        self.test_menu_item1 = MenuItem(
            name='Test Item 1',
            description='Test menu item 1',
            price=Decimal('100.00'),
            category_id=self.test_category.id,
            stock_quantity=50,
            is_active=True,
            is_available=True
        )
        
        self.test_menu_item2 = MenuItem(
            name='Test Item 2',
            description='Test menu item 2',
            price=Decimal('200.00'),
            category_id=self.test_category.id,
            stock_quantity=30,
            is_active=True,
            is_available=True
        )
        
        db.session.add(self.test_menu_item1)
        db.session.add(self.test_menu_item2)
        db.session.flush()
        
        # Create test table
        self.test_table = Table(
            table_number='T001',
            capacity=4,
            location='Main Hall',
            is_active=True
        )
        db.session.add(self.test_table)
        db.session.flush()
        
        # Create test order
        self.test_order = Order(
            order_number='TEST001',
            table_id=self.test_table.id,
            customer_name='Test Customer',
            customer_mobile='+919876543210',
            order_type='Dine-in',
            created_by=self.test_user.id
        )
        db.session.add(self.test_order)
        db.session.flush()
        
        # Add items to order
        self.test_order_item1 = OrderItem(
            order_id=self.test_order.id,
            menu_item_id=self.test_menu_item1.id,
            quantity=2,
            price=self.test_menu_item1.price,
            status='Pending'
        )
        
        self.test_order_item2 = OrderItem(
            order_id=self.test_order.id,
            menu_item_id=self.test_menu_item2.id,
            quantity=1,
            price=self.test_menu_item2.price,
            status='Pending'
        )
        
        db.session.add(self.test_order_item1)
        db.session.add(self.test_order_item2)
        db.session.flush()
        
        # Calculate order totals
        self.test_order.calculate_totals()
        db.session.commit()


class TestPaymentGatewayModels(PaymentGatewayTestCase):
    """Test payment gateway database models"""
    
    def test_payment_gateway_creation(self):
        """Test creating a payment gateway"""
        gateway = PaymentGateway(
            name='test_gateway',
            display_name='Test Gateway',
            is_enabled=True,
            is_test_mode=True
        )
        
        gateway.api_key = 'test_api_key'
        gateway.secret_key = 'test_secret_key'
        gateway.webhook_secret = 'test_webhook_secret'
        gateway.set_supported_currencies(['INR', 'USD'])
        gateway.set_supported_payment_methods(['card', 'upi'])
        
        db.session.add(gateway)
        db.session.commit()
        
        # Verify gateway was created
        saved_gateway = PaymentGateway.query.filter_by(name='test_gateway').first()
        self.assertIsNotNone(saved_gateway)
        self.assertEqual(saved_gateway.display_name, 'Test Gateway')
        self.assertTrue(saved_gateway.is_enabled)
        self.assertTrue(saved_gateway.is_test_mode)
        self.assertEqual(saved_gateway.get_supported_currencies(), ['INR', 'USD'])
        self.assertEqual(saved_gateway.get_supported_payment_methods(), ['card', 'upi'])
        
        # Test fee calculation
        fee = saved_gateway.calculate_transaction_fee(Decimal('100.00'))
        self.assertEqual(fee, Decimal('2.90'))  # 2.9% of 100 + 0 fixed fee
    
    def test_payment_gateway_transaction_limits(self):
        """Test transaction limit checking"""
        gateway = PaymentGateway(
            name='limited_gateway',
            display_name='Limited Gateway',
            min_amount=Decimal('10.00'),
            max_amount=Decimal('1000.00'),
            daily_transaction_limit=Decimal('5000.00')
        )
        db.session.add(gateway)
        db.session.commit()
        
        # Test minimum amount check
        is_valid, message = gateway.check_transaction_limits(Decimal('5.00'))
        self.assertFalse(is_valid)
        self.assertIn('minimum', message.lower())
        
        # Test maximum amount check
        is_valid, message = gateway.check_transaction_limits(Decimal('1500.00'))
        self.assertFalse(is_valid)
        self.assertIn('maximum', message.lower())
        
        # Test valid amount
        is_valid, message = gateway.check_transaction_limits(Decimal('100.00'))
        self.assertTrue(is_valid)
        
        # Test daily limit
        gateway.total_amount_today = Decimal('4500.00')
        is_valid, message = gateway.check_transaction_limits(Decimal('600.00'))
        self.assertFalse(is_valid)
        self.assertIn('daily', message.lower())
    
    def test_payment_transaction_creation(self):
        """Test creating payment transactions"""
        # Create gateway first
        gateway = PaymentGateway(
            name='test_txn_gateway',
            display_name='Test Transaction Gateway'
        )
        db.session.add(gateway)
        db.session.flush()
        
        # Create payment
        payment = EnhancedPayment.create_payment(
            order_id=self.test_order.id,
            payment_mode='Test Gateway',
            amount=Decimal('500.00'),
            processed_by=self.test_user.id,
            gateway_id=gateway.id
        )
        
        # Create transaction
        transaction = PaymentTransaction.create_transaction(
            payment_id=payment.id,
            gateway_id=gateway.id,
            amount=Decimal('500.00'),
            currency='INR'
        )
        
        db.session.commit()
        
        # Verify transaction
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('500.00'))
        self.assertEqual(transaction.currency, 'INR')
        self.assertEqual(transaction.status, 'pending')
        self.assertFalse(transaction.is_succeeded)
        self.assertTrue(transaction.is_pending)
        
        # Test status updates
        transaction.mark_succeeded()
        self.assertTrue(transaction.is_succeeded)
        self.assertIsNotNone(transaction.completed_at)
        
        # Test failure
        transaction.mark_failed(error_code='TEST_ERROR', error_message='Test error')
        self.assertTrue(transaction.is_failed)
        self.assertEqual(transaction.error_code, 'TEST_ERROR')
    
    def test_payment_transaction_retry_logic(self):
        """Test payment transaction retry functionality"""
        gateway = PaymentGateway(name='retry_gateway', display_name='Retry Gateway')
        db.session.add(gateway)
        db.session.flush()
        
        payment = EnhancedPayment.create_payment(
            order_id=self.test_order.id,
            payment_mode='Retry Gateway',
            amount=Decimal('100.00'),
            gateway_id=gateway.id,
            processed_by=self.test_user.id
        )
        
        # Create initial transaction
        transaction = PaymentTransaction.create_transaction(
            payment_id=payment.id,
            gateway_id=gateway.id,
            amount=Decimal('100.00')
        )
        
        # Mark as failed to test retry
        transaction.mark_failed(error_code='NETWORK_ERROR')
        
        # Test retry
        retry_transaction = transaction.retry()
        self.assertIsNotNone(retry_transaction)
        self.assertEqual(retry_transaction.retry_count, 1)
        self.assertEqual(retry_transaction.parent_transaction_id, transaction.id)
        
        # Test retry limit
        for i in range(3):  # max_retries is 3
            retry_transaction = retry_transaction.retry()
        
        # Should not allow more retries
        self.assertIsNone(transaction.retry())


class TestRazorpayGateway(PaymentGatewayTestCase):
    """Test Razorpay gateway integration"""
    
    def setUp(self):
        super().setUp()
        self.create_razorpay_gateway()
    
    def create_razorpay_gateway(self):
        """Create test Razorpay gateway"""
        self.razorpay_gateway = PaymentGateway(
            name='razorpay',
            display_name='Razorpay',
            is_enabled=True,
            is_test_mode=True
        )
        
        # Use test credentials
        self.razorpay_gateway.api_key = 'rzp_test_1234567890'
        self.razorpay_gateway.secret_key = 'test_secret_key'
        self.razorpay_gateway.webhook_secret = 'test_webhook_secret'
        
        db.session.add(self.razorpay_gateway)
        db.session.commit()
    
    @patch('razorpay.Client')
    def test_razorpay_client_initialization(self, mock_razorpay_client):
        """Test Razorpay client initialization"""
        mock_client = Mock()
        mock_razorpay_client.return_value = mock_client
        
        gateway = RazorpayGateway(self.razorpay_gateway)
        
        # Verify client was created with correct auth
        mock_razorpay_client.assert_called_once_with(
            auth=('rzp_test_1234567890', 'test_secret_key')
        )
        self.assertEqual(gateway.client, mock_client)
    
    @patch('razorpay.Client')
    def test_create_razorpay_order(self, mock_razorpay_client):
        """Test creating Razorpay order"""
        mock_client = Mock()
        mock_razorpay_client.return_value = mock_client
        
        # Mock order creation response
        mock_client.order.create.return_value = {
            'id': 'order_test123456',
            'amount': 50000,  # Amount in paise
            'currency': 'INR',
            'amount_due': 50000,
            'amount_paid': 0,
            'status': 'created',
            'receipt': 'receipt_test',
            'created_at': int(time.time()),
            'notes': {}
        }
        
        gateway = RazorpayGateway(self.razorpay_gateway)
        order_response = gateway.create_order(
            amount=Decimal('500.00'),
            currency='INR',
            receipt='receipt_test',
            notes={'test': 'note'}
        )
        
        # Verify order creation
        self.assertEqual(order_response['order_id'], 'order_test123456')
        self.assertEqual(order_response['amount'], 50000)
        self.assertEqual(order_response['currency'], 'INR')
        
        # Verify API call was made
        mock_client.order.create.assert_called_once()
        call_args = mock_client.order.create.call_args[1]['data']
        self.assertEqual(call_args['amount'], 50000)
        self.assertEqual(call_args['currency'], 'INR')
        self.assertEqual(call_args['receipt'], 'receipt_test')
    
    @patch('razorpay.Client')
    def test_razorpay_payment_capture(self, mock_razorpay_client):
        """Test capturing Razorpay payment"""
        mock_client = Mock()
        mock_razorpay_client.return_value = mock_client
        
        # Mock payment capture response
        mock_client.payment.capture.return_value = {
            'id': 'pay_test123456',
            'amount': 50000,
            'currency': 'INR',
            'status': 'captured',
            'method': 'card',
            'created_at': int(time.time()),
            'description': 'Test payment',
            'card': {'id': 'card_test123'},
            'bank': 'HDFC',
            'wallet': None,
            'vpa': None,
            'email': 'test@example.com',
            'contact': '+919876543210',
            'customer_id': 'cust_test123',
            'order_id': 'order_test123456'
        }
        
        gateway = RazorpayGateway(self.razorpay_gateway)
        capture_response = gateway.capture_payment('pay_test123456')
        
        # Verify capture response
        self.assertEqual(capture_response['payment_id'], 'pay_test123456')
        self.assertEqual(capture_response['amount'], Decimal('500.00'))
        self.assertEqual(capture_response['currency'], 'INR')
        self.assertEqual(capture_response['status'], 'captured')
        self.assertEqual(capture_response['method'], 'card')
    
    def test_razorpay_webhook_verification(self):
        """Test Razorpay webhook signature verification"""
        gateway = RazorpayGateway(self.razorpay_gateway)
        
        payload = '{"event": "payment.captured", "payload": {"payment": {"id": "pay_test123"}}}'
        signature = 'test_signature'
        
        # Mock the verification to pass
        with patch('hmac.compare_digest', return_value=True):
            result = gateway.verify_webhook_signature(payload, signature)
            self.assertTrue(result)
        
        # Test with invalid signature
        with patch('hmac.compare_digest', return_value=False):
            with self.assertRaises(WebhookVerificationError):
                gateway.verify_webhook_signature(payload, signature)
    
    @patch('razorpay.Client')
    def test_razorpay_webhook_processing(self, mock_razorpay_client):
        """Test processing Razorpay webhook events"""
        mock_client = Mock()
        mock_razorpay_client.return_value = mock_client
        
        gateway = RazorpayGateway(self.razorpay_gateway)
        
        # Test payment captured event
        webhook_data = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'id': 'pay_test123',
                    'amount': 50000,
                    'currency': 'INR',
                    'status': 'captured',
                    'method': 'card',
                    'created_at': int(time.time()),
                    'order_id': 'order_test123',
                    'customer_id': 'cust_test123'
                }
            }
        }
        
        processed = gateway.process_webhook(webhook_data)
        
        self.assertEqual(processed['event'], 'payment.captured')
        self.assertEqual(processed['payment_id'], 'pay_test123')
        self.assertEqual(processed['status'], 'captured')
        self.assertEqual(processed['amount'], Decimal('500.00'))
        
        # Test payment failed event
        webhook_data['event'] = 'payment.failed'
        webhook_data['payload']['payment']['status'] = 'failed'
        webhook_data['payload']['payment']['error_code'] = 'BAD_REQUEST_ERROR'
        webhook_data['payload']['payment']['error_description'] = 'Invalid request'
        
        processed = gateway.process_webhook(webhook_data)
        
        self.assertEqual(processed['event'], 'payment.failed')
        self.assertEqual(processed['status'], 'failed')
        self.assertEqual(processed['error_code'], 'BAD_REQUEST_ERROR')


class TestStripeGateway(PaymentGatewayTestCase):
    """Test Stripe gateway integration"""
    
    def setUp(self):
        super().setUp()
        self.create_stripe_gateway()
    
    def create_stripe_gateway(self):
        """Create test Stripe gateway"""
        self.stripe_gateway = PaymentGateway(
            name='stripe',
            display_name='Stripe',
            is_enabled=True,
            is_test_mode=True
        )
        
        # Use test credentials
        self.stripe_gateway.api_key = 'sk_test_1234567890'
        db.session.add(self.stripe_gateway)
        db.session.commit()
    
    @patch('stripe.api_key', 'sk_test_1234567890')
    @patch('stripe.PaymentIntent')
    def test_stripe_payment_intent_creation(self, mock_payment_intent):
        """Test creating Stripe payment intent"""
        # Mock payment intent creation
        mock_intent = Mock()
        mock_intent.id = 'pi_test123456'
        mock_intent.client_secret = 'pi_test123456_secret_test'
        mock_intent.amount = 50000
        mock_intent.currency = 'inr'
        mock_intent.status = 'requires_payment_method'
        mock_intent.created = int(time.time())
        mock_intent.capture_method = 'automatic'
        mock_intent.metadata = {}
        mock_payment_intent.create.return_value = mock_intent
        
        gateway = StripeGateway(self.stripe_gateway)
        intent_response = gateway.create_payment_intent(
            amount=Decimal('500.00'),
            currency='inr',
            metadata={'order_id': '123'}
        )
        
        # Verify payment intent creation
        self.assertEqual(intent_response['payment_intent_id'], 'pi_test123456')
        self.assertEqual(intent_response['client_secret'], 'pi_test123456_secret_test')
        self.assertEqual(intent_response['amount'], 50000)
        self.assertEqual(intent_response['currency'], 'inr')
        
        # Verify API call was made
        mock_payment_intent.create.assert_called_once()
        call_args = mock_payment_intent.create.call_args[1]
        self.assertEqual(call_args['amount'], 50000)
        self.assertEqual(call_args['currency'], 'inr')
    
    @patch('stripe.api_key', 'sk_test_1234567890')
    @patch('stripe.PaymentIntent')
    def test_stripe_payment_confirmation(self, mock_payment_intent):
        """Test confirming Stripe payment intent"""
        # Mock payment confirmation
        mock_intent = Mock()
        mock_intent.id = 'pi_test123456'
        mock_intent.status = 'succeeded'
        mock_intent.amount = 50000
        mock_intent.currency = 'inr'
        mock_intent.payment_method = 'pm_test123'
        mock_intent.created = int(time.time())
        mock_intent.next_action = None
        mock_intent.charges = {'data': []}
        mock_intent.metadata = {}
        mock_payment_intent.confirm.return_value = mock_intent
        
        gateway = StripeGateway(self.stripe_gateway)
        confirm_response = gateway.confirm_payment_intent(
            'pi_test123456',
            payment_method_id='pm_test123'
        )
        
        # Verify confirmation response
        self.assertEqual(confirm_response['payment_intent_id'], 'pi_test123456')
        self.assertEqual(confirm_response['status'], 'succeeded')
        self.assertEqual(confirm_response['amount'], 50000)
    
    @patch('stripe.api_key', 'sk_test_1234567890')
    @patch('stripe.Refund')
    def test_stripe_refund_creation(self, mock_refund):
        """Test creating Stripe refund"""
        # Mock refund creation
        mock_refund_obj = Mock()
        mock_refund_obj.id = 're_test123456'
        mock_refund_obj.payment_intent = 'pi_test123456'
        mock_refund_obj.amount = 25000
        mock_refund_obj.currency = 'inr'
        mock_refund_obj.status = 'succeeded'
        mock_refund_obj.reason = 'requested_by_customer'
        mock_refund_obj.created = int(time.time())
        mock_refund_obj.metadata = {}
        mock_refund.create.return_value = mock_refund_obj
        
        gateway = StripeGateway(self.stripe_gateway)
        refund_response = gateway.create_refund(
            payment_intent_id='pi_test123456',
            amount=Decimal('250.00'),
            reason='requested_by_customer'
        )
        
        # Verify refund response
        self.assertEqual(refund_response['refund_id'], 're_test123456')
        self.assertEqual(refund_response['payment_intent_id'], 'pi_test123456')
        self.assertEqual(refund_response['amount'], Decimal('250.00'))
        self.assertEqual(refund_response['status'], 'succeeded')
    
    def test_stripe_webhook_verification(self):
        """Test Stripe webhook signature verification"""
        gateway = StripeGateway(self.stripe_gateway)
        
        payload = '{"type": "payment_intent.succeeded", "data": {"object": {}}}'
        signature = 'v1=test_signature,t=1234567890'
        timestamp = 1234567890
        
        # Mock successful verification
        with patch('hmac.compare_digest', return_value=True):
            with patch('json.loads', return_value=json.loads(payload)):
                result = gateway.verify_webhook_signature(payload, signature, timestamp)
                self.assertEqual(result, json.loads(payload))
        
        # Test with invalid signature
        with patch('hmac.compare_digest', return_value=False):
            with self.assertRaises(WebhookVerificationError):
                gateway.verify_webhook_signature(payload, signature, timestamp)
    
    @patch('stripe.api_key', 'sk_test_1234567890')
    def test_stripe_webhook_processing(self, mock_stripe):
        """Test processing Stripe webhook events"""
        gateway = StripeGateway(self.stripe_gateway)
        
        # Test payment intent succeeded event
        webhook_data = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_test123456',
                    'amount': 50000,
                    'currency': 'inr',
                    'status': 'succeeded',
                    'payment_method': 'pm_test123',
                    'created': int(time.time()),
                    'charges': {'data': []},
                    'metadata': {'order_id': '123'}
                }
            }
        }
        
        processed = gateway.process_webhook(webhook_data)
        
        self.assertEqual(processed['event'], 'payment_intent.succeeded')
        self.assertEqual(processed['payment_intent_id'], 'pi_test123456')
        self.assertEqual(processed['status'], 'succeeded')
        self.assertEqual(processed['amount'], Decimal('500.00'))
        
        # Test payment intent failed event
        webhook_data['type'] = 'payment_intent.payment_failed'
        webhook_data['data']['object']['status'] = 'payment_failed'
        webhook_data['data']['object']['last_payment_error'] = {
            'code': 'card_declined',
            'message': 'Your card was declined.',
            'type': 'card_error'
        }
        
        processed = gateway.process_webhook(webhook_data)
        
        self.assertEqual(processed['event'], 'payment_intent.payment_failed')
        self.assertEqual(processed['status'], 'failed')
        self.assertEqual(processed['error_code'], 'card_declined')


class TestPaymentProcessor(PaymentGatewayTestCase):
    """Test unified payment processor"""
    
    def setUp(self):
        super().setUp()
        self.create_test_gateways()
    
    def create_test_gateways(self):
        """Create test payment gateways"""
        self.razorpay_gateway = PaymentGateway(
            name='razorpay',
            display_name='Razorpay',
            is_enabled=True,
            is_test_mode=True
        )
        self.razorpay_gateway.api_key = 'rzp_test_123'
        self.razorpay_gateway.secret_key = 'secret_123'
        self.razorpay_gateway.webhook_secret = 'webhook_123'
        
        self.stripe_gateway = PaymentGateway(
            name='stripe',
            display_name='Stripe',
            is_enabled=True,
            is_test_mode=True
        )
        self.stripe_gateway.api_key = 'sk_test_123'
        
        db.session.add(self.razorpay_gateway)
        db.session.add(self.stripe_gateway)
        db.session.commit()
    
    def test_processor_initialization(self):
        """Test payment processor initialization"""
        processor = PaymentProcessor()
        
        # Should load both gateways
        self.assertIn('razorpay', processor.gateways)
        self.assertIn('stripe', processor.gateways)
        
        # Check gateway types
        self.assertIsInstance(processor.gateways['razorpay'], RazorpayGateway)
        self.assertIsInstance(processor.gateways['stripe'], StripeGateway)
    
    def test_get_available_gateways(self):
        """Test getting available gateways"""
        gateways = self.processor.get_available_gateways()
        
        self.assertEqual(len(gateways), 2)
        
        razorpay_info = next(g for g in gateways if g['name'] == 'razorpay')
        self.assertEqual(razorpay_info['display_name'], 'Razorpay')
        self.assertTrue(razorpay_info['is_test_mode'])
        self.assertIn('INR', razorpay_info['supported_currencies'])
        
        stripe_info = next(g for g in gateways if g['name'] == 'stripe')
        self.assertEqual(stripe_info['display_name'], 'Stripe')
        self.assertTrue(stripe_info['is_test_mode'])
    
    @patch('utils.payment_gateways.razorpay.RazorpayGateway.create_order')
    def test_process_razorpay_payment(self, mock_create_order):
        """Test processing Razorpay payment"""
        # Mock Razorpay order creation
        mock_create_order.return_value = {
            'order_id': 'order_test123',
            'amount': 50000,
            'currency': 'INR',
            'amount_due': 50000,
            'amount_paid': 0,
            'status': 'created',
            'receipt': 'receipt_test',
            'created_at': int(time.time()),
            'notes': {}
        }
        
        # Process payment
        result = self.processor.process_payment(
            order_id=self.test_order.id,
            gateway_name='razorpay',
            processed_by=self.test_user.id
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['gateway'], 'razorpay')
        self.assertEqual(result['order_id'], 'order_test123')
        self.assertEqual(result['amount'], float(self.test_order.grand_total))
        
        # Verify payment record was created
        payment = EnhancedPayment.query.filter_by(order_id=self.test_order.id).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.gateway_id, self.razorpay_gateway.id)
        self.assertEqual(payment.status, 'Pending')
        
        # Verify transaction record was created
        transaction = PaymentTransaction.query.filter_by(payment_id=payment.id).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.status, 'pending')
    
    @patch('utils.payment_gateways.stripe.StripeGateway.create_payment_intent')
    def test_process_stripe_payment(self, mock_create_intent):
        """Test processing Stripe payment"""
        # Mock Stripe payment intent creation
        mock_intent = Mock()
        mock_intent.id = 'pi_test123'
        mock_intent.client_secret = 'pi_test123_secret'
        mock_intent.amount = 50000
        mock_intent.currency = 'inr'
        mock_intent.status = 'requires_payment_method'
        mock_intent.created = int(time.time())
        mock_intent.capture_method = 'automatic'
        mock_intent.metadata = {}
        mock_create_intent.return_value = {
            'payment_intent_id': 'pi_test123',
            'client_secret': 'pi_test123_secret',
            'amount': 50000,
            'currency': 'inr',
            'status': 'requires_payment_method',
            'created': int(time.time()),
            'capture_method': 'automatic',
            'metadata': {}
        }
        
        # Process payment
        result = self.processor.process_payment(
            order_id=self.test_order.id,
            gateway_name='stripe',
            processed_by=self.test_user.id
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['gateway'], 'stripe')
        self.assertEqual(result['payment_intent_id'], 'pi_test123')
        self.assertEqual(result['client_secret'], 'pi_test123_secret')
    
    def test_get_payment_status(self):
        """Test getting payment status"""
        # Create a test payment
        payment = EnhancedPayment.create_payment(
            order_id=self.test_order.id,
            payment_mode='Test Gateway',
            amount=Decimal('500.00'),
            processed_by=self.test_user.id
        )
        
        status = self.processor.get_payment_status(payment.id)
        
        self.assertEqual(status['payment_id'], payment.id)
        self.assertEqual(status['order_id'], self.test_order.id)
        self.assertEqual(status['order_number'], self.test_order.order_number)
        self.assertEqual(status['amount'], 500.00)
        self.assertEqual(status['status'], 'Pending')


class TestPaymentSecurity(PaymentGatewayTestCase):
    """Test payment security features"""
    
    def test_security_manager_initialization(self):
        """Test security manager initialization"""
        security_manager = PaymentSecurityManager()
        self.assertIsNotNone(security_manager)
    
    def test_secure_token_generation(self):
        """Test secure token generation"""
        security_manager = PaymentSecurityManager()
        token1 = security_manager.generate_secure_token()
        token2 = security_manager.generate_secure_token()
        
        # Tokens should be different
        self.assertNotEqual(token1, token2)
        
        # Tokens should be of expected length
        self.assertGreater(len(token1), 20)
    
    def test_sensitive_data_masking(self):
        """Test masking of sensitive data"""
        security_manager = PaymentSecurityManager()
        
        # Test card number masking
        masked_card = security_manager.mask_sensitive_data('card_number', '1234567890123456')
        self.assertEqual(masked_card, '************3456')
        
        # Test CVV masking
        masked_cvv = security_manager.mask_sensitive_data('cvv', '123')
        self.assertEqual(masked_cvv, '***')
        
        # Test email masking
        masked_email = security_manager.mask_sensitive_data('email', 'john.doe@example.com')
        self.assertEqual(masked_email, 'jo**********@example.com')
        
        # Test mobile masking
        masked_mobile = security_manager.mask_sensitive_data('mobile', '+919876543210')
        self.assertEqual(masked_mobile, '+919876543**')
    
    def test_card_number_validation(self):
        """Test credit card number validation using Luhn algorithm"""
        security_manager = PaymentSecurityManager()
        
        # Test valid card numbers
        valid_cards = [
            '4532015112830366',  # Visa
            '5555555555554444',  # Mastercard
            '378282246310005',   # American Express
        ]
        
        for card in valid_cards:
            self.assertTrue(security_manager.validate_card_number(card))
        
        # Test invalid card numbers
        invalid_cards = [
            '1234567890123456',  # Fails Luhn check
            '123',               # Too short
            '4532015112830367',  # Wrong check digit
        ]
        
        for card in invalid_cards:
            self.assertFalse(security_manager.validate_card_number(card))
    
    def test_amount_validation(self):
        """Test payment amount validation"""
        security_manager = PaymentSecurityManager()
        
        # Test valid amounts
        is_valid, message = security_manager.validate_amount('100.00')
        self.assertTrue(is_valid)
        self.assertEqual(message, 'Valid amount')
        
        is_valid, message = security_manager.validate_amount('0.01')
        self.assertTrue(is_valid)
        
        # Test invalid amounts
        is_valid, message = security_manager.validate_amount('-10.00')
        self.assertFalse(is_valid)
        self.assertIn('positive', message.lower())
        
        is_valid, message = security_manager.validate_amount('0')
        self.assertFalse(is_valid)
        
        is_valid, message = security_manager.validate_amount('1000000.00')
        self.assertFalse(is_valid)
        self.assertIn('maximum', message.lower())
    
    def test_currency_validation(self):
        """Test currency code validation"""
        security_manager = PaymentSecurityManager()
        
        # Test valid currencies
        self.assertTrue(security_manager.validate_currency('INR'))
        self.assertTrue(security_manager.validate_currency('USD'))
        self.assertTrue(security_manager.validate_currency('EUR'))
        
        # Test invalid currencies
        self.assertFalse(security_manager.validate_currency('XYZ'))
        self.assertFalse(security_manager.validate_currency(''))
    
    def test_log_sanitization(self):
        """Test log data sanitization"""
        security_manager = PaymentSecurityManager()
        
        sensitive_data = {
            'order_id': 123,
            'card_number': '4532015112830366',
            'cvv': '123',
            'api_key': 'sk_test_1234567890',
            'customer_info': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'mobile': '+919876543210'
            }
        }
        
        sanitized = security_manager.sanitize_log_data(sensitive_data)
        
        # Sensitive fields should be redacted
        self.assertEqual(sanitized['card_number'], '[REDACTED]')
        self.assertEqual(sanitized['cvv'], '[REDACTED]')
        self.assertEqual(sanitized['api_key'], '[REDACTED]')
        
        # Non-sensitive fields should remain
        self.assertEqual(sanitized['order_id'], 123)
        self.assertEqual(sanitized['customer_info']['name'], 'John Doe')


class TestPaymentFlowIntegration(PaymentGatewayTestCase):
    """Test end-to-end payment flows"""
    
    def setUp(self):
        super().setUp()
        self.create_test_gateways()
    
    def create_test_gateways(self):
        """Create test payment gateways"""
        self.razorpay_gateway = PaymentGateway(
            name='razorpay',
            display_name='Razorpay',
            is_enabled=True,
            is_test_mode=True
        )
        self.razorpay_gateway.api_key = 'rzp_test_123'
        self.razorpay_gateway.secret_key = 'secret_123'
        self.razorpay_gateway.webhook_secret = 'webhook_123'
        
        db.session.add(self.razorpay_gateway)
        db.session.commit()
    
    @patch('utils.payment_gateways.razorpay.RazorpayGateway.create_order')
    @patch('utils.payment_gateways.razorpay.RazorpayGateway.get_payment_details')
    def test_complete_razorpay_payment_flow(self, mock_get_payment, mock_create_order):
        """Test complete Razorpay payment flow"""
        # Mock order creation
        mock_create_order.return_value = {
            'order_id': 'order_test123',
            'amount': 50000,
            'currency': 'INR',
            'status': 'created'
        }
        
        # Mock payment confirmation
        mock_get_payment.return_value = {
            'id': 'pay_test123',
            'amount': 50000,
            'currency': 'INR',
            'status': 'captured',
            'method': 'card',
            'created_at': int(time.time())
        }
        
        # Step 1: Process payment
        process_result = self.processor.process_payment(
            order_id=self.test_order.id,
            gateway_name='razorpay',
            processed_by=self.test_user.id
        )
        
        self.assertTrue(process_result['success'])
        payment_id = process_result['payment_id']
        
        # Step 2: Confirm payment
        confirm_result = self.processor.confirm_payment(
            payment_id=payment_id,
            razorpay_payment_id='pay_test123'
        )
        
        self.assertTrue(confirm_result['success'])
        self.assertEqual(confirm_result['status'], 'completed')
        
        # Verify payment status
        payment = EnhancedPayment.get_by_id(payment_id)
        self.assertEqual(payment.status, 'Completed')
        self.assertEqual(payment.gateway_transaction_id, 'pay_test123')
        
        # Verify order status (should remain as is for manual completion)
        order = Order.get_by_id(self.test_order.id)
        self.assertEqual(order.status, 'New')  # Order status updated separately
    
    @patch('utils.payment_gateways.processor.payment_processor')
    def test_webhook_processing_flow(self, mock_processor):
        """Test webhook processing flow"""
        # Mock webhook processing
        mock_processor.process_webhook.return_value = {
            'success': True,
            'message': 'Payment webhook processed successfully',
            'payment_id': 1,
            'transaction_id': 1
        }
        
        # Simulate webhook data
        webhook_data = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'id': 'pay_test123',
                    'amount': 50000,
                    'currency': 'INR',
                    'status': 'captured'
                }
            }
        }
        
        # Process webhook
        result = mock_processor.process_webhook(
            gateway_name='razorpay',
            payload=json.dumps(webhook_data),
            signature='test_signature'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('payment_id', result)
        
        # Verify webhook processing was called
        mock_processor.process_webhook.assert_called_once()


class TestPaymentRoutes(PaymentGatewayTestCase):
    """Test payment routes and endpoints"""
    
    def setUp(self):
        super().setUp()
        self.create_test_gateways()
        self.client = self.app.test_client()
        
        # Login as test user
        with self.client.session_transaction() as sess:
            sess['_user_id'] = self.test_user.id
            sess['_fresh'] = True
    
    def create_test_gateways(self):
        """Create test payment gateways"""
        self.razorpay_gateway = PaymentGateway(
            name='razorpay',
            display_name='Razorpay',
            is_enabled=True,
            is_test_mode=True
        )
        db.session.add(self.razorpay_gateway)
        db.session.commit()
    
    def test_payment_methods_endpoint(self):
        """Test payment methods API endpoint"""
        response = self.client.get('/payment/methods')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('gateways', data)
        self.assertIn('total_gateways', data)
    
    def test_payment_status_endpoint(self):
        """Test payment status API endpoint"""
        # Create test payment
        payment = EnhancedPayment.create_payment(
            order_id=self.test_order.id,
            payment_mode='Test Gateway',
            amount=Decimal('100.00'),
            processed_by=self.test_user.id
        )
        
        response = self.client.get(f'/payment/status/{payment.id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('status', data)
        self.assertEqual(data['status']['payment_id'], payment.id)
    
    def test_transactions_list_endpoint(self):
        """Test transactions list API endpoint"""
        response = self.client.get('/payment/transactions')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('transactions', data)
        self.assertIn('pagination', data)
    
    def test_payment_analytics_endpoint(self):
        """Test payment analytics API endpoint"""
        response = self.client.get('/payment/analytics')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('analytics', data)
        
        analytics = data['analytics']
        self.assertIn('total_payments', analytics)
        self.assertIn('total_amount', analytics)
        self.assertIn('success_rate', analytics)


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(TestPaymentGatewayModels))
    suite.addTest(unittest.makeSuite(TestRazorpayGateway))
    suite.addTest(unittest.makeSuite(TestStripeGateway))
    suite.addTest(unittest.makeSuite(TestPaymentProcessor))
    suite.addTest(unittest.makeSuite(TestPaymentSecurity))
    suite.addTest(unittest.makeSuite(TestPaymentFlowIntegration))
    suite.addTest(unittest.makeSuite(TestPaymentRoutes))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("PAYMENT GATEWAY INTEGRATION TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ All payment gateway integration tests passed!")
    else:
        print("❌ Some tests failed:")
        
        if result.failures:
            print("\nFAILURES:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
        
        if result.errors:
            print("\nERRORS:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")