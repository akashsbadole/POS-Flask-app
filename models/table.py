from datetime import datetime
from . import db

class Table(db.Model):
    """Table model for restaurant seating"""
    __tablename__ = 'tables'
    
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.String(20), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=4)
    status = db.Column(db.String(20), default='Available')  # Available, Occupied, Reserved, Maintenance
    location = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', backref='table', lazy=True)
    
    def __init__(self, table_number, capacity=4, location=None, description=None):
        self.table_number = table_number
        self.capacity = capacity
        self.location = location
        self.description = description
    
    @property
    def is_available(self):
        """Check if table is available"""
        return self.status == 'Available'
    
    @property
    def is_occupied(self):
        """Check if table is occupied"""
        return self.status == 'Occupied'
    
    @property
    def is_reserved(self):
        """Check if table is reserved"""
        return self.status == 'Reserved'
    
    @property
    def is_under_maintenance(self):
        """Check if table is under maintenance"""
        return self.status == 'Maintenance'
    
    def get_current_order(self):
        """Get current active order for this table"""
        from .order import Order
        return Order.query.filter_by(
            table_id=self.id, 
            status='New'
        ).first()
    
    def update_status(self, new_status):
        """Update table status"""
        valid_statuses = ['Available', 'Occupied', 'Reserved', 'Maintenance']
        if new_status not in valid_statuses:
            return False
        
        self.status = new_status
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def mark_available(self):
        """Mark table as available"""
        return self.update_status('Available')
    
    def mark_occupied(self):
        """Mark table as occupied"""
        return self.update_status('Occupied')
    
    def mark_reserved(self):
        """Mark table as reserved"""
        return self.update_status('Reserved')
    
    def mark_maintenance(self):
        """Mark table as under maintenance"""
        return self.update_status('Maintenance')
    
    def to_dict(self):
        """Convert table to dictionary"""
        return {
            'id': self.id,
            'table_number': self.table_number,
            'capacity': self.capacity,
            'status': self.status,
            'is_available': self.is_available,
            'is_occupied': self.is_occupied,
            'is_reserved': self.is_reserved,
            'is_under_maintenance': self.is_under_maintenance,
            'location': self.location,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_status_summary():
        """Get summary of table statuses"""
        statuses = db.session.query(
            Table.status,
            db.func.count(Table.id)
        ).filter_by(is_active=True).group_by(Table.status).all()
        
        return dict(statuses)
    
    @staticmethod
    def get_by_status(status):
        """Get tables by status"""
        return Table.query.filter_by(is_active=True, status=status).order_by(Table.table_number).all()
    
    @staticmethod
    def bulk_update_status(table_ids, new_status):
        """Update status for multiple tables"""
        valid_statuses = ['Available', 'Occupied', 'Reserved', 'Maintenance']
        if new_status not in valid_statuses:
            return False
        
        Table.query.filter(Table.id.in_(table_ids)).update({
            'status': new_status,
            'updated_at': datetime.utcnow()
        })
        db.session.commit()
        return True
    
    @staticmethod
    def get_all_active():
        """Get all active tables"""
        return Table.query.filter_by(is_active=True).order_by(Table.table_number).all()
    
    @staticmethod
    def get_available():
        """Get all available tables"""
        return Table.query.filter_by(is_active=True, status='Available').order_by(Table.table_number).all()
    
    @staticmethod
    def get_occupied():
        """Get all occupied tables"""
        return Table.query.filter_by(is_active=True, status='Occupied').order_by(Table.table_number).all()
    
    @staticmethod
    def get_by_number(table_number):
        """Get table by table number"""
        return Table.query.filter_by(table_number=table_number, is_active=True).first()
    
    @staticmethod
    def get_by_id(table_id):
        """Get table by ID"""
        return Table.query.filter_by(id=table_id, is_active=True).first()
    
    @staticmethod
    def create_table(table_number, capacity=4, location=None, description=None):
        """Create new table"""
        if Table.query.filter_by(table_number=table_number).first():
            return None
        
        table = Table(table_number, capacity, location, description)
        db.session.add(table)
        db.session.commit()
        return table
    
    def update(self, table_number=None, capacity=None, location=None, description=None):
        """Update table"""
        if table_number and table_number != self.table_number:
            # Check if table number already exists
            existing = Table.query.filter_by(table_number=table_number).first()
            if existing and existing.id != self.id:
                return False
            self.table_number = table_number
        
        if capacity is not None:
            self.capacity = capacity
        
        if location is not None:
            self.location = location
        
        if description is not None:
            self.description = description
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def delete(self):
        """Soft delete table (mark as inactive)"""
        self.is_active = False
        self.status = 'Maintenance'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def hard_delete(self):
        """Hard delete table"""
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def reset_all_to_available():
        """Reset all tables to available status"""
        Table.query.filter_by(is_active=True).update({'status': 'Available'})
        db.session.commit()
    
    @staticmethod
    def get_status_summary():
        """Get summary of table statuses"""
        statuses = db.session.query(
            Table.status, 
            db.func.count(Table.id)
        ).filter_by(is_active=True).group_by(Table.status).all()
        
        return dict(statuses)
    
    def __repr__(self):
        return f'<Table {self.table_number} ({self.status})>'
