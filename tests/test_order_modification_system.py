"""
Comprehensive Test Suite for Order Modification System
Tests all modification scenarios and workflows
"""

import unittest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Flask
from flask_testing import TestCase
from flask_login import current_user

from models import db, create_tables
from models.user import User
from models.order import Order, OrderItem
from models.menu_item import MenuItem, Category
from models.table import Table
from models.order_modification import OrderModification, OrderItemModification, ModificationRequest
from utils.order_modification_workflow import (
    ModificationWorkflowManager, ModificationCalculator, ModificationValidator,
    create_addition_modification, create_removal_modification, create_quantity_modification
)
from utils.payment_integration import ModificationPaymentManager
from utils.websocket_integration import ModificationWebSocketManager


class OrderModificationTestCase(TestCase):
    """Base test case for order modification system"""
    
    def create_app(self):
        """Create test Flask application"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['WTF_CSRF_ENABLED'] = False
        
        # Initialize extensions
        db.init_app(app)
        
        return app
    
    def setUp(self):
        """Set up test database and data"""
        db.create_all()
        
        # Create test users
        self.admin_user = User(username='admin', role='admin', email='admin@test.com')
        self.admin_user.set_password('admin123')
        
        self.manager_user = User(username='manager', role='manager', email='manager@test.com')
        self.manager_user.set_password('manager123')
        
        self.chef_user = User(username='chef', role='chef', email='chef@test.com')
        self.chef_user.set_password('chef123')
        
        self.cashier_user = User(username='cashier', role='cashier', email='cashier@test.com')
        self.cashier_user.set_password('cashier123')
        
        db.session.add_all([self.admin_user, self.manager_user, self.chef_user, self.cashier_user])
        db.session.commit()
        
        # Create test category and menu items
        self.category = Category(name='Test Category', description='Test category description')
        db.session.add(self.category)
        db.session.flush()
        
        self.menu_item1 = MenuItem(
            name='Test Pizza',
            description='Test pizza description',
            price=Decimal('250.00'),
            category_id=self.category.id,
            is_active=True,
            is_available=True,
            stock_quantity=100
        )
        
        self.menu_item2 = MenuItem(
            name='Test Burger',
            description='Test burger description',
            price=Decimal('150.00'),
            category_id=self.category.id,
            is_active=True,
            is_available=True,
            stock_quantity=50
        )
        
        self.menu_item3 = MenuItem(
            name='Test Pasta',
            description='Test pasta description',
            price=Decimal('200.00'),
            category_id=self.category.id,
            is_active=True,
            is_available=True,
            stock_quantity=30
        )
        
        db.session.add_all([self.menu_item1, self.menu_item2, self.menu_item3])
        db.session.flush()
        
        # Create test table
        self.table = Table(table_number='1', capacity=4, status='Available')
        db.session.add(self.table)
        db.session.flush()
        
        # Create test order
        self.order = Order(
            order_number='ORD-TEST-001',
            table_id=self.table.id,
            customer_name='Test Customer',
            order_type='Dine-in',
            status='New',
            created_by=self.cashier_user.id
        )
        db.session.add(self.order)
        db.session.flush()
        
        # Create order items
        self.order_item1 = OrderItem(
            order_id=self.order.id,
            menu_item_id=self.menu_item1.id,
            quantity=2,
            price=self.menu_item1.price,
            status='Pending'
        )
        
        self.order_item2 = OrderItem(
            order_id=self.order.id,
            menu_item_id=self.menu_item2.id,
            quantity=1,
            price=self.menu_item2.price,
            status='Pending'
        )
        
        db.session.add_all([self.order_item1, self.order_item2])
        self.order.calculate_totals()
        db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()


class TestModificationModels(OrderModificationTestCase):
    """Test order modification models"""
    
    def test_order_modification_creation(self):
        """Test OrderModification model creation"""
        modification = OrderModification(
            order_id=self.order.id,
            modification_type='add_items',
            requested_by_user_id=self.cashier_user.id,
            reason='Customer wants to add more items'
        )
        
        db.session.add(modification)
        db.session.commit()
        
        self.assertIsNotNone(modification.id)
        self.assertIsNotNone(modification.modification_id)
        self.assertEqual(modification.order_id, self.order.id)
        self.assertEqual(modification.modification_type, 'add_items')
        self.assertEqual(modification.status, 'Pending')
        self.assertEqual(modification.requested_by_user_id, self.cashier_user.id)
    
    def test_order_modification_approval_workflow(self):
        """Test modification approval workflow"""
        modification = OrderModification(
            order_id=self.order.id,
            modification_type='add_items',
            requested_by_user_id=self.cashier_user.id,
            reason='Customer request'
        )
        db.session.add(modification)
        db.session.commit()
        
        # Test approval
        success, message = modification.approve(self.manager_user.id, 'Approved by manager')
        self.assertTrue(success)
        self.assertEqual(modification.status, 'Approved')
        self.assertEqual(modification.approved_by_user_id, self.manager_user.id)
        self.assertIsNotNone(modification.approved_at)
        
        # Test implementation start
        success, message = modification.start_implementation(self.chef_user.id)
        self.assertTrue(success)
        self.assertEqual(modification.status, 'In Progress')
        self.assertEqual(modification.implemented_by_user_id, self.chef_user.id)
        
        # Test completion
        success, message = modification.complete_implementation('Items added successfully', self.order.grand_total + 50)
        self.assertTrue(success)
        self.assertEqual(modification.status, 'Completed')
        self.assertEqual(modification.modified_total, self.order.grand_total + 50)
    
    def test_order_modification_rejection(self):
        """Test modification rejection"""
        modification = OrderModification(
            order_id=self.order.id,
            modification_type='add_items',
            requested_by_user_id=self.cashier_user.id,
            reason='Customer request'
        )
        db.session.add(modification)
        db.session.commit()
        
        # Test rejection
        success, message = modification.reject(self.manager_user.id, 'Insufficient stock')
        self.assertTrue(success)
        self.assertEqual(modification.status, 'Rejected')
        self.assertEqual(modification.approved_by_user_id, self.manager_user.id)
    
    def test_order_item_modification(self):
        """Test OrderItemModification model"""
        modification = OrderModification(
            order_id=self.order.id,
            modification_type='add_items',
            requested_by_user_id=self.cashier_user.id,
            reason='Add new item'
        )
        db.session.add(modification)
        db.session.flush()
        
        item_modification = OrderItemModification(
            modification_id=modification.id,
            modification_type='add_item',
            original_menu_item_id=self.menu_item3.id,
            original_quantity=0,
            original_price=Decimal('0'),
            new_quantity=1,
            new_price=self.menu_item3.price
        )
        
        db.session.add(item_modification)
        db.session.commit()
        
        self.assertIsNotNone(item_modification.id)
        self.assertEqual(item_modification.modification_type, 'add_item')
        self.assertEqual(item_modification.original_menu_item_id, self.menu_item3.id)
        self.assertEqual(item_modification.new_quantity, 1)
    
    def test_modification_request(self):
        """Test ModificationRequest model"""
        modification = OrderModification(
            order_id=self.order.id,
            modification_type='add_items',
            requested_by_user_id=self.cashier_user.id,
            reason='Customer request'
        )
        db.session.add(modification)
        db.session.flush()
        
        request = ModificationRequest(
            modification_id=modification.id,
            order_id=self.order.id,
            request_type='customer_request',
            priority='normal'
        )
        
        db.session.add(request)
        db.session.commit()
        
        self.assertIsNotNone(request.id)
        self.assertIsNotNone(request.request_id)
        self.assertEqual(request.modification_id, modification.id)
        self.assertEqual(request.status, 'Pending')


class TestModificationWorkflow(OrderModificationTestCase):
    """Test modification workflow functionality"""
    
    def test_workflow_manager_creation(self):
        """Test ModificationWorkflowManager creation and basic functionality"""
        workflow_manager = ModificationWorkflowManager()
        
        self.assertIn('add_items', workflow_manager.supported_modification_types)
        self.assertIn('remove_items', workflow_manager.supported_modification_types)
        self.assertIn('modify_items', workflow_manager.supported_modification_types)
    
    def test_create_addition_modification(self):
        """Test creating addition modification"""
        workflow_manager = ModificationWorkflowManager()
        
        additions = [{
            'menu_item_id': self.menu_item3.id,
            'quantity': 1,
            'price': self.menu_item3.price
        }]
        
        success, result = create_addition_modification(
            self.order.id,
            self.cashier_user.id,
            additions,
            'Customer wants pasta'
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(result)
        
        # Verify modification was created
        modification = OrderModification.query.get(result)
        self.assertIsNotNone(modification)
        self.assertEqual(modification.modification_type, 'add_items')
        self.assertEqual(modification.status, 'Pending')
        
        # Verify item modification was created
        self.assertEqual(len(modification.item_modifications), 1)
        item_mod = modification.item_modifications[0]
        self.assertEqual(item_mod.modification_type, 'add_item')
        self.assertEqual(item_mod.original_menu_item_id, self.menu_item3.id)
    
    def test_create_removal_modification(self):
        """Test creating removal modification"""
        workflow_manager = ModificationWorkflowManager()
        
        removals = [{
            'order_item_id': self.order_item2.id
        }]
        
        success, result = create_removal_modification(
            self.order.id,
            self.cashier_user.id,
            removals,
            'Customer changed mind'
        )
        
        self.assertTrue(success)
        
        # Verify modification was created
        modification = OrderModification.query.get(result)
        self.assertEqual(modification.modification_type, 'remove_items')
        
        # Verify item modification was created
        item_mod = modification.item_modifications[0]
        self.assertEqual(item_mod.modification_type, 'remove_item')
        self.assertEqual(item_mod.order_item_id, self.order_item2.id)
    
    def test_create_quantity_modification(self):
        """Test creating quantity modification"""
        workflow_manager = ModificationWorkflowManager()
        
        quantity_changes = [{
            'order_item_id': self.order_item1.id,
            'new_quantity': 3
        }]
        
        success, result = create_quantity_modification(
            self.order.id,
            self.cashier_user.id,
            quantity_changes,
            'Customer wants more pizza'
        )
        
        self.assertTrue(success)
        
        # Verify modification was created
        modification = OrderModification.query.get(result)
        self.assertEqual(modification.modification_type, 'modify_items')
        
        # Verify item modification was created
        item_mod = modification.item_modifications[0]
        self.assertEqual(item_mod.modification_type, 'change_quantity')
        self.assertEqual(item_mod.new_quantity, 3)
    
    def test_approval_permissions(self):
        """Test approval permissions"""
        workflow_manager = ModificationWorkflowManager()
        
        # Create a modification with small price difference
        additions = [{
            'menu_item_id': self.menu_item3.id,
            'quantity': 1,
            'price': self.menu_item3.price
        }]
        
        success, result = create_addition_modification(
            self.order.id,
            self.cashier_user.id,
            additions,
            'Small addition'
        )
        
        self.assertTrue(success)
        
        modification = OrderModification.query.get(result)
        
        # Manager should be able to approve
        can_approve = workflow_manager._can_approve_modification(modification, self.manager_user)
        self.assertTrue(can_approve)
        
        # Chef should not be able to approve this type
        can_approve = workflow_manager._can_approve_modification(modification, self.chef_user)
        self.assertFalse(can_approve)
    
    def test_modification_implementation(self):
        """Test modification implementation"""
        workflow_manager = ModificationWorkflowManager()
        
        # Create and approve modification
        additions = [{
            'menu_item_id': self.menu_item3.id,
            'quantity': 1,
            'price': self.menu_item3.price
        }]
        
        success, result = create_addition_modification(
            self.order.id,
            self.cashier_user.id,
            additions,
            'Add pasta'
        )
        
        self.assertTrue(success)
        
        modification = OrderModification.query.get(result)
        
        # Approve modification
        workflow_manager.approve_modification(modification.id, self.manager_user.id, 'Approved')
        
        # Implement modification
        success, message = workflow_manager.implement_modification(
            modification.id,
            self.chef_user.id,
            'Added pasta to order'
        )
        
        self.assertTrue(success)
        
        # Verify modification status
        modification = OrderModification.query.get(modification.id)
        self.assertEqual(modification.status, 'Completed')
        
        # Verify item was added to order
        order_items = OrderItem.query.filter_by(order_id=self.order.id).all()
        self.assertEqual(len(order_items), 3)  # Original 2 + 1 new
        
        # Find the new item
        new_item = next((item for item in order_items if item.menu_item_id == self.menu_item3.id), None)
        self.assertIsNotNone(new_item)
        self.assertEqual(new_item.quantity, 1)


class TestModificationCalculator(OrderModificationTestCase):
    """Test modification calculation functionality"""
    
    def test_addition_cost_calculation(self):
        """Test cost calculation for additions"""
        additions = [
            {'menu_item_id': self.menu_item1.id, 'quantity': 2},
            {'menu_item_id': self.menu_item2.id, 'quantity': 1}
        ]
        
        cost = ModificationCalculator.calculate_addition_cost(additions)
        expected_cost = (Decimal('250.00') * 2) + (Decimal('150.00') * 1)
        
        self.assertEqual(cost, expected_cost)
    
    def test_removal_refund_calculation(self):
        """Test refund calculation for removals"""
        removals = [
            {'order_item_id': self.order_item1.id},
            {'order_item_id': self.order_item2.id}
        ]
        
        refund = ModificationCalculator.calculate_removal_refund(removals)
        expected_refund = self.order_item1.total + self.order_item2.total
        
        self.assertEqual(refund, expected_refund)
    
    def test_quantity_change_cost_calculation(self):
        """Test cost calculation for quantity changes"""
        new_quantity = 5
        cost_diff = ModificationCalculator.calculate_quantity_change_cost(
            self.order_item1.id, new_quantity
        )
        
        # Original: 2 * 250 = 500
        # New: 5 * 250 = 1250
        # Difference: 750
        expected_diff = Decimal('750.00')
        
        self.assertEqual(cost_diff, expected_diff)
    
    def test_item_substitution_cost_calculation(self):
        """Test cost calculation for item substitutions"""
        cost_diff = ModificationCalculator.calculate_item_substitution_cost(
            self.order_item1.id,
            self.menu_item3.id,
            2
        )
        
        # Original: 2 * 250 = 500
        # New: 2 * 200 = 400
        # Difference: -100
        expected_diff = Decimal('-100.00')
        
        self.assertEqual(cost_diff, expected_diff)
    
    def test_gst_impact_calculation(self):
        """Test GST impact calculation"""
        original_amount = Decimal('1000.00')
        new_amount = Decimal('1200.00')
        discount_amount = Decimal('0')
        
        gst_impact = ModificationCalculator.calculate_gst_impact(
            original_amount, new_amount, discount_amount
        )
        
        # Original GST: 1000 * 0.05 = 50
        # New GST: 1200 * 0.05 = 60
        # Impact: 10
        expected_impact = Decimal('10.00')
        
        self.assertEqual(gst_impact, expected_impact)


class TestModificationValidator(OrderModificationTestCase):
    """Test modification validation functionality"""
    
    def test_addition_validation(self):
        """Test validation for item additions"""
        # Valid addition
        valid, message = ModificationValidator.validate_addition(self.menu_item1.id, 5)
        self.assertTrue(valid)
        self.assertIn('validated', message.lower())
        
        # Invalid addition - item not found
        valid, message = ModificationValidator.validate_addition(999, 1)
        self.assertFalse(valid)
        
        # Invalid addition - insufficient stock
        valid, message = ModificationValidator.validate_addition(self.menu_item1.id, 200)
        self.assertFalse(valid)
    
    def test_removal_validation(self):
        """Test validation for item removals"""
        # Valid removal
        valid, message = ModificationValidator.validate_removal(self.order_item1.id)
        self.assertTrue(valid)
        
        # Invalid removal - item not found
        valid, message = ModificationValidator.validate_removal(999)
        self.assertFalse(valid)
    
    def test_quantity_change_validation(self):
        """Test validation for quantity changes"""
        # Valid quantity change
        valid, message = ModificationValidator.validate_quantity_change(self.order_item1.id, 3)
        self.assertTrue(valid)
        
        # Invalid quantity change - negative quantity
        valid, message = ModificationValidator.validate_quantity_change(self.order_item1.id, 0)
        self.assertFalse(valid)
    
    def test_item_substitution_validation(self):
        """Test validation for item substitutions"""
        # Valid substitution
        valid, message = ModificationValidator.validate_item_substitution(
            self.order_item1.id, self.menu_item3.id, 2
        )
        self.assertTrue(valid)
        
        # Invalid substitution - item not found
        valid, message = ModificationValidator.validate_item_substitution(
            self.order_item1.id, 999, 2
        )
        self.assertFalse(valid)
    
    def test_modification_permissions_validation(self):
        """Test validation for modification permissions"""
        # Admin should have full permissions
        valid, message = ModificationValidator.validate_modification_permissions(
            self.admin_user.id, 'add_items', Decimal('1000.00')
        )
        self.assertTrue(valid)
        
        # Manager should have limited permissions
        valid, message = ModificationValidator.validate_modification_permissions(
            self.manager_user.id, 'add_items', Decimal('50.00')  # Under limit
        )
        self.assertTrue(valid)
        
        valid, message = ModificationValidator.validate_modification_permissions(
            self.manager_user.id, 'add_items', Decimal('200.00')  # Over limit
        )
        self.assertFalse(valid)


class TestModificationPaymentIntegration(OrderModificationTestCase):
    """Test payment integration for modifications"""
    
    def test_payment_manager_initialization(self):
        """Test PaymentManager initialization"""
        payment_manager = ModificationPaymentManager()
        self.assertIsNotNone(payment_manager.payment_processor)
    
    def test_modification_payment_summary(self):
        """Test getting payment summary for modifications"""
        # Create a modification
        additions = [{
            'menu_item_id': self.menu_item3.id,
            'quantity': 1,
            'price': self.menu_item3.price
        }]
        
        success, result = create_addition_modification(
            self.order.id,
            self.cashier_user.id,
            additions,
            'Add pasta'
        )
        
        self.assertTrue(success)
        
        modification = OrderModification.query.get(result)
        
        # Get payment summary
        payment_manager = ModificationPaymentManager()
        summary = payment_manager.get_modification_payment_summary(modification)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary['modification_id'], modification.id)
        self.assertIn('transactions', summary)


class TestModificationWebSocketIntegration(OrderModificationTestCase):
    """Test WebSocket integration for modifications"""
    
    def test_websocket_manager_initialization(self):
        """Test WebSocketManager initialization"""
        ws_manager = ModificationWebSocketManager()
        self.assertIsNotNone(ws_manager.MODIFICATION_EVENTS)
        self.assertIn('created', ws_manager.MODIFICATION_EVENTS)
    
    def test_modification_event_preparation(self):
        """Test preparation of modification events"""
        # Create a modification
        additions = [{
            'menu_item_id': self.menu_item3.id,
            'quantity': 1,
            'price': self.menu_item3.price
        }]
        
        success, result = create_addition_modification(
            self.order.id,
            self.cashier_user.id,
            additions,
            'Add pasta'
        )
        
        self.assertTrue(success)
        
        modification = OrderModification.query.get(result)
        
        # Prepare event data
        ws_manager = ModificationWebSocketManager()
        event_data = ws_manager._prepare_modification_event_data(modification, 'created')
        
        self.assertIsNotNone(event_data)
        self.assertEqual(event_data['modification_id'], modification.modification_id)
        self.assertEqual(event_data['order_id'], modification.order_id)
        self.assertEqual(event_data['event_type'], 'created')


class TestModificationScenarios(OrderModificationTestCase):
    """Test common modification scenarios"""
    
    def test_customer_addition_scenario(self):
        """Test customer adding items to existing order"""
        # Customer wants to add a burger
        additions = [{
            'menu_item_id': self.menu_item2.id,
            'quantity': 1,
            'price': self.menu_item2.price
        }]
        
        success, result = create_addition_modification(
            self.order.id,
            self.cashier_user.id,
            additions,
            'Customer wants to add a burger'
        )
        
        self.assertTrue(success)
        
        modification = OrderModification.query.get(result)
        
        # Verify modification details
        self.assertEqual(modification.modification_type, 'add_items')
        self.assertEqual(modification.status, 'Pending')
        self.assertEqual(len(modification.item_modifications), 1)
        
        # Approve and implement
        workflow_manager = ModificationWorkflowManager()
        workflow_manager.approve_modification(modification.id, self.manager_user.id, 'Approved')
        workflow_manager.implement_modification(modification.id, self.chef_user.id, 'Added burger')
        
        # Verify order was updated
        updated_order = Order.query.get(self.order.id)
        order_items = OrderItem.query.filter_by(order_id=self.order.id).all()
        
        self.assertEqual(len(order_items), 3)  # 2 original + 1 new
        self.assertGreater(float(updated_order.grand_total), float(self.order.grand_total))
    
    def test_customer_removal_scenario(self):
        """Test customer removing items from order"""
        # Customer wants to remove one pizza
        removals = [{
            'order_item_id': self.order_item1.id
        }]
        
        success, result = create_removal_modification(
            self.order.id,
            self.cashier_user.id,
            removals,
            'Customer changed mind about pizza'
        )
        
        self.assertTrue(success)
        
        modification = OrderModification.query.get(result)
        
        # Approve and implement
        workflow_manager = ModificationWorkflowManager()
        workflow_manager.approve_modification(modification.id, self.manager_user.id, 'Approved')
        workflow_manager.implement_modification(modification.id, self.chef_user.id, 'Removed pizza')
        
        # Verify item was cancelled
        updated_order_item = OrderItem.query.get(self.order_item1.id)
        self.assertEqual(updated_order_item.status, 'Cancelled')
    
    def test_kitchen_substitution_scenario(self):
        """Test kitchen-initiated item substitution"""
        # Kitchen runs out of pizza, needs to substitute with pasta
        quantity_changes = [{
            'order_item_id': self.order_item1.id,
            'new_quantity': 2
        }]
        
        success, result = create_quantity_modification(
            self.order.id,
            self.chef_user.id,
            quantity_changes,
            'Kitchen substitution - ran out of pizza'
        )
        
        self.assertTrue(success)
        
        modification = OrderModification.query.get(result)
        modification.source = 'kitchen'
        db.session.commit()
        
        # Kitchen staff should be able to implement directly
        workflow_manager = ModificationWorkflowManager()
        workflow_manager.implement_modification(modification.id, self.chef_user.id, 'Substituted pizza with pasta')
        
        # Verify modification was completed
        modification = OrderModification.query.get(modification.id)
        self.assertEqual(modification.status, 'Completed')
    
    def test_order_cancellation_scenario(self):
        """Test order cancellation scenario"""
        from utils.order_modification_workflow import create_cancellation_modification
        
        # Customer wants to cancel entire order
        success, result = create_cancellation_modification(
            self.order.id,
            self.cashier_user.id,
            'Customer had to leave unexpectedly',
            partial=False
        )
        
        self.assertTrue(success)
        
        modification = OrderModification.query.get(result)
        
        # Verify modification type
        self.assertEqual(modification.modification_type, 'cancel_order')
        
        # Approve and implement
        workflow_manager = ModificationWorkflowManager()
        workflow_manager.approve_modification(modification.id, self.manager_user.id, 'Approved cancellation')
        workflow_manager.implement_modification(modification.id, self.chef_user.id, 'Order cancelled')
        
        # Verify order was cancelled
        updated_order = Order.query.get(self.order.id)
        self.assertEqual(updated_order.status, 'Cancelled')


class TestModificationSecurity(OrderModificationTestCase):
    """Test security features of modification system"""
    
    def test_role_based_permissions(self):
        """Test role-based access control"""
        workflow_manager = ModificationWorkflowManager()
        
        # Test modification creation permissions
        can_modify = workflow_manager._can_user_modify_order(self.order, self.cashier_user)
        self.assertTrue(can_modify)  # Cashier can modify their own orders
        
        can_modify = workflow_manager._can_user_modify_order(self.order, self.admin_user)
        self.assertTrue(can_modify)  # Admin can modify any order
        
        # Test approval permissions
        modification = OrderModification(
            order_id=self.order.id,
            modification_type='add_items',
            requested_by_user_id=self.cashier_user.id,
            reason='Test'
        )
        db.session.add(modification)
        db.session.commit()
        
        # Manager can approve
        can_approve = workflow_manager._can_approve_modification(modification, self.manager_user)
        self.assertTrue(can_approve)
        
        # Cashier cannot approve
        can_approve = workflow_manager._can_approve_modification(modification, self.cashier_user)
        self.assertFalse(can_approve)
    
    def test_time_based_modification_limits(self):
        """Test time-based modification restrictions"""
        # Create an old order
        old_order = Order(
            order_number='ORD-OLD-001',
            table_id=self.table.id,
            customer_name='Old Customer',
            order_type='Dine-in',
            status='In Progress',
            created_by=self.cashier_user.id
        )
        old_order.created_at = datetime.utcnow() - timedelta(hours=2)
        db.session.add(old_order)
        db.session.flush()
        
        workflow_manager = ModificationWorkflowManager()
        
        # Should not be able to modify old orders in progress
        can_modify = workflow_manager._can_modify_order(old_order)
        self.assertFalse(can_modify)


def run_modification_tests():
    """Run all modification tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestModificationModels,
        TestModificationWorkflow,
        TestModificationCalculator,
        TestModificationValidator,
        TestModificationPaymentIntegration,
        TestModificationWebSocketIntegration,
        TestModificationScenarios,
        TestModificationSecurity
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Running Order Modification System Tests...")
    print("=" * 60)
    
    success = run_modification_tests()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Order modification system is working correctly.")
    else:
        print("❌ Some tests failed. Please review the implementation.")
    
    exit(0 if success else 1)