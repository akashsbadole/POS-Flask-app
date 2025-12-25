from datetime import datetime
from decimal import Decimal
import uuid
from utils.encryption import get_encryption_manager
from . import db

class Order(db.Model):
    """Order model for restaurant orders"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=True)
    customer_mobile = db.Column(db.String(20), nullable=True)
    order_type = db.Column(db.String(20), default='Dine-in')  # Dine-in, Takeaway, Delivery
    status = db.Column(db.String(20), default='New')  # New, In Progress, Ready, Completed, Cancelled
    
    # Financial fields
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    cgst_amount = db.Column(db.Numeric(10, 2), default=0)  # 2.5%
    sgst_amount = db.Column(db.Numeric(10, 2), default=0)  # 2.5%
    total_tax = db.Column(db.Numeric(10, 2), default=0)      # Total GST (5%)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_type = db.Column(db.String(10), default='none')  # none, percentage, fixed
    grand_total = db.Column(db.Numeric(10, 2), default=0)
    
    # Additional fields
    special_instructions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, order_number=None, table_id=None, customer_name=None, customer_mobile=None,
                 order_type='Dine-in', created_by=None):
        self.order_number = order_number or self.generate_order_number()
        self.table_id = table_id
        self.customer_name = self._encrypt_customer_name(customer_name) if customer_name else None
        self.customer_mobile = self._encrypt_customer_mobile(customer_mobile) if customer_mobile else None
        self.order_type = order_type
        self.created_by = created_by
    
    @staticmethod
    def generate_order_number():
        """Generate unique order number"""
        prefix = "ORD"
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = str(uuid.uuid4())[:8].upper()
        return f"{prefix}{date_str}{random_str}"
    
    @property
    def formatted_subtotal(self):
        """Get formatted subtotal"""
        return f"₹{self.subtotal:.2f}"
    
    @property
    def formatted_cgst(self):
        """Get formatted CGST"""
        return f"₹{self.cgst_amount:.2f}"
    
    @property
    def formatted_sgst(self):
        """Get formatted SGST"""
        return f"₹{self.sgst_amount:.2f}"
    
    @property
    def formatted_total_tax(self):
        """Get formatted total tax"""
        return f"₹{self.total_tax:.2f}"
    
    @property
    def formatted_discount(self):
        """Get formatted discount"""
        return f"-₹{self.discount_amount:.2f}" if self.discount_amount > 0 else "₹0.00"
    
    @property
    def formatted_grand_total(self):
        """Get formatted grand total"""
        return f"₹{self.grand_total:.2f}"
    
    @property
    def item_count(self):
        """Get total number of items"""
        return sum(item.quantity for item in self.order_items if item.status != 'Cancelled')
    
    @property
    def is_new(self):
        """Check if order is new"""
        return self.status == 'New'
    
    @property
    def is_in_progress(self):
        """Check if order is in progress"""
        return self.status == 'In Progress'
    
    @property
    def is_ready(self):
        """Check if order is ready"""
        return self.status == 'Ready'
    
    @property
    def is_completed(self):
        """Check if order is completed"""
        return self.status == 'Completed'
    
    @property
    def is_cancelled(self):
        """Check if order is cancelled"""
        return self.status == 'Cancelled'
    
    def add_item(self, menu_item_id, quantity, price):
        """Add item to order"""
        from .menu_item import MenuItem
        
        # Check if menu item exists and is available
        menu_item = MenuItem.query.filter_by(id=menu_item_id, is_active=True, is_available=True).first()
        if not menu_item:
            return False
        
        # Check stock
        if menu_item.stock_quantity < quantity:
            return False
        
        # Check if item already exists in order
        existing_item = OrderItem.query.filter_by(
            order_id=self.id, 
            menu_item_id=menu_item_id, 
            status__in=['Pending', 'In Progress']
        ).first()
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item.quantity + quantity
            if menu_item.stock_quantity < quantity:
                return False
            existing_item.quantity = new_quantity
            existing_item.total = existing_item.price * new_quantity
        else:
            # Add new item
            order_item = OrderItem(
                order_id=self.id,
                menu_item_id=menu_item_id,
                quantity=quantity,
                price=price
            )
            db.session.add(order_item)
        
        # Update stock
        menu_item.update_stock(-quantity)
        self.calculate_totals()
        db.session.commit()
        return True
    
    def remove_item(self, item_id):
        """Remove item from order"""
        order_item = OrderItem.query.filter_by(id=item_id, order_id=self.id).first()
        if not order_item:
            return False
        
        # Return stock
        menu_item = order_item.menu_item
        if menu_item:
            menu_item.update_stock(order_item.quantity)
        
        db.session.delete(order_item)
        self.calculate_totals()
        db.session.commit()
        return True
    
    def update_item_quantity(self, item_id, new_quantity):
        """Update item quantity"""
        order_item = OrderItem.query.filter_by(id=item_id, order_id=self.id).first()
        if not order_item:
            return False
        
        menu_item = order_item.menu_item
        if not menu_item:
            return False
        
        # Calculate stock difference
        quantity_diff = new_quantity - order_item.quantity
        
        # Check stock availability
        if quantity_diff > 0 and menu_item.stock_quantity < quantity_diff:
            return False
        
        # Update quantity and stock
        order_item.quantity = new_quantity
        order_item.total = order_item.price * new_quantity
        menu_item.update_stock(-quantity_diff)
        
        self.calculate_totals()
        db.session.commit()
        return True
    
    def apply_discount(self, discount_type, discount_value):
        """Apply discount to order"""
        if discount_type == 'percentage':
            self.discount_amount = self.subtotal * (Decimal(str(discount_value)) / Decimal('100'))
        elif discount_type == 'fixed':
            self.discount_amount = Decimal(str(discount_value))
        else:
            self.discount_amount = Decimal('0')
        
        self.discount_type = discount_type
        self.calculate_totals()
        db.session.commit()
    
    def calculate_totals(self):
        """Calculate order totals including GST"""
        # Calculate subtotal
        self.subtotal = sum(item.total for item in self.order_items if item.status != 'Cancelled')
        
        # Calculate GST (5% total: 2.5% CGST + 2.5% SGST)
        taxable_amount = self.subtotal - self.discount_amount
        self.cgst_amount = taxable_amount * Decimal('0.025')  # 2.5%
        self.sgst_amount = taxable_amount * Decimal('0.025')  # 2.5%
        self.total_tax = self.cgst_amount + self.sgst_amount
        
        # Calculate grand total
        self.grand_total = taxable_amount + self.total_tax
    
    def update_status(self, new_status):
        """Update order status"""
        valid_statuses = ['New', 'In Progress', 'Ready', 'Completed', 'Cancelled']
        if new_status not in valid_statuses:
            return False
        
        old_status = self.status
        self.status = new_status
        
        # Update completed_at timestamp
        if new_status == 'Completed' and not self.completed_at:
            self.completed_at = datetime.utcnow()
        
        # Update table status if needed
        if self.table_id and new_status == 'Completed':
            from .table import Table
            table = Table.query.get(self.table_id)
            if table:
                table.mark_available()
        
        # Update item statuses based on order status
        if new_status in ['Completed', 'Cancelled']:
            for item in self.order_items:
                if item.status not in ['Completed', 'Cancelled']:
                    item.status = new_status
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def to_dict(self):
        """Convert order to dictionary"""
        return {
            'id': self.id,
            'order_number': self.order_number,
            'table_id': self.table_id,
            'table_number': self.table.table_number if self.table else None,
            'customer_name': self._decrypt_customer_name(self.customer_name),
            'customer_mobile': self._decrypt_customer_mobile(self.customer_mobile),
            'order_type': self.order_type,
            'status': self.status,
            'item_count': self.item_count,
            'subtotal': float(self.subtotal),
            'formatted_subtotal': self.formatted_subtotal,
            'cgst_amount': float(self.cgst_amount),
            'formatted_cgst': self.formatted_cgst,
            'sgst_amount': float(self.sgst_amount),
            'formatted_sgst': self.formatted_sgst,
            'total_tax': float(self.total_tax),
            'formatted_total_tax': self.formatted_total_tax,
            'discount_amount': float(self.discount_amount),
            'formatted_discount': self.formatted_discount,
            'discount_type': self.discount_type,
            'grand_total': float(self.grand_total),
            'formatted_grand_total': self.formatted_grand_total,
            'special_instructions': self.special_instructions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_by': self.created_by,
            'created_by_username': self.created_by_user.username if self.created_by_user else None
        }
    
    @staticmethod
    def get_by_number(order_number):
        """Get order by order number"""
        return Order.query.filter_by(order_number=order_number).first()
    
    @staticmethod
    def get_by_id(order_id):
        """Get order by ID"""
        return Order.query.get(order_id)
    
    @staticmethod
    def get_active_orders():
        """Get all active orders (not completed or cancelled)"""
        return Order.query.filter(
            Order.status.in_(['New', 'In Progress', 'Ready'])
        ).order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def get_orders_by_date_range(start_date, end_date):
        """Get orders within date range"""
        return Order.query.filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).order_by(Order.created_at.desc()).all()
    
    def _encrypt_customer_name(self, customer_name):
        """Encrypt customer name"""
        if not customer_name:
            return None
        return get_encryption_manager().encrypt_field(customer_name)
    
    def _decrypt_customer_name(self, encrypted_customer_name):
        """Decrypt customer name"""
        if not encrypted_customer_name:
            return None
        return get_encryption_manager().decrypt_field(encrypted_customer_name)
    
    def _encrypt_customer_mobile(self, customer_mobile):
        """Encrypt customer mobile number"""
        if not customer_mobile:
            return None
        return get_encryption_manager().encrypt_field(customer_mobile)
    
    def _decrypt_customer_mobile(self, encrypted_customer_mobile):
        """Decrypt customer mobile number"""
        if not encrypted_customer_mobile:
            return None
        return get_encryption_manager().decrypt_field(encrypted_customer_mobile)
    
    @property
    def customer_name_decrypted(self):
        """Get decrypted customer name"""
        return self._decrypt_customer_name(self.customer_name)
    
    @property
    def customer_mobile_decrypted(self):
        """Get decrypted customer mobile"""
        return self._decrypt_customer_mobile(self.customer_mobile)
    
    def __repr__(self):
        return f'<Order {self.order_number} ({self.status})>'


class OrderItem(db.Model):
    """Order item model for individual items in an order"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Unit price
    total = db.Column(db.Numeric(10, 2), nullable=False)    # Total price (price * quantity)
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Ready, Completed, Cancelled
    special_instructions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, order_id, menu_item_id, quantity, price):
        self.order_id = order_id
        self.menu_item_id = menu_item_id
        self.quantity = quantity
        self.price = Decimal(str(price))
        self.total = self.price * self.quantity
    
    @property
    def formatted_price(self):
        """Get formatted unit price"""
        return f"₹{self.price:.2f}"
    
    @property
    def formatted_total(self):
        """Get formatted total price"""
        return f"₹{self.total:.2f}"
    
    @property
    def item_name(self):
        """Get menu item name"""
        return self.menu_item.name if self.menu_item else "Unknown Item"
    
    def update_status(self, new_status):
        """Update item status"""
        valid_statuses = ['Pending', 'In Progress', 'Ready', 'Completed', 'Cancelled']
        if new_status not in valid_statuses:
            return False
        
        self.status = new_status
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def to_dict(self):
        """Convert order item to dictionary"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'menu_item_id': self.menu_item_id,
            'item_name': self.item_name,
            'quantity': self.quantity,
            'price': float(self.price),
            'formatted_price': self.formatted_price,
            'total': float(self.total),
            'formatted_total': self.formatted_total,
            'status': self.status,
            'special_instructions': self.special_instructions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<OrderItem {self.item_name} x{self.quantity}>'
