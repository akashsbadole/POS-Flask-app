import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///restaurant_pos.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
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

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

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
