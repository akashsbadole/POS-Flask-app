import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///restaurant_pos.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # Set to True in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # GST Configuration
    CGST_RATE = 0.025  # 2.5%
    SGST_RATE = 0.025  # 2.5%
    TOTAL_GST_RATE = 0.05  # 5%
    
    # Currency
    CURRENCY_SYMBOL = '₹'
    DECIMAL_PLACES = 2
    
    # Pagination
    ITEMS_PER_PAGE = 50
    
    # Export settings
    EXPORT_FOLDER = 'exports'
    
    # POS Settings
    DEFAULT_RESTAURANT_NAME = 'Restaurant POS'
    DEFAULT_TAX_RATE = 5.0
    
    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }

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
