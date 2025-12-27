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
from .print_history import PrintHistory
from .audit_log import AuditLog

# Import backup models
from .backup import (
    BackupJob, BackupRun, RestoreOperation, BackupAlert, BackupConfiguration,
    BackupType, BackupStatus, RestoreStatus, init_backup_models
)

def create_tables():
    """Create all database tables"""
    db.create_all()

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    # Create all tables first within app context
    with app.app_context():
        create_tables()
        # Then initialize backup models
        init_backup_models(app)

def validate_database_config(app):
    """Validate database configuration"""
    with app.app_context():
        try:
            # Test database connection
            from sqlalchemy import text
            with db.engine.connect() as connection:
                result = connection.execute(text('SELECT 1'))
                return True
        except Exception as e:
            print(f"Database configuration error: {str(e)}")
            return False

def get_database_info():
    """Get database information"""
    try:
        from sqlalchemy import text
        with db.engine.connect() as connection:
            result = connection.execute(text('SELECT version()'))
            version = result.fetchone()[0]
            
            if 'PostgreSQL' in version:
                db_type = 'PostgreSQL'
            elif 'SQLite' in version:
                db_type = 'SQLite'
            else:
                db_type = 'Unknown'
            
            return {
                'type': db_type,
                'version': version,
                'uri': str(db.engine.url)
            }
    except Exception as e:
        return {
            'type': 'Error',
            'error': str(e),
            'uri': 'Unable to connect'
        }

__all__ = [
    'db', 'User', 'Category', 'MenuItem', 'Table', 'Order', 'OrderItem', 
    'Payment', 'Settings', 'PrintHistory', 'AuditLog', 'create_tables', 
    'init_db', 'validate_database_config', 'get_database_info',
    # Backup models
    'BackupJob', 'BackupRun', 'RestoreOperation', 'BackupAlert', 
    'BackupConfiguration', 'BackupType', 'BackupStatus', 'RestoreStatus',
    'init_backup_models'
]