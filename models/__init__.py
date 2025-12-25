from flask_sqlalchemy import SQLAlchemy

# Create shared database instance
db = SQLAlchemy()

from .user import User
from .category import Category
from .menu_item import MenuItem
from .table import Table
from .order import Order, OrderItem
from .payment import Payment
from .settings import Settings

def create_tables():
    """Create all database tables"""
    db.create_all()

__all__ = ['db', 'User', 'Category', 'MenuItem', 'Table', 'Order', 'OrderItem', 'Payment', 'Settings', 'create_tables']
