from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from config import config

# Import models
from models import db, User, Category, MenuItem, Table, Order, OrderItem, Payment, Settings

# Create Flask app
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Configure logging
    configure_logging(app)
    
    # Initialize extensions
    db.init_app(app)
    
    # CSRF protection
    csrf = CSRFProtect(app)
    
    # Login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Create default settings
        Settings.create_defaults()
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin_user = User.create_user('admin', 'admin123', 'admin', 'admin@restaurant.com')
            if admin_user:
                print("Default admin user created: username=admin, password=admin123")
    
    # Simple test route first
    @app.route('/simple-test')
    def simple_test():
        return "Simple test working!"
    
    # Register blueprints
    try:
        from routes.auth import auth_bp
        print("Auth blueprint imported successfully")
        app.register_blueprint(auth_bp, url_prefix='/auth')
        print("Auth blueprint registered successfully")
    except Exception as e:
        print(f"Error importing/registering auth blueprint: {e}")
        import traceback
        traceback.print_exc()
    
    from routes.dashboard import dashboard_bp
    from routes.orders import orders_bp
    from routes.menu import menu_bp
    from routes.tables import tables_bp
    from routes.inventory import inventory_bp
    from routes.kot import kot_bp
    from routes.reports import reports_bp
    from routes.api import api_bp
    from routes.email import email_bp
    from routes.footer_settings import footer_settings_bp
    
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(menu_bp, url_prefix='/menu')
    app.register_blueprint(tables_bp, url_prefix='/tables')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(kot_bp, url_prefix='/kot')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(email_bp, url_prefix='/email')
    app.register_blueprint(footer_settings_bp, url_prefix='/footer')
    
    # Main routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    
    # Context processors
    @app.context_processor
    def inject_settings():
        """Inject global settings into templates"""
        public_settings = Settings.get_public()
        all_settings = Settings.get_all_as_dict()
        return dict(public_settings=public_settings, settings=all_settings)
    
    @app.context_processor
    def inject_user():
        """Inject current user into templates"""
        return dict(current_user=current_user)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"Internal server error: {str(error)}")
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.warning(f"Forbidden access attempt: {str(error)}")
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(400)
    def bad_request_error(error):
        app.logger.error(f"Bad request error: {str(error)}")
        app.logger.error(f"Request data: {request.form}")
        app.logger.error(f"Request method: {request.method}")
        app.logger.error(f"Request URL: {request.url}")
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({'error': 'Bad request', 'details': str(error)}), 400
        return render_template('errors/400.html'), 400
    
    # Template filters
    @app.template_filter('currency')
    def currency_filter(amount):
        """Format amount as currency"""
        try:
            currency_symbol = Settings.get('currency_symbol', '₹')
            decimal_places = int(Settings.get('decimal_places', 2))
            return f"{currency_symbol}{float(amount):.{decimal_places}f}"
        except (ValueError, TypeError):
            return f"₹{amount}"
    
    @app.template_filter('datetime')
    def datetime_filter(dt):
        """Format datetime"""
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        return dt.strftime('%d %b %Y %I:%M %p') if dt else ''
    
    @app.template_filter('date')
    def date_filter(dt):
        """Format date"""
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        return dt.strftime('%d %b %Y') if dt else ''
    
    @app.template_filter('time')
    def time_filter(dt):
        """Format time"""
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        return dt.strftime('%I:%M %p') if dt else ''
    
    # Security headers
    @app.after_request
    def after_request(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    return app

def configure_logging(app):
    """Configure application logging"""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Configure file handler with rotation
        file_handler = RotatingFileHandler(
            'logs/pos_app.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)
        app.logger.addHandler(console_handler)
        
        app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
        app.logger.info('POS application startup')
        
        # Configure encryption logger separately
        encryption_logger = logging.getLogger('web_cloud.utils.encryption')
        encryption_handler = RotatingFileHandler(
            'logs/encryption.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        encryption_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        encryption_handler.setLevel(logging.INFO)
        encryption_logger.addHandler(encryption_handler)
        encryption_logger.setLevel(logging.INFO)
        
        # Prevent encryption logs from propagating to root logger
        encryption_logger.propagate = False

# Create app instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
