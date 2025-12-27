import unittest
import json
import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, create_tables, User
from models.supplier import Supplier, SupplierCategory, SupplierContact, SupplierDocument, SupplierRating
from models.purchase_order import PurchaseOrder, PurchaseOrderItem, PurchaseOrderApproval, PurchaseOrderReceipt, PurchaseOrderTemplate
from models.accounts_payable import AccountsPayable, SupplierPaymentTransaction, BudgetAllocation, BudgetTransaction

class SupplierManagementTestCase(unittest.TestCase):
    """Test case for supplier management system"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        with self.app.app_context():
            # Initialize database
            from models import init_db
            init_db(self.app)
            create_tables()
            
            # Create test user
            self.test_user = User('testuser', 'password', 'admin', 'test@example.com')
            db.session.add(self.test_user)
            db.session.commit()
            
            # Create test supplier category
            self.test_category = SupplierCategory('Food Suppliers', 'Food and beverage suppliers', '#FF6B6B')
            db.session.add(self.test_category)
            db.session.commit()
            
            # Create test supplier
            self.test_supplier = Supplier('Fresh Market', self.test_category.id)
            self.test_supplier.email = 'contact@freshmarket.com'
            self.test_supplier.phone = '+91-9876543210'
            self.test_supplier.payment_terms = 'net_30'
            self.test_supplier.lead_time_days = 2
            self.test_supplier.approve_supplier(self.test_user.id)
            db.session.add(self.test_supplier)
            db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    # ==================== SUPPLIER CATEGORY TESTS ====================
    
    def test_create_supplier_category(self):
        """Test creating a new supplier category"""
        category = SupplierCategory('Equipment Suppliers', 'Kitchen and restaurant equipment', '#4ECDC4')
        db.session.add(category)
        db.session.commit()
        
        self.assertIsNotNone(category.id)
        self.assertEqual(category.name, 'Equipment Suppliers')
        self.assertEqual(category.color_code, '#4ECDC4')
        self.assertTrue(category.is_active)
    
    def test_update_supplier_category(self):
        """Test updating a supplier category"""
        self.test_category.name = 'Updated Food Suppliers'
        self.test_category.description = 'Updated description'
        db.session.commit()
        
        updated_category = Supplier.query.get(self.test_category.id)
        self.assertEqual(updated_category.name, 'Updated Food Suppliers')
        self.assertEqual(updated_category.description, 'Updated description')
    
    # ==================== SUPPLIER TESTS ====================
    
    def test_create_supplier(self):
        """Test creating a new supplier"""
        supplier = Supplier('Kitchen Pro', self.test_category.id)
        supplier.business_name = 'Kitchen Pro Solutions Pvt Ltd'
        supplier.email = 'info@kitchenpro.com'
        supplier.phone = '+91-9876543211'
        supplier.address_line_1 = '123 Industrial Area'
        supplier.city = 'Mumbai'
        supplier.state = 'Maharashtra'
        
        db.session.add(supplier)
        db.session.commit()
        
        self.assertIsNotNone(supplier.id)
        self.assertTrue(supplier.supplier_code.startswith('SUP'))
        self.assertEqual(supplier.name, 'Kitchen Pro')
        self.assertFalse(supplier.is_approved)
    
    def test_supplier_approval(self):
        """Test supplier approval process"""
        # Initially not approved
        self.assertFalse(self.test_supplier.is_approved)
        self.assertEqual(self.test_supplier.status, Supplier.STATUS_PENDING)
        
        # Approve supplier
        self.test_supplier.approve_supplier(self.test_user.id)
        
        self.assertTrue(self.test_supplier.is_approved)
        self.assertEqual(self.test_supplier.status, Supplier.STATUS_ACTIVE)
    
    def test_supplier_performance_update(self):
        """Test supplier performance metrics update"""
        # Create test purchase orders
        po1 = PurchaseOrder(self.test_supplier.id, self.test_user.id)
        po1.total_amount = Decimal('1000.00')
        po1.status = PurchaseOrder.STATUS_COMPLETED
        po1.on_time_delivery = True
        po1.actual_delivery_time = 24
        db.session.add(po1)
        
        po2 = PurchaseOrder(self.test_supplier.id, self.test_user.id)
        po2.total_amount = Decimal('2000.00')
        po2.status = PurchaseOrder.STATUS_COMPLETED
        po2.on_time_delivery = False
        po2.actual_delivery_time = 48
        db.session.add(po2)
        db.session.commit()
        
        # Update performance metrics
        self.test_supplier.update_performance_metrics()
        
        self.assertEqual(self.test_supplier.total_orders, 2)
        self.assertEqual(self.test_supplier.on_time_delivery_rate, 50.0)  # 1 out of 2
        self.assertEqual(self.test_supplier.average_delivery_time, 36)  # (24+48)/2
    
    def test_supplier_rating_update(self):
        """Test supplier rating system"""
        # Add rating
        rating = SupplierRating(
            supplier_id=self.test_supplier.id,
            quality_rating=4.5,
            delivery_rating=4.0,
            price_rating=3.5,
            service_rating=4.0,
            rated_by=self.test_user.id
        )
        db.session.add(rating)
        db.session.commit()
        
        # Update supplier ratings
        self.test_supplier.update_rating(
            quality=rating.quality_rating,
            delivery=rating.delivery_rating,
            price=rating.price_rating
        )
        
        self.assertEqual(float(self.test_supplier.quality_rating), 4.5)
        self.assertEqual(float(self.test_supplier.delivery_rating), 4.0)
        self.assertEqual(float(self.test_supplier.price_rating), 3.5)
        self.assertGreater(float(self.test_supplier.overall_rating), 0)
    
    # ==================== SUPPLIER CONTACT TESTS ====================
    
    def test_create_supplier_contact(self):
        """Test creating a supplier contact"""
        contact = SupplierContact(
            supplier_id=self.test_supplier.id,
            name='John Doe',
            position='Sales Manager',
            email='john@freshmarket.com',
            phone='+91-9876543212'
        )
        contact.is_primary = True
        db.session.add(contact)
        db.session.commit()
        
        self.assertIsNotNone(contact.id)
        self.assertEqual(contact.name, 'John Doe')
        self.assertEqual(contact.position, 'Sales Manager')
        self.assertTrue(contact.is_primary)
    
    # ==================== PURCHASE ORDER TESTS ====================
    
    def test_create_purchase_order(self):
        """Test creating a new purchase order"""
        po = PurchaseOrder(
            supplier_id=self.test_supplier.id,
            created_by=self.test_user.id
        )
        po.expected_delivery_date = date.today() + timedelta(days=3)
        po.priority = PurchaseOrder.PRIORITY_NORMAL
        
        db.session.add(po)
        db.session.flush()
        
        # Add items
        item1 = PurchaseOrderItem(
            purchase_order_id=po.id,
            item_name='Tomatoes',
            quantity_ordered=10,
            unit_price=Decimal('50.00'),
            inventory_item_id=1
        )
        item2 = PurchaseOrderItem(
            purchase_order_id=po.id,
            item_name='Onions',
            quantity_ordered=5,
            unit_price=Decimal('30.00'),
            inventory_item_id=2
        )
        db.session.add_all([item1, item2])
        
        # Calculate totals
        po.calculate_totals()
        db.session.commit()
        
        self.assertIsNotNone(po.id)
        self.assertTrue(po.po_number.startswith('PO'))
        self.assertEqual(po.status, PurchaseOrder.STATUS_DRAFT)
        self.assertEqual(float(po.subtotal), 650.00)  # (10*50) + (5*30)
        self.assertGreater(float(po.total_amount), 0)
    
    def test_purchase_order_workflow(self):
        """Test purchase order status workflow"""
        po = PurchaseOrder(self.test_supplier.id, self.test_user.id)
        db.session.add(po)
        db.session.commit()
        
        # Test status transitions
        self.assertEqual(po.status, PurchaseOrder.STATUS_DRAFT)
        
        # Update to pending
        success, message = po.update_status(PurchaseOrder.STATUS_PENDING, self.test_user.id)
        self.assertTrue(success)
        self.assertEqual(po.status, PurchaseOrder.STATUS_PENDING)
        
        # Approve
        success, message = po.approve(self.test_user.id, 'Approved for purchase')
        self.assertTrue(success)
        self.assertEqual(po.status, PurchaseOrder.STATUS_APPROVED)
        
        # Mark as received
        success, message = po.mark_received(self.test_user.id, date.today())
        self.assertTrue(success)
        self.assertEqual(po.status, PurchaseOrder.STATUS_COMPLETED)
    
    def test_purchase_order_approval_workflow(self):
        """Test multi-level approval workflow"""
        po = PurchaseOrder(self.test_supplier.id, self.test_user.id)
        po.total_amount = Decimal('15000.00')
        po.requires_approval = True
        db.session.add(po)
        db.session.commit()
        
        # Create approval records
        approval1 = PurchaseOrderApproval(
            purchase_order_id=po.id,
            approval_level=1,
            approver_id=self.test_user.id,
            amount_limit=Decimal('10000.00')
        )
        approval2 = PurchaseOrderApproval(
            purchase_order_id=po.id,
            approval_level=2,
            approver_id=self.test_user.id,
            amount_limit=Decimal('50000.00')
        )
        db.session.add_all([approval1, approval2])
        db.session.commit()
        
        self.assertEqual(len(po.approvals), 2)
        self.assertEqual(po.approvals[0].approval_level, 1)
        self.assertEqual(po.approvals[1].approval_level, 2)
    
    def test_item_receiving(self):
        """Test item receiving process"""
        # Create PO with items
        po = PurchaseOrder(self.test_supplier.id, self.test_user.id)
        db.session.add(po)
        db.session.flush()
        
        item = PurchaseOrderItem(
            purchase_order_id=po.id,
            item_name='Rice',
            quantity_ordered=100,
            unit_price=Decimal('40.00'),
            inventory_item_id=1
        )
        db.session.add(item)
        db.session.commit()
        
        # Receive partial quantity
        success, message = item.receive_quantity(50, quality_passed=True)
        self.assertTrue(success)
        self.assertEqual(item.received_quantity, 50)
        self.assertEqual(item.status, PurchaseOrderItem.STATUS_PARTIALLY_RECEIVED)
        
        # Receive remaining quantity
        success, message = item.receive_quantity(50, quality_passed=True)
        self.assertTrue(success)
        self.assertEqual(item.received_quantity, 100)
        self.assertEqual(item.status, PurchaseOrderItem.STATUS_RECEIVED)
        self.assertTrue(item.is_fully_received)
    
    # ==================== ACCOUNTS PAYABLE TESTS ====================
    
    def test_create_accounts_payable(self):
        """Test creating accounts payable entry"""
        ap = AccountsPayable(
            supplier_id=self.test_supplier.id,
            invoice_number='INV-001',
            total_amount=Decimal('5000.00'),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        ap.subtotal = Decimal('4500.00')
        ap.tax_amount = Decimal('500.00')
        db.session.add(ap)
        db.session.commit()
        
        self.assertIsNotNone(ap.id)
        self.assertEqual(ap.invoice_number, 'INV-001')
        self.assertEqual(float(ap.total_amount), 5000.00)
        self.assertEqual(float(ap.balance_amount), 5000.00)
        self.assertEqual(ap.status, AccountsPayable.STATUS_PENDING)
    
    def test_payment_processing(self):
        """Test payment processing"""
        ap = AccountsPayable(
            supplier_id=self.test_supplier.id,
            invoice_number='INV-002',
            total_amount=Decimal('3000.00')
        )
        db.session.add(ap)
        db.session.commit()
        
        # Make partial payment
        success, message = ap.add_payment(
            amount=Decimal('1000.00'),
            payment_method=AccountsPayable.METHOD_BANK_TRANSFER,
            reference='TXN-001'
        )
        self.assertTrue(success)
        self.assertEqual(float(ap.paid_amount), 1000.00)
        self.assertEqual(float(ap.balance_amount), 2000.00)
        self.assertEqual(ap.status, AccountsPayable.STATUS_PARTIAL)
        
        # Make full payment
        success, message = ap.add_payment(
            amount=Decimal('2000.00'),
            payment_method=AccountsPayable.METHOD_BANK_TRANSFER,
            reference='TXN-002'
        )
        self.assertTrue(success)
        self.assertEqual(float(ap.paid_amount), 3000.00)
        self.assertEqual(float(ap.balance_amount), 0.00)
        self.assertEqual(ap.status, AccountsPayable.STATUS_PAID)
    
    def test_overdue_detection(self):
        """Test overdue payment detection"""
        ap = AccountsPayable(
            supplier_id=self.test_supplier.id,
            invoice_number='INV-003',
            total_amount=Decimal('2000.00'),
            due_date=date.today() - timedelta(days=5)  # 5 days overdue
        )
        db.session.add(ap)
        db.session.commit()
        
        self.assertTrue(ap.is_overdue)
        self.assertEqual(ap.days_overdue, 5)
        self.assertEqual(ap.status, AccountsPayable.STATUS_OVERDUE)
    
    # ==================== BUDGET ALLOCATION TESTS ====================
    
    def test_budget_allocation(self):
        """Test budget allocation system"""
        budget = BudgetAllocation(
            name='Monthly Food Procurement',
            total_budget=Decimal('50000.00'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            created_by=self.test_user.id
        )
        budget.category = 'Food'
        budget.department = 'Kitchen'
        db.session.add(budget)
        db.session.commit()
        
        self.assertIsNotNone(budget.id)
        self.assertEqual(float(budget.total_budget), 50000.00)
        self.assertEqual(float(budget.remaining_amount), 50000.00)
        self.assertTrue(budget.is_active)
        
        # Allocate amount
        success, message = budget.allocate_amount(Decimal('10000.00'), 'Initial allocation')
        self.assertTrue(success)
        self.assertEqual(float(budget.remaining_amount), 40000.00)
        
        # Spend amount
        success, message = budget.spend_amount(Decimal('5000.00'), reference_type='purchase_order')
        self.assertTrue(success)
        self.assertEqual(float(budget.spent_amount), 5000.00)
        self.assertEqual(float(budget.remaining_amount), 45000.00)
    
    def test_budget_utilization(self):
        """Test budget utilization tracking"""
        budget = BudgetAllocation(
            name='Equipment Budget',
            total_budget=Decimal('100000.00'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            created_by=self.test_user.id
        )
        db.session.add(budget)
        db.session.commit()
        
        # Spend amounts
        budget.spend_amount(Decimal('25000.00'))
        budget.spend_amount(Decimal('30000.00'))
        budget.spend_amount(Decimal('20000.00'))
        
        self.assertEqual(float(budget.spent_amount), 75000.00)
        self.assertEqual(budget.utilization_percentage, 75.0)
        self.assertEqual(float(budget.remaining_amount), 25000.00)
    
    # ==================== INTEGRATION TESTS ====================
    
    def test_complete_procurement_workflow(self):
        """Test complete procurement workflow from supplier to payment"""
        # 1. Create supplier and add contact
        supplier = Supplier('Premium Foods', self.test_category.id)
        supplier.approve_supplier(self.test_user.id)
        db.session.add(supplier)
        db.session.flush()
        
        contact = SupplierContact(
            supplier_id=supplier.id,
            name='Alice Johnson',
            position='Account Manager',
            email='alice@premiumfoods.com'
        )
        db.session.add(contact)
        
        # 2. Create purchase order
        po = PurchaseOrder(supplier.id, self.test_user.id)
        db.session.add(po)
        db.session.flush()
        
        # Add items
        items = [
            PurchaseOrderItem(po.id, 'Premium Tomatoes', 20, Decimal('80.00'), 1),
            PurchaseOrderItem(po.id, 'Organic Lettuce', 15, Decimal('60.00'), 2),
            PurchaseOrderItem(po.id, 'Fresh Herbs', 10, Decimal('40.00'), 3)
        ]
        db.session.add_all(items)
        po.calculate_totals()
        db.session.commit()
        
        # 3. Approve PO
        po.approve(self.test_user.id)
        
        # 4. Receive items
        for item in items:
            item.receive_quantity(float(item.quantity_ordered), quality_passed=True)
        po.mark_received(self.test_user.id)
        
        # 5. Create accounts payable
        ap = AccountsPayable(
            supplier_id=supplier.id,
            invoice_number='PF-INV-001',
            total_amount=po.total_amount,
            purchase_order_id=po.id
        )
        db.session.add(ap)
        db.session.commit()
        
        # 6. Process payment
        ap.add_payment(
            amount=po.total_amount,
            payment_method=AccountsPayable.METHOD_BANK_TRANSFER,
            reference='PF-PAY-001'
        )
        
        # Verify complete workflow
        self.assertEqual(po.status, PurchaseOrder.STATUS_COMPLETED)
        self.assertEqual(ap.status, AccountsPayable.STATUS_PAID)
        self.assertEqual(float(ap.paid_amount), float(po.total_amount))
        self.assertTrue(supplier.total_orders > 0)
    
    def test_supplier_performance_integration(self):
        """Test supplier performance tracking integration"""
        # Create multiple POs with different performance
        supplier = Supplier('Performance Test Supplier', self.test_category.id)
        supplier.approve_supplier(self.test_user.id)
        db.session.add(supplier)
        db.session.flush()
        
        # Create POs with ratings
        for i in range(3):
            po = PurchaseOrder(supplier.id, self.test_user.id)
            po.expected_delivery_date = date.today() - timedelta(days=5-i)
            po.actual_delivery_date = date.today() - timedelta(days=4-i)
            po.on_time_delivery = (i % 2 == 0)  # Every other order on time
            po.status = PurchaseOrder.STATUS_COMPLETED
            db.session.add(po)
            db.session.flush()
            
            # Add rating
            rating = SupplierRating(
                supplier_id=supplier.id,
                purchase_order_id=po.id,
                quality_rating=4.0 + i * 0.5,
                delivery_rating=3.5 + i * 0.5,
                price_rating=4.5,
                service_rating=4.0,
                rated_by=self.test_user.id
            )
            db.session.add(rating)
            db.session.flush()
        
        db.session.commit()
        
        # Update performance metrics
        supplier.update_performance_metrics()
        supplier.update_rating(quality=4.0, delivery=4.0, price=4.5)
        
        # Verify performance tracking
        self.assertEqual(supplier.total_orders, 3)
        self.assertEqual(supplier.on_time_delivery_rate, 66.67)  # 2 out of 3
        self.assertGreater(float(supplier.overall_rating), 0)
    
    def test_budget_enforcement(self):
        """Test budget enforcement in procurement"""
        # Create budget
        budget = BudgetAllocation(
            name='Weekly Food Budget',
            total_budget=Decimal('20000.00'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            created_by=self.test_user.id
        )
        budget.max_order_amount = Decimal('5000.00')
        db.session.add(budget)
        db.session.commit()
        
        # Test budget allocation
        success, message = budget.allocate_amount(Decimal('15000.00'))
        self.assertTrue(success)
        
        # Test spending within budget
        success, message = budget.spend_amount(Decimal('3000.00'), reference_type='purchase_order')
        self.assertTrue(success)
        
        # Test overspending attempt
        success, message = budget.spend_amount(Decimal('20000.00'), reference_type='purchase_order')
        self.assertFalse(success)
        self.assertIn('Insufficient budget', message)
    
    def test_multi_supplier_comparison(self):
        """Test supplier comparison functionality"""
        # Create multiple suppliers
        suppliers_data = [
            ('Supplier A', 4.5, 95.0),
            ('Supplier B', 4.0, 88.0),
            ('Supplier C', 3.5, 75.0)
        ]
        
        suppliers = []
        for name, rating, delivery_rate in suppliers_data:
            supplier = Supplier(name, self.test_category.id)
            supplier.overall_rating = rating
            supplier.on_time_delivery_rate = delivery_rate
            supplier.approve_supplier(self.test_user.id)
            db.session.add(supplier)
            suppliers.append(supplier)
        
        db.session.commit()
        
        # Verify supplier rankings
        sorted_suppliers = sorted(suppliers, key=lambda s: s.overall_rating, reverse=True)
        self.assertEqual(sorted_suppliers[0].name, 'Supplier A')
        self.assertEqual(sorted_suppliers[1].name, 'Supplier B')
        self.assertEqual(sorted_suppliers[2].name, 'Supplier C')
        
        # Verify delivery performance
        best_delivery = max(suppliers, key=lambda s: s.on_time_delivery_rate)
        self.assertEqual(best_delivery.name, 'Supplier A')


def create_test_suite():
    """Create and return test suite"""
    suite = unittest.TestSuite()
    
    # Add test cases
    test_case = SupplierManagementTestCase
    
    # Supplier category tests
    suite.addTest(test_case('test_create_supplier_category'))
    suite.addTest(test_case('test_update_supplier_category'))
    
    # Supplier tests
    suite.addTest(test_case('test_create_supplier'))
    suite.addTest(test_case('test_supplier_approval'))
    suite.addTest(test_case('test_supplier_performance_update'))
    suite.addTest(test_case('test_supplier_rating_update'))
    
    # Supplier contact tests
    suite.addTest(test_case('test_create_supplier_contact'))
    
    # Purchase order tests
    suite.addTest(test_case('test_create_purchase_order'))
    suite.addTest(test_case('test_purchase_order_workflow'))
    suite.addTest(test_case('test_purchase_order_approval_workflow'))
    suite.addTest(test_case('test_item_receiving'))
    
    # Accounts payable tests
    suite.addTest(test_case('test_create_accounts_payable'))
    suite.addTest(test_case('test_payment_processing'))
    suite.addTest(test_case('test_overdue_detection'))
    
    # Budget allocation tests
    suite.addTest(test_case('test_budget_allocation'))
    suite.addTest(test_case('test_budget_utilization'))
    
    # Integration tests
    suite.addTest(test_case('test_complete_procurement_workflow'))
    suite.addTest(test_case('test_supplier_performance_integration'))
    suite.addTest(test_case('test_budget_enforcement'))
    suite.addTest(test_case('test_multi_supplier_comparison'))
    
    return suite


if __name__ == '__main__':
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    test_suite = create_test_suite()
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        if result.failures:
            print("\nFAILURES:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
        if result.errors:
            print("\nERRORS:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")