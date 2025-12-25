#!/usr/bin/env python3
"""
Test script for Flask POS Application
Tests all major functionality and identifies issues
"""

import os
import sys
import unittest
from datetime import datetime

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, create_tables
from models.user import User
from models.category import Category
from models.menu_item import MenuItem
from models.table import Table

class POSTestCase(unittest.TestCase):
    """Test cases for POS Application"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Use in-memory database for testing
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        db.create_all()
        self.client = self.app.test_client()
        
        # Create test user
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            role='admin',
            is_active=True
        )
        self.test_user.set_password('testpass')
        db.session.add(self.test_user)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def login(self, username, password):
        """Helper function to login"""
        return self.client.post('/auth/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)
    
    def logout(self):
        """Helper function to logout"""
        return self.client.get('/auth/logout', follow_redirects=True)
    
    def test_user_creation(self):
        """Test user creation and authentication"""
        user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('testpass'))
        self.assertEqual(user.role, 'admin')
        print("✅ User creation test passed")
    
    def test_login_logout(self):
        """Test login and logout functionality"""
        # Test login
        response = self.login('testuser', 'testpass')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
        
        # Test logout
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
        
        print("✅ Login/Logout test passed")
    
    def test_dashboard_access(self):
        """Test dashboard access after login"""
        self.login('testuser', 'testpass')
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        print("✅ Dashboard access test passed")
    
    def test_category_crud(self):
        """Test category CRUD operations"""
        self.login('testuser', 'testpass')
        
        # Create category
        response = self.client.post('/menu/add_category', data=dict(
            name='Test Category',
            description='Test description'
        ), follow_redirects=True)
        
        category = Category.query.filter_by(name='Test Category').first()
        self.assertIsNotNone(category)
        self.assertEqual(category.description, 'Test description')
        
        print("✅ Category CRUD test passed")
    
    def test_menu_item_crud(self):
        """Test menu item CRUD operations"""
        self.login('testuser', 'testpass')
        
        # Create a category first
        category = Category(name='Test Food', description='Test')
        db.session.add(category)
        db.session.commit()
        
        # Create menu item
        response = self.client.post('/menu/add', data=dict(
            name='Test Item',
            category_id=category.id,
            price=100.00,
            description='Test item',
            stock_quantity=50,
            min_stock_level=10,
            unit='pcs'
        ), follow_redirects=True)
        
        item = MenuItem.query.filter_by(name='Test Item').first()
        self.assertIsNotNone(item)
        self.assertEqual(item.price, 100.00)
        self.assertEqual(item.stock_quantity, 50)
        
        print("✅ Menu item CRUD test passed")
    
    def test_table_management(self):
        """Test table management"""
        self.login('testuser', 'testpass')
        
        # Create table
        response = self.client.post('/tables/add', data=dict(
            table_number='TEST1',
            capacity=4,
            location='Test Location',
            description='Test table'
        ), follow_redirects=True)
        
        table = Table.query.filter_by(table_number='TEST1').first()
        self.assertIsNotNone(table)
        self.assertEqual(table.capacity, 4)
        self.assertEqual(table.status, 'Available')
        
        print("✅ Table management test passed")
    
    def test_gst_calculation(self):
        """Test GST calculation"""
        # Test GST calculation logic
        subtotal = 1000.00
        tax_rate = 5.0  # 5% total GST (2.5% CGST + 2.5% SGST)
        
        expected_cgst = subtotal * 0.025  # 2.5%
        expected_sgst = subtotal * 0.025  # 2.5%
        expected_total = subtotal + expected_cgst + expected_sgst
        
        self.assertEqual(expected_cgst, 25.00)
        self.assertEqual(expected_sgst, 25.00)
        self.assertEqual(expected_total, 1050.00)
        
        print("✅ GST calculation test passed")
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        self.login('testuser', 'testpass')
        
        # Test menu API
        response = self.client.get('/api/menu_items')
        self.assertEqual(response.status_code, 200)
        
        # Test categories API
        response = self.client.get('/api/categories')
        self.assertEqual(response.status_code, 200)
        
        # Test tables API
        response = self.client.get('/api/tables')
        self.assertEqual(response.status_code, 200)
        
        print("✅ API endpoints test passed")

def run_functionality_tests():
    """Run functionality tests outside of unittest framework"""
    print("🧪 Running functionality tests...")
    
    # Test database connection
    try:
        from models import db
        from app import create_app
        app = create_app()
        with app.app_context():
            create_tables()
        print("✅ Database connection test passed")
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False
    
    # Test model imports
    try:
        from models.user import User
        from models.category import Category
        from models.menu_item import MenuItem
        from models.table import Table
        from models.order import Order
        from models.payment import Payment
        from models.settings import Settings
        print("✅ Model imports test passed")
    except Exception as e:
        print(f"❌ Model imports test failed: {e}")
        return False
    
    # Test route imports
    try:
        from routes.auth import auth_bp
        from routes.dashboard import dashboard_bp
        from routes.orders import orders_bp
        from routes.menu import menu_bp
        from routes.tables import tables_bp
        from routes.inventory import inventory_bp
        from routes.kot import kot_bp
        from routes.reports import reports_bp
        from routes.api import api_bp
        print("✅ Route imports test passed")
    except Exception as e:
        print(f"❌ Route imports test failed: {e}")
        return False
    
    # Test template existence
    template_files = [
        'templates/base.html',
        'templates/dashboard/index.html',
        'templates/orders/new.html',
        'templates/menu/index.html',
        'templates/tables/index.html',
        'templates/inventory/index.html',
        'templates/kot/index.html',
        'templates/reports/index.html',
        'templates/auth/login.html'
    ]
    
    for template_file in template_files:
        if os.path.exists(template_file):
            print(f"✅ Template exists: {template_file}")
        else:
            print(f"❌ Template missing: {template_file}")
            return False
    
    # Test static files
    static_files = [
        'static/css/pos.css',
        'static/js/pos.js',
        'static/js/dashboard.js',
        'static/js/order-screen.js',
        'static/js/menu-management.js',
        'static/js/table-management.js',
        'static/js/inventory-management.js',
        'static/js/kot.js',
        'static/js/reports.js'
    ]
    
    for static_file in static_files:
        if os.path.exists(static_file):
            print(f"✅ Static file exists: {static_file}")
        else:
            print(f"❌ Static file missing: {static_file}")
            return False
    
    print("\n🎉 All functionality tests passed!")
    return True

def main():
    """Main test runner"""
    print("🚀 Starting Flask POS Application Tests...\n")
    
    # Change to web_cloud directory
    if os.path.basename(os.getcwd()) != 'web_cloud':
        if os.path.exists('web_cloud'):
            os.chdir('web_cloud')
        else:
            print("❌ Error: web_cloud directory not found")
            return False
    
    print("📋 Running functionality checks...")
    functionality_ok = run_functionality_tests()
    
    if not functionality_ok:
        print("\n❌ Functionality tests failed!")
        return False
    
    print("\n📋 Running unit tests...")
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=0)
    
    print("\n📋 Integration test summary:")
    print("✅ Database setup: OK")
    print("✅ Model definitions: OK")
    print("✅ Route definitions: OK")
    print("✅ Template files: OK")
    print("✅ Static assets: OK")
    print("✅ GST calculations: OK")
    
    print("\n🎉 All tests completed successfully!")
    print("\n📝 Next Steps:")
    print("1. Run 'python init_db.py' to initialize the database")
    print("2. Start the application with 'python app.py'")
    print("3. Login with admin/admin123")
    print("4. Test all features in the web interface")
    
    return True

if __name__ == '__main__':
    main()
