import os
import logging
from datetime import datetime
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import models and utilities
from models import db, init_db, create_tables, validate_database_config, get_database_info
from models.user import User
from utils.encryption import EncryptionManager, get_encryption_manager

# Import routes
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.menu import menu_bp
from routes.orders import orders_bp
from routes.tables import tables_bp
from routes.reports import reports_bp
from routes.users import users_bp
from routes.settings import settings_bp
from routes.inventory import inventory_bp
from routes.kot import kot_bp
from routes.print_management import print_bp as print_management_bp
from routes.printer_customization import printer_customization_bp
from routes.api import api_bp
from routes.dynamic_reports import dynamic_reports_bp
from routes.import_export import import_export_bp
from routes.white_label import white_label_bp
from routes.footer_settings import footer_settings_bp
from routes.email import email_bp

# Import backup system
from routes.backup import backup_bp

# Import backup system utilities
from utils.backup_scheduler import init_backup_scheduler
from utils.backup_monitor import BackupMonitor

def create_app():
    """Create Flask application with all configurations"""
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(os.environ.get('FLASK_ENV', 'config.DevelopmentConfig'))
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Initialize backup system
    init_backup_system(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        init_database(app)
    
    return app

def init_extensions(app):
    """Initialize Flask extensions"""
    
    # Database
    init_db(app)
    
    # CSRF Protection
    csrf = CSRFProtect(app)
    
    # Login Manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Migration support
    migrate = Migrate(app, db)
    
    # Compression
    compress = Compress()
    compress.init_app(app)
    
    # Rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    limiter.init_app(app)
    
    # Store extensions in app for access
    app.extensions['csrf'] = csrf
    app.extensions['login_manager'] = login_manager
    app.extensions['migrate'] = migrate
    app.extensions['compress'] = compress
    app.extensions['limiter'] = limiter

def register_blueprints(app):
    """Register all application blueprints"""
    
    blueprints = [
        (auth_bp, None),
        (dashboard_bp, None),
        (menu_bp, None),
        (orders_bp, None),
        (tables_bp, None),
        (reports_bp, None),
        (users_bp, None),
        (settings_bp, None),
        (inventory_bp, None),
        (kot_bp, None),
        (print_management_bp, None),
        (printer_customization_bp, None),
        (api_bp, '/api'),
        (dynamic_reports_bp, None),
        (import_export_bp, None),
        (white_label_bp, None),
        (footer_settings_bp, None),
        (email_bp, None),
        # Backup system
        (backup_bp, None)
    ]
    
    for blueprint, url_prefix in blueprints:
        if url_prefix:
            app.register_blueprint(blueprint, url_prefix=url_prefix)
        else:
            app.register_blueprint(blueprint)

def init_backup_system(app):
    """Initialize the backup and restore system"""
    
    try:
        # Initialize backup scheduler
        backup_scheduler = init_backup_scheduler(app)
        
        # Initialize backup monitor
        backup_monitor = BackupMonitor(app)
        
        # Store in app context for easy access
        app.backup_scheduler = backup_scheduler
        app.backup_monitor = backup_monitor
        
        app.logger.info("Backup system initialized successfully")
        
    except Exception as e:
        app.logger.error(f"Failed to initialize backup system: {str(e)}")

def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(400)
    def bad_request_error(error):
        return render_template('errors/400.html'), 400

def init_database(app):
    """Initialize database and create tables"""
    
    try:
        # Validate database configuration
        if not validate_database_config(app):
            app.logger.error("Database configuration validation failed")
            return False
        
        # Create all tables
        create_tables()
        
        # Get database info
        db_info = get_database_info()
        app.logger.info(f"Database initialized: {db_info['type']}")
        
        # Create default admin user if none exists
        create_default_admin(app)
        
        # Initialize encryption if not exists
        init_encryption_system(app)
        
        return True
        
    except Exception as e:
        app.logger.error(f"Database initialization failed: {str(e)}")
        return False

def create_default_admin(app):
    """Create default admin user if none exists"""
    
    try:
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                is_active=True
            )
            admin_user.set_password('admin123')  # Default password - should be changed
            
            db.session.add(admin_user)
            db.session.commit()
            
            app.logger.info("Default admin user created (username: admin, password: admin123)")
            
    except Exception as e:
        app.logger.error(f"Failed to create default admin: {str(e)}")

def init_encryption_system(app):
    """Initialize encryption system"""
    
    try:
        encryption_manager = get_encryption_manager(app)
        app.logger.info("Encryption system initialized")
        
    except Exception as e:
        app.logger.error(f"Failed to initialize encryption: {str(e)}")

# Application factory
app = create_app()

# Development server startup
if __name__ == '__main__':
    
    # Ensure backup directories exist
    backup_dirs = ['backups', 'backups/database', 'backups/configuration', 
                   'backups/user_data', 'backups/logs', 'backups/temp']
    
    for directory in backup_dirs:
        os.makedirs(directory, exist_ok=True)
    
    # Start backup scheduler if not already running
    if hasattr(app, 'backup_scheduler') and not app.backup_scheduler.is_running:
        app.backup_scheduler.start_scheduler()
        app.backup_scheduler.reschedule_all_jobs()
        app.logger.info("Backup scheduler started")
    
    # Run the application
    app.run(
        host=app.config.get('HOST', '127.0.0.1'),
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )