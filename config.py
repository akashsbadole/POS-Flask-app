import os
from datetime import timedelta
from decimal import Decimal

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Twilio SMS Configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    TWILIO_VERIFY_SERVICE_SID = os.environ.get('TWILIO_VERIFY_SERVICE_SID')
    TWILIO_ENABLED = os.environ.get('TWILIO_ENABLED', 'false').lower() in ['true', '1', 'yes']
    
    # Database configuration - supports both SQLite and PostgreSQL
    # Check DATABASE_URL first, then construct based on DATABASE_TYPE
    DATABASE_URL = os.environ.get('DATABASE_URL')
    DATABASE_TYPE = os.environ.get('DATABASE_TYPE', 'sqlite').lower()
    
    if DATABASE_URL:
        # Use DATABASE_URL if provided
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    elif DATABASE_TYPE == 'postgresql':
        # PostgreSQL configuration
        POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
        POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
        POSTGRES_USER = os.environ.get('POSTGRES_USER', 'postgres')
        POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', '')
        POSTGRES_DB = os.environ.get('POSTGRES_DB', 'restaurant_pos')
        SQLALCHEMY_DATABASE_URI = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'
    else:
        # Default SQLite configuration
        SQLITE_DATABASE_PATH = os.environ.get('SQLITE_DATABASE_PATH', 'restaurant_pos.db')
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{SQLITE_DATABASE_PATH}'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    
    # Security enhancements
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # Performance settings
    SQLALCHEMY_POOL_SIZE = 20
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_MAX_OVERFLOW = 0
    
    # Cache configuration
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Email settings (production defaults)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Payment Gateway Configuration
    RAZORPAY_API_KEY = os.environ.get('RAZORPAY_API_KEY')
    RAZORPAY_SECRET_KEY = os.environ.get('RAZORPAY_SECRET_KEY')
    RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET')
    RAZORPAY_ENABLED = os.environ.get('RAZORPAY_ENABLED', 'false').lower() in ['true', '1', 'yes']
    RAZORPAY_TEST_MODE = os.environ.get('RAZORPAY_TEST_MODE', 'true').lower() in ['true', '1', 'yes']
    
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    STRIPE_ENABLED = os.environ.get('STRIPE_ENABLED', 'false').lower() in ['true', '1', 'yes']
    STRIPE_TEST_MODE = os.environ.get('STRIPE_TEST_MODE', 'true').lower() in ['true', '1', 'yes']
    
    # Payment Security Settings
    PAYMENT_DATA_RETENTION_DAYS = int(os.environ.get('PAYMENT_DATA_RETENTION_DAYS', 365))
    DAILY_PAYMENT_LIMIT = Decimal(os.environ.get('DAILY_PAYMENT_LIMIT', '100000'))
    PAYMENT_RATE_LIMIT_PER_MINUTE = int(os.environ.get('PAYMENT_RATE_LIMIT_PER_MINUTE', 10))
    
    # Redis Configuration for Rate Limiting
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Payment Gateway URLs
    PAYMENT_SUCCESS_URL = os.environ.get('PAYMENT_SUCCESS_URL')
    PAYMENT_FAILURE_URL = os.environ.get('PAYMENT_FAILURE_URL')
    PAYMENT_WEBHOOK_BASE_URL = os.environ.get('PAYMENT_WEBHOOK_BASE_URL')
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/production.log'
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    
    # SSL/TLS
    PREFERRED_URL_SCHEME = 'https'
    
    # Asset optimization
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year
    
    # Backup settings
    BACKUP_ENABLED = True
    BACKUP_INTERVAL_HOURS = 24
    BACKUP_RETENTION_DAYS = 30
    
    # Payment Gateway Features
    PAYMENT_GATEWAYS_ENABLED = True
    PAYMENT_REFUNDS_ENABLED = True
    PAYMENT_SPLIT_ENABLED = False  # For future implementation
    PAYMENT_RECURRING_ENABLED = False  # For future implementation
    PAYMENT_MULTI_CURRENCY = True
    
    # PCI Compliance Settings
    PCI_DSS_COMPLIANT = True
    ENCRYPT_PAYMENT_DATA = True
    LOG_PAYMENT_EVENTS = True
    AUDIT_PAYMENT_ACCESS = True
    
    # Webhook Security
    WEBHOOK_SIGNATURE_VERIFICATION = True
    WEBHOOK_IP_WHITELIST = os.environ.get('WEBHOOK_IP_WHITELIST', '').split(',') if os.environ.get('WEBHOOK_IP_WHITELIST') else []
    
    # Payment Method Configuration
    DEFAULT_CURRENCY = 'INR'
    SUPPORTED_CURRENCIES = ['INR', 'USD', 'EUR']
    PAYMENT_TIMEOUT_MINUTES = 15

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
