"""
Performance Configuration for Flask Web POS Application
Handles performance settings, caching, and resource optimization
"""

import os
from datetime import timedelta
from typing import Dict, Any

class PerformanceConfig:
    """Base performance configuration class"""
    
    def __init__(self):
        # Database Performance Settings
        self.DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 10))
        self.DB_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', 20))
        self.DB_POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', 30))
        self.DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 3600))
        
        # Caching Settings
        self.CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')  # simple, redis, memcached
        self.CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))  # 5 minutes
        self.CACHE_KEY_PREFIX = os.environ.get('CACHE_KEY_PREFIX', 'pos_')
        
        # Lazy Loading Settings
        self.LAZY_LOADING_ENABLED = os.environ.get('LAZY_LOADING_ENABLED', 'true').lower() == 'true'
        self.IMAGE_LAZY_LOADING = os.environ.get('IMAGE_LAZY_LOADING', 'true').lower() == 'true'
        self.JS_LAZY_LOADING = os.environ.get('JS_LAZY_LOADING', 'true').lower() == 'true'
        
        # Pagination Settings
        self.DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 50))
        self.MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', 200))
        
        # Memory Management
        self.MEMORY_MONITORING_ENABLED = os.environ.get('MEMORY_MONITORING_ENABLED', 'true').lower() == 'true'
        self.MEMORY_WARNING_THRESHOLD = float(os.environ.get('MEMORY_WARNING_THRESHOLD', 0.8))  # 80%
        self.MEMORY_CRITICAL_THRESHOLD = float(os.environ.get('MEMORY_CRITICAL_THRESHOLD', 0.9))  # 90%
        
        # Resource Optimization
        self.CSS_MINIFICATION = os.environ.get('CSS_MINIFICATION', 'true').lower() == 'true'
        self.JS_MINIFICATION = os.environ.get('JS_MINIFICATION', 'true').lower() == 'true'
        self.COMPRESS_RESPONSES = os.environ.get('COMPRESS_RESPONSES', 'true').lower() == 'true'
        
        # Performance Profiles
        self.PERFORMANCE_PROFILE = os.environ.get('PERFORMANCE_PROFILE', 'balanced')  # low, medium, high, balanced
        
        # Background Task Settings
        self.BACKGROUND_TASKS_ENABLED = os.environ.get('BACKGROUND_TASKS_ENABLED', 'true').lower() == 'true'
        self.BACKGROUND_TASK_THREADS = int(os.environ.get('BACKGROUND_TASK_THREADS', 4))
        
    def get_database_uri_optimized(self, base_uri: str) -> str:
        """Get optimized database URI with connection pooling parameters"""
        if 'sqlite' in base_uri:
            # SQLite optimizations
            return f"{base_uri}?cache_size=10000&journal_mode=WAL&synchronous=NORMAL"
        elif 'mysql' in base_uri:
            # MySQL optimizations
            return f"{base_uri}?pool_size={self.DB_POOL_SIZE}&max_overflow={self.DB_MAX_OVERFLOW}"
        elif 'postgresql' in base_uri:
            # PostgreSQL optimizations
            return f"{base_uri}?pool_size={self.DB_POOL_SIZE}&max_overflow={self.DB_MAX_OVERFLOW}"
        return base_uri
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration based on cache type"""
        base_config = {
            'default_timeout': self.CACHE_DEFAULT_TIMEOUT,
            'key_prefix': self.CACHE_KEY_PREFIX
        }
        
        if self.CACHE_TYPE == 'redis':
            return {
                **base_config,
                'type': 'redis',
                'host': os.environ.get('REDIS_HOST', 'localhost'),
                'port': int(os.environ.get('REDIS_PORT', 6379)),
                'db': int(os.environ.get('REDIS_DB', 0)),
                'password': os.environ.get('REDIS_PASSWORD'),
                'decode_responses': True
            }
        elif self.CACHE_TYPE == 'memcached':
            return {
                **base_config,
                'type': 'memcached',
                'servers': os.environ.get('MEMCACHED_SERVERS', 'localhost:11211').split(',')
            }
        else:
            return {**base_config, 'type': 'simple'}
    
    def get_performance_profile(self) -> Dict[str, Any]:
        """Get settings based on performance profile"""
        profiles = {
            'low': {
                'DB_POOL_SIZE': 5,
                'DEFAULT_PAGE_SIZE': 25,
                'CACHE_DEFAULT_TIMEOUT': 600,  # 10 minutes
                'BACKGROUND_TASK_THREADS': 2,
                'IMAGE_QUALITY': 'medium'
            },
            'medium': {
                'DB_POOL_SIZE': 10,
                'DEFAULT_PAGE_SIZE': 50,
                'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes
                'BACKGROUND_TASK_THREADS': 4,
                'IMAGE_QUALITY': 'high'
            },
            'high': {
                'DB_POOL_SIZE': 20,
                'DEFAULT_PAGE_SIZE': 100,
                'CACHE_DEFAULT_TIMEOUT': 60,  # 1 minute
                'BACKGROUND_TASK_THREADS': 8,
                'IMAGE_QUALITY': 'high'
            },
            'balanced': {
                'DB_POOL_SIZE': 10,
                'DEFAULT_PAGE_SIZE': 50,
                'CACHE_DEFAULT_TIMEOUT': 300,
                'BACKGROUND_TASK_THREADS': 4,
                'IMAGE_QUALITY': 'high'
            }
        }
        
        return profiles.get(self.PERFORMANCE_PROFILE, profiles['balanced'])

class DevelopmentPerformanceConfig(PerformanceConfig):
    """Development performance configuration"""
    
    def __init__(self):
        super().__init__()
        self.DEBUG = True
        self.CACHE_TYPE = 'simple'  # Use simple cache for development
        self.LAZY_LOADING_ENABLED = False  # Disable lazy loading in development
        self.CSS_MINIFICATION = False
        self.JS_MINIFICATION = False
        self.PERFORMANCE_PROFILE = 'balanced'

class ProductionPerformanceConfig(PerformanceConfig):
    """Production performance configuration"""
    
    def __init__(self):
        super().__init__()
        self.DEBUG = False
        self.CACHE_TYPE = os.environ.get('CACHE_TYPE', 'redis')  # Use Redis in production
        self.LAZY_LOADING_ENABLED = True
        self.CSS_MINIFICATION = True
        self.JS_MINIFICATION = True
        self.COMPRESS_RESPONSES = True
        self.PERFORMANCE_PROFILE = os.environ.get('PERFORMANCE_PROFILE', 'balanced')

class TestingPerformanceConfig(PerformanceConfig):
    """Testing performance configuration"""
    
    def __init__(self):
        super().__init__()
        self.DEBUG = True
        self.CACHE_TYPE = 'simple'
        self.DB_POOL_SIZE = 2
        self.DEFAULT_PAGE_SIZE = 10
        self.CACHE_DEFAULT_TIMEOUT = 60  # 1 minute for tests
        self.LAZY_LOADING_ENABLED = False

# Performance configuration instances
_performance_configs = {}

def get_performance_config(config_name: str = 'default') -> PerformanceConfig:
    """Get performance configuration instance"""
    if config_name not in _performance_configs:
        if config_name == 'development':
            _performance_configs[config_name] = DevelopmentPerformanceConfig()
        elif config_name == 'production':
            _performance_configs[config_name] = ProductionPerformanceConfig()
        elif config_name == 'testing':
            _performance_configs[config_name] = TestingPerformanceConfig()
        else:
            _performance_configs[config_name] = DevelopmentPerformanceConfig()
    
    return _performance_configs[config_name]

def optimize_flask_config(app, config_name: str = 'default'):
    """Apply performance optimizations to Flask app configuration"""
    perf_config = get_performance_config(config_name)
    
    # Optimize database URI
    if app.config.get('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = perf_config.get_database_uri_optimized(
            app.config['SQLALCHEMY_DATABASE_URI']
        )
    
    # Apply performance profile settings
    profile_settings = perf_config.get_performance_profile()
    for key, value in profile_settings.items():
        env_key = f"POS_{key.upper()}"
        os.environ[env_key] = str(value)
    
    return perf_config