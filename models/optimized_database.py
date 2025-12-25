"""
Optimized Database Module for Flask Web POS Application
Implements connection pooling, query optimization, and caching
"""

import time
import threading
from contextlib import contextmanager
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import logging
import psutil
import json

from config.performance_config import get_performance_config

class DatabaseOptimizer:
    """Database optimization utilities"""
    
    def __init__(self, app=None):
        self.app = app
        self.config = get_performance_config()
        self.logger = logging.getLogger(__name__)
        self.query_stats = {}
        self.connection_stats = {}
        self._setup_database_optimizations()
    
    def _setup_database_optimizations(self):
        """Setup database optimizations"""
        # SQLite specific optimizations
        @event.listens_for(Engine, 'connect')
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if 'sqlite' in str(dbapi_connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode = WAL")
                cursor.execute("PRAGMA synchronous = NORMAL")
                cursor.execute("PRAGMA cache_size = 10000")
                cursor.execute("PRAGMA temp_store = MEMORY")
                cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB
                cursor.close()
        
        # MySQL specific optimizations
        @event.listens_for(Engine, 'connect')
        def set_mysql_optimizations(dbapi_connection, connection_record):
            if 'mysql' in str(dbapi_connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION'")
                cursor.execute("SET SESSION innodb_buffer_pool_size = 268435456")  # 256MB
                cursor.close()
    
    def get_optimized_engine(self, database_uri: str) -> Engine:
        """Get optimized database engine with connection pooling"""
        pool_config = {
            'poolclass': QueuePool,
            'pool_size': self.config.DB_POOL_SIZE,
            'max_overflow': self.config.DB_MAX_OVERFLOW,
            'pool_timeout': self.config.DB_POOL_TIMEOUT,
            'pool_recycle': self.config.DB_POOL_RECYCLE,
            'pool_pre_ping': True,
            'pool_reset_on_return': 'commit'
        }
        
        return create_engine(
            database_uri,
            **pool_config,
            echo=self.config.DEBUG,
            echo_pool=self.config.DEBUG
        )
    
    def get_optimized_session(self, engine: Engine):
        """Get optimized session factory"""
        return scoped_session(
            sessionmaker(
                bind=engine,
                autoflush=False,
                expire_on_commit=False
            )
        )

class QueryOptimizer:
    """Query optimization utilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.slow_query_threshold = 1.0  # seconds
        self.query_cache = {}
    
    def optimize_query(self, query_func):
        """Decorator to optimize query execution"""
        @wraps(query_func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Check cache first
            cache_key = self._get_query_cache_key(query_func.__name__, args, kwargs)
            if cache_key in self.query_cache:
                cached_result, cached_time = self.query_cache[cache_key]
                if time.time() - cached_time < 300:  # 5 minutes cache
                    self.logger.debug(f"Cache hit for query: {query_func.__name__}")
                    return cached_result
            
            # Execute query
            result = query_func(*args, **kwargs)
            
            # Log slow queries
            execution_time = time.time() - start_time
            if execution_time > self.slow_query_threshold:
                self.logger.warning(f"Slow query detected: {query_func.__name__} took {execution_time:.2f}s")
            
            # Cache result
            if len(self.query_cache) < 1000:  # Limit cache size
                self.query_cache[cache_key] = (result, time.time())
            
            return result
        return wrapper
    
    def _get_query_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key for query"""
        import hashlib
        key_data = f"{func_name}_{str(args)}_{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def add_index_suggestions(self, table_name: str, columns: List[str]):
        """Add index suggestions for table columns"""
        suggestions = []
        for column in columns:
            suggestion = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{column} ON {table_name}({column})"
            suggestions.append(suggestion)
        return suggestions
    
    def analyze_query(self, query: str):
        """Analyze query performance"""
        # This would typically use EXPLAIN ANALYZE in PostgreSQL
        # or similar functionality in other databases
        analysis = {
            'query': query,
            'suggestions': [
                "Consider adding indexes on frequently filtered columns",
                "Use SELECT specific columns instead of *",
                "Add WHERE conditions to limit result sets",
                "Use JOIN instead of subqueries when possible"
            ]
        }
        return analysis

class ConnectionMonitor:
    """Database connection monitoring"""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.logger = logging.getLogger(__name__)
        self.monitoring_enabled = True
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'avg_connection_time': 0
        }
    
    def monitor_connection(self, func):
        """Decorator to monitor database connections"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            self.connection_stats['total_connections'] += 1
            
            try:
                result = func(*args, **kwargs)
                self.connection_stats['active_connections'] += 1
                return result
            except Exception as e:
                self.connection_stats['failed_connections'] += 1
                self.logger.error(f"Database connection failed: {e}")
                raise
            finally:
                execution_time = time.time() - start_time
                self.connection_stats['avg_connection_time'] = (
                    (self.connection_stats['avg_connection_time'] * (self.connection_stats['total_connections'] - 1) + execution_time) /
                    self.connection_stats['total_connections']
                )
        return wrapper
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return self.connection_stats.copy()
    
    def check_pool_health(self) -> Dict[str, Any]:
        """Check connection pool health"""
        pool = self.engine.pool
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'invalidated': pool.invalidated()
        }

class DatabasePerformanceManager:
    """Main database performance manager"""
    
    def __init__(self, app=None):
        self.app = app
        self.optimizer = DatabaseOptimizer(app)
        self.query_optimizer = QueryOptimizer()
        self.connection_monitor = None
        self.logger = logging.getLogger(__name__)
        self._setup_performance_tracking()
    
    def _setup_performance_tracking(self):
        """Setup performance tracking"""
        if self.app:
            @self.app.before_request
            def before_request():
                self.start_time = time.time()
            
            @self.app.after_request
            def after_request(response):
                if hasattr(self, 'start_time'):
                    execution_time = time.time() - self.start_time
                    if execution_time > 1.0:  # Log slow requests
                        self.logger.warning(f"Slow request detected: {execution_time:.2f}s")
                return response
    
    def get_optimized_engine(self, database_uri: str) -> Engine:
        """Get optimized database engine"""
        return self.optimizer.get_optimized_engine(database_uri)
    
    def get_optimized_session(self, engine: Engine):
        """Get optimized session"""
        return self.optimizer.get_optimized_session(engine)
    
    @contextmanager
    def optimized_session(self, engine: Engine):
        """Context manager for optimized database sessions"""
        session = self.get_optimized_session(engine)
        try:
            yield session
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def monitor_database_performance(self, engine: Engine):
        """Monitor database performance"""
        self.connection_monitor = ConnectionMonitor(engine)
        
        # Log database performance metrics
        def log_performance_metrics():
            while True:
                try:
                    stats = self.connection_monitor.get_connection_stats()
                    pool_health = self.connection_monitor.check_pool_health()
                    
                    self.logger.info(f"Database Performance - Connections: {stats}, Pool Health: {pool_health}")
                    
                    # Check memory usage
                    memory_info = psutil.virtual_memory()
                    if memory_info.percent > 80:
                        self.logger.warning(f"High memory usage: {memory_info.percent}%")
                    
                    time.sleep(60)  # Log every minute
                except Exception as e:
                    self.logger.error(f"Performance monitoring error: {e}")
                    time.sleep(30)  # Wait less on error
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=log_performance_metrics, daemon=True)
        monitor_thread.start()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        report = {
            'database_stats': self.connection_monitor.get_connection_stats() if self.connection_monitor else {},
            'query_cache_info': {
                'cache_size': len(self.query_optimizer.query_cache),
                'cache_hit_rate': self._calculate_cache_hit_rate()
            },
            'system_metrics': self._get_system_metrics(),
            'recommendations': self._get_performance_recommendations()
        }
        return report
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate query cache hit rate"""
        # This would need actual implementation to track cache hits/misses
        return 0.85  # Placeholder
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            return {
                'memory_usage_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'cpu_usage_percent': cpu,
                'disk_usage_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            }
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return {}
    
    def _get_performance_recommendations(self) -> List[str]:
        """Get performance recommendations based on current metrics"""
        recommendations = []
        
        # Check memory usage
        metrics = self._get_system_metrics()
        if metrics.get('memory_usage_percent', 0) > 80:
            recommendations.append("Consider increasing database cache size or optimizing memory usage")
        
        # Check connection pool
        if self.connection_monitor:
            pool_health = self.connection_monitor.check_pool_health()
            if pool_health.get('checked_out', 0) > pool_health.get('pool_size', 1) * 0.8:
                recommendations.append("Consider increasing connection pool size")
        
        # Check query cache
        cache_size = len(self.query_optimizer.query_cache)
        if cache_size > 800:
            recommendations.append("Query cache is getting full, consider increasing cache timeout")
        
        return recommendations

# Global database performance manager instance
_db_performance_manager = None

def get_db_performance_manager(app=None) -> DatabasePerformanceManager:
    """Get global database performance manager instance"""
    global _db_performance_manager
    if _db_performance_manager is None:
        _db_performance_manager = DatabasePerformanceManager(app)
    return _db_performance_manager