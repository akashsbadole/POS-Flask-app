from datetime import datetime
from decimal import Decimal
from . import db

class MenuItem(db.Model):
    """Menu item model for restaurant menu"""
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=10)
    image_path = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)
    
    def __init__(self, name, price, category_id, description=None, stock_quantity=0, 
                 min_stock_level=10, image_path=None):
        self.name = name
        self.price = Decimal(str(price))
        self.category_id = category_id
        self.description = description
        self.stock_quantity = stock_quantity
        self.min_stock_level = min_stock_level
        self.image_path = image_path
    
    @property
    def formatted_price(self):
        """Get formatted price string"""
        return f"₹{self.price:.2f}"
    
    def is_in_stock(self):
        """Check if item is in stock"""
        return self.stock_quantity > 0
    
    def is_low_stock(self):
        """Check if item has low stock"""
        return self.stock_quantity <= self.min_stock_level and self.stock_quantity > 0
    
    def is_out_of_stock(self):
        """Check if item is out of stock"""
        return self.stock_quantity == 0
    
    def update_stock(self, quantity_change):
        """Update stock quantity"""
        new_quantity = self.stock_quantity + quantity_change
        if new_quantity < 0:
            return False
        self.stock_quantity = new_quantity
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def set_stock(self, new_quantity):
        """Set stock quantity directly"""
        if new_quantity < 0:
            return False
        self.stock_quantity = new_quantity
        self.update_stock_status()
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def update_stock_status(self):
        """Update stock status flags based on current stock level"""
        # This method updates the status flags based on stock levels
        # The actual status is determined by is_low_stock() and is_out_of_stock() methods
        # No database fields to update since status is calculated dynamically
        # Just update the timestamp to indicate status was checked
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert menu item to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'formatted_price': self.formatted_price,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'stock_quantity': self.stock_quantity,
            'min_stock_level': self.min_stock_level,
            'is_in_stock': self.is_in_stock(),
            'is_low_stock': self.is_low_stock(),
            'is_out_of_stock': self.is_out_of_stock(),
            'is_active': self.is_active,
            'is_available': self.is_available,
            'image_path': self.image_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_all_active(search_term="", category_id=None):
        """Get all active menu items with optional search and category filter"""
        query = MenuItem.query.filter_by(is_active=True)
        
        if search_term:
            query = query.filter(MenuItem.name.ilike(f'%{search_term}%'))
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        return query.order_by(MenuItem.name).all()
    
    @staticmethod
    def get_by_id(item_id):
        """Get menu item by ID"""
        return MenuItem.query.filter_by(id=item_id, is_active=True).first()
    
    @staticmethod
    def get_by_name(name):
        """Get menu item by name"""
        return MenuItem.query.filter_by(name=name, is_active=True).first()
    
    @staticmethod
    def get_low_stock_items():
        """Get all items with low stock"""
        return MenuItem.query.filter(
            MenuItem.is_active == True,
            MenuItem.stock_quantity <= MenuItem.min_stock_level,
            MenuItem.stock_quantity > 0
        ).all()
    
    @staticmethod
    def get_out_of_stock_items():
        """Get all out of stock items"""
        return MenuItem.query.filter_by(is_active=True, stock_quantity=0).all()
    
    @staticmethod
    def create_menu_item(name, price, category_id, description=None, stock_quantity=0, 
                        min_stock_level=10, image_path=None):
        """Create new menu item"""
        if MenuItem.query.filter_by(name=name).first():
            return None
        
        menu_item = MenuItem(
            name=name,
            price=price,
            category_id=category_id,
            description=description,
            stock_quantity=stock_quantity,
            min_stock_level=min_stock_level,
            image_path=image_path
        )
        db.session.add(menu_item)
        db.session.commit()
        return menu_item
    
    def update(self, name=None, price=None, category_id=None, description=None,
               stock_quantity=None, min_stock_level=None, image_path=None):
        """Update menu item"""
        if name and name != self.name:
            # Check if name already exists
            existing = MenuItem.query.filter_by(name=name).first()
            if existing and existing.id != self.id:
                return False
            self.name = name
        
        if price is not None:
            self.price = Decimal(str(price))
        
        if category_id is not None:
            self.category_id = category_id
        
        if description is not None:
            self.description = description
        
        if stock_quantity is not None:
            self.stock_quantity = stock_quantity
        
        if min_stock_level is not None:
            self.min_stock_level = min_stock_level
        
        if image_path is not None:
            self.image_path = image_path
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def delete(self):
        """Soft delete menu item (mark as inactive)"""
        self.is_active = False
        self.is_available = False
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def hard_delete(self):
        """Hard delete menu item"""
        db.session.delete(self)
        db.session.commit()
    
    def __repr__(self):
        return f'<MenuItem {self.name} (₹{self.price})>'
