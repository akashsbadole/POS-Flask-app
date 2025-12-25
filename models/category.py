from datetime import datetime

from . import db

class Category(db.Model):
    """Category model for menu item organization"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    menu_items = db.relationship('MenuItem', backref='category', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
    
    def get_item_count(self):
        """Get count of menu items in this category"""
        from .menu_item import MenuItem
        return MenuItem.query.filter_by(category_id=self.id, is_active=True).count()
    
    def get_active_items(self):
        """Get all active menu items in this category"""
        from .menu_item import MenuItem
        return MenuItem.query.filter_by(category_id=self.id, is_active=True).all()
    
    def to_dict(self):
        """Convert category to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'item_count': self.get_item_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_all_active():
        """Get all active categories"""
        return Category.query.filter_by(is_active=True).order_by(Category.name).all()
    
    @staticmethod
    def get_by_name(name):
        """Get category by name"""
        return Category.query.filter_by(name=name).first()
    
    @staticmethod
    def create_category(name, description=None):
        """Create new category"""
        if Category.query.filter_by(name=name).first():
            return None
        category = Category(name, description)
        db.session.add(category)
        db.session.commit()
        return category
    
    def update(self, name=None, description=None):
        """Update category"""
        if name and name != self.name:
            # Check if name already exists
            existing = Category.query.filter_by(name=name).first()
            if existing and existing.id != self.id:
                return False
            self.name = name
        
        if description is not None:
            self.description = description
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def delete(self):
        """Soft delete category (mark as inactive)"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def hard_delete(self):
        """Hard delete category and all associated menu items"""
        db.session.delete(self)
        db.session.commit()
    
    def __repr__(self):
        return f'<Category {self.name}>'
