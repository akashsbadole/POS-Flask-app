"""
Print History Model for Restaurant POS System
Tracks all print operations for bills and KOTs
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from models import db

class PrintHistory(db.Model):
    """Model to track print operations"""
    __tablename__ = 'print_history'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    print_type = db.Column(db.String(20), nullable=False)  # 'bill', 'kot', 'invoice'
    print_method = db.Column(db.String(20), nullable=False)  # 'thermal', 'pdf', 'preview'
    copies = db.Column(db.Integer, default=1)
    printer_name = db.Column(db.String(100))
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order = db.relationship('Order', backref=db.backref('print_history', lazy=True))
    user = db.relationship('User', backref=db.backref('print_history', lazy=True))
    
    def __repr__(self):
        return f'<PrintHistory {self.id}: Order {self.order_id} - {self.print_type}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else None,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'print_type': self.print_type,
            'print_method': self.print_method,
            'copies': self.copies,
            'printer_name': self.printer_name,
            'success': self.success,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def create_print_record(order_id, user_id, print_type, print_method='thermal', copies=1, printer_name=None, success=True, error_message=None):
        """Create a new print history record"""
        try:
            print_record = PrintHistory(
                order_id=order_id,
                user_id=user_id,
                print_type=print_type,
                print_method=print_method,
                copies=copies,
                printer_name=printer_name,
                success=success,
                error_message=error_message
            )
            db.session.add(print_record)
            db.session.commit()
            return print_record
        except Exception as e:
            db.session.rollback()
            print(f"Error creating print history record: {e}")
            return None
    
    @staticmethod
    def get_print_history(order_id=None, user_id=None, print_type=None, limit=50):
        """Get print history with optional filters"""
        query = PrintHistory.query
        
        if order_id:
            query = query.filter_by(order_id=order_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if print_type:
            query = query.filter_by(print_type=print_type)
        
        return query.order_by(PrintHistory.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_print_statistics(days=30):
        """Get print statistics for the last N days"""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total prints by type
        prints_by_type = db.session.query(
            PrintHistory.print_type,
            db.func.count(PrintHistory.id).label('count'),
            db.func.sum(PrintHistory.copies).label('total_copies')
        ).filter(
            PrintHistory.created_at >= start_date
        ).group_by(PrintHistory.print_type).all()
        
        # Success rate
        total_prints = PrintHistory.query.filter(
            PrintHistory.created_at >= start_date
        ).count()
        
        successful_prints = PrintHistory.query.filter(
            PrintHistory.created_at >= start_date,
            PrintHistory.success == True
        ).count()
        
        success_rate = (successful_prints / total_prints * 100) if total_prints > 0 else 0
        
        # Top users by print count
        top_users = db.session.query(
            PrintHistory.user_id,
            db.func.count(PrintHistory.id).label('print_count')
        ).filter(
            PrintHistory.created_at >= start_date
        ).group_by(PrintHistory.user_id).order_by(
            db.func.count(PrintHistory.id).desc()
        ).limit(5).all()
        
        return {
            'prints_by_type': [
                {
                    'type': item.print_type,
                    'count': item.count,
                    'total_copies': item.total_copies or 0
                } for item in prints_by_type
            ],
            'total_prints': total_prints,
            'successful_prints': successful_prints,
            'success_rate': round(success_rate, 2),
            'top_users': [
                {
                    'user_id': item.user_id,
                    'print_count': item.print_count
                } for item in top_users
            ]
        }