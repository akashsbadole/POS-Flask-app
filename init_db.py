#!/usr/bin/env python3
"""
Database initialization script for Flask POS Application
Creates tables and initial data for the POS system
"""

import os
import sys
from datetime import datetime, date

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, create_tables
from models.user import User
from models.category import Category
from models.menu_item import MenuItem
from models.table import Table
from models.settings import Settings

def create_initial_data():
    """Create initial data for the POS system"""
    
    print("Creating initial data...")
    
    # Create default admin user
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@restaurant.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_active=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        print("Created admin user: admin/admin123")
    
    # Create categories
    categories = [
        {'name': 'Appetizers', 'description': 'Starters and appetizers'},
        {'name': 'Main Course', 'description': 'Main dishes'},
        {'name': 'Beverages', 'description': 'Drinks and beverages'},
        {'name': 'Desserts', 'description': 'Sweet dishes and desserts'},
        {'name': 'Snacks', 'description': 'Quick snacks and sides'}
    ]
    
    for cat_data in categories:
        category = Category.query.filter_by(name=cat_data['name']).first()
        if not category:
            category = Category(
                name=cat_data['name'],
                description=cat_data['description']
            )
            category.is_active = True
            db.session.add(category)
    
    db.session.commit()
    print("Created categories")
    
    # Get created categories
    appetizers_cat = Category.query.filter_by(name='Appetizers').first()
    main_course_cat = Category.query.filter_by(name='Main Course').first()
    beverages_cat = Category.query.filter_by(name='Beverages').first()
    desserts_cat = Category.query.filter_by(name='Desserts').first()
    snacks_cat = Category.query.filter_by(name='Snacks').first()
    
    # Create sample menu items
    menu_items = [
        {
            'name': 'Veg Samosa',
            'category_id': appetizers_cat.id,
            'price': 30.00,
            'description': 'Crispy vegetable samosas with mint chutney',
            'stock_quantity': 50,
            'min_stock_level': 10
        },
        {
            'name': 'Paneer Tikka',
            'category_id': appetizers_cat.id,
            'price': 120.00,
            'description': 'Grilled cottage cheese with spices',
            'stock_quantity': 30,
            'min_stock_level': 5
        },
        {
            'name': 'Butter Chicken',
            'category_id': main_course_cat.id,
            'price': 180.00,
            'description': 'Tender chicken in creamy tomato curry',
            'stock_quantity': 25,
            'min_stock_level': 5
        },
        {
            'name': 'Veg Biryani',
            'category_id': main_course_cat.id,
            'price': 140.00,
            'description': 'Fragrant basmati rice with mixed vegetables',
            'stock_quantity': 20,
            'min_stock_level': 5
        },
        {
            'name': 'Fresh Lime Soda',
            'category_id': beverages_cat.id,
            'price': 40.00,
            'description': 'Refreshing lime soda with mint',
            'stock_quantity': 100,
            'min_stock_level': 20
        },
        {
            'name': 'Mango Lassi',
            'category_id': beverages_cat.id,
            'price': 60.00,
            'description': 'Sweet yogurt drink with mango flavor',
            'stock_quantity': 80,
            'min_stock_level': 15
        },
        {
            'name': 'Gulab Jamun',
            'category_id': desserts_cat.id,
            'price': 25.00,
            'description': 'Sweet milk dumplings in sugar syrup',
            'stock_quantity': 60,
            'min_stock_level': 10
        },
        {
            'name': 'French Fries',
            'category_id': snacks_cat.id,
            'price': 80.00,
            'description': 'Crispy golden french fries',
            'stock_quantity': 40,
            'min_stock_level': 8
        }
    ]
    
    for item_data in menu_items:
        item = MenuItem.query.filter_by(name=item_data['name']).first()
        if not item:
            item = MenuItem(
                name=item_data['name'],
                category_id=item_data['category_id'],
                price=item_data['price'],
                description=item_data['description'],
                stock_quantity=item_data['stock_quantity'],
                min_stock_level=item_data['min_stock_level']
            )
            item.is_active = True
            db.session.add(item)
    
    db.session.commit()
    print("Created sample menu items")
    
    # Create tables
    tables = [
        {'table_number': 'T1', 'capacity': 4, 'location': 'Ground Floor'},
        {'table_number': 'T2', 'capacity': 4, 'location': 'Ground Floor'},
        {'table_number': 'T3', 'capacity': 2, 'location': 'Ground Floor'},
        {'table_number': 'T4', 'capacity': 6, 'location': 'Ground Floor'},
        {'table_number': 'T5', 'capacity': 4, 'location': 'First Floor'},
        {'table_number': 'T6', 'capacity': 4, 'location': 'First Floor'},
        {'table_number': 'T7', 'capacity': 8, 'location': 'First Floor'},
        {'table_number': 'T8', 'capacity': 2, 'location': 'Balcony'}
    ]
    
    for table_data in tables:
        table = Table.query.filter_by(table_number=table_data['table_number']).first()
        if not table:
            table = Table(
                table_number=table_data['table_number'],
                capacity=table_data['capacity'],
                location=table_data['location']
            )
            table.status = 'Available'
            table.is_active = True
            db.session.add(table)
    
    db.session.commit()
    print("Created tables")

def main():
    """Main function to initialize the database"""
    print("Starting database initialization...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Create tables
        create_tables()
        print("Database tables created successfully")
        
        # Create initial data
        create_initial_data()
        
        # Create default settings using Settings.create_defaults()
        Settings.create_defaults()
    
    print("\nDatabase initialization completed successfully!")
    print("\nLogin Credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\nPlease change the default password after first login!")

if __name__ == '__main__':
    main()
