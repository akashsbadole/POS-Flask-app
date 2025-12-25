from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from utils.encryption import get_encryption_manager
from . import db

class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cashier')  # admin, cashier
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    orders = db.relationship('Order', backref='created_by_user', lazy=True)
    
    def __init__(self, username, password, role='cashier', email=None):
        self.username = username
        self.email = self._encrypt_email(email) if email else None
        self.role = role
        self.set_password(password)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = self._encrypt_password_hash(generate_password_hash(password))
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        decrypted_hash = self._decrypt_password_hash(self.password_hash)
        return check_password_hash(decrypted_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_cashier(self):
        """Check if user is cashier"""
        return self.role == 'cashier'
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self._decrypt_email(self.email),
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def create_user(username, password, role='cashier', email=None):
        """Create new user"""
        if User.query.filter_by(username=username).first():
            return None
        user = User(username, password, role, email)
        db.session.add(user)
        db.session.commit()
        return user
    
    def _encrypt_email(self, email):
        """Encrypt email address"""
        if not email:
            return None
        return get_encryption_manager().encrypt_field(email)
    
    def _decrypt_email(self, encrypted_email):
        """Decrypt email address"""
        if not encrypted_email:
            return None
        return get_encryption_manager().decrypt_field(encrypted_email)
    
    def _encrypt_password_hash(self, password_hash):
        """Encrypt password hash"""
        if not password_hash:
            return None
        return get_encryption_manager().encrypt_field(password_hash)
    
    def _decrypt_password_hash(self, encrypted_password_hash):
        """Decrypt password hash"""
        if not encrypted_password_hash:
            return None
        return get_encryption_manager().decrypt_field(encrypted_password_hash)
    
    @property
    def email_decrypted(self):
        """Get decrypted email address"""
        return self._decrypt_email(self.email)
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
