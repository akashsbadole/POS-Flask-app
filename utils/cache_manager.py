"""
Cache Manager for Flask Web POS Application
Implements multi-level caching with automatic invalidation and monitoring
"""

import time
import threading
import pickle
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps
import logging
import os
from pathlib import Path
import sqlite3
import zlib

from config.performance_config import get_performance_config

class CacheLevel:
    """Base cache level class"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.hit_count = 0
        self.miss_count = 0
        self.set_count = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache"""
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        raise NotImplementedError
    
    def clear(self) -> bool:
        """Clear all values from cache"""
        raise NotImplementedError
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests) if total_requests > 0 else 0
        
        return {
            'name': self.name,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'set_count': self.set_count,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }

class MemoryCache(CacheLevel):
    """In-memory cache implementation"""
    
    def __init__(self, name: str = "memory", max_size: int = 1000):
        super().__init__(name)
        self.max_size = max_size
        self.cache = {}
        self.timestamps = {}
        self.access_times = {}
        self.lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        with self.lock:
            if key not in self.cache:
                self.miss_count += 1
                return None
            
            # Check if expired
            if key in self.timestamps:
                ttl = self.timestamps[key]
                if ttl is not None and time.time() > ttl:
                    del self.cache[key]
                    del self.timestamps[key]
                    del self.access_times[key]
                    self.miss_count += 1
                    return None
            
            # Update access time
            self.access_times[key] = time.time()
            self.hit_count += 1
            return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in memory cache"""
        with self.lock:
            # Check if we need to evict items
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # Set value
            self.cache[key] = value
            
            # Set expiration time
            if ttl is not None:
                self.timestamps[key] = time.time() + ttl
            else:
                self.timestamps[key] = None
            
            # Set access time
            self.access_times[key] = time.time()
            self.set_count += 1
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete value from memory cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.timestamps:
                    del self.timestamps[key]
                if key in self.access_times:
                    del self.access_times[key]
                return True
            return False
    
    def clear(self) -> bool:
        """Clear all values from memory cache"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
            self.access_times.clear()
            return True
    
    def _evict_lru(self):
        """Evict least recently used items"""
        if not self.access_times:
            return
        
        # Find least recently used item
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        
        # Remove it
        del self.cache[lru_key]
        del self.timestamps[lru_key]
        del self.access_times[lru_key]

class DiskCache(CacheLevel):
    """Disk-based cache implementation"""
    
    def __init__(self, name: str = "disk", cache_dir: str = "cache", max_size_mb: int = 100):
        super().__init__(name)
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.lock = threading.RLock()
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize cache database
        self._init_cache_db()
    
    def _init_cache_db(self):
        """Initialize cache metadata database"""
        db_path = self.cache_dir / "cache_metadata.db"
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                filename TEXT,
                created_at REAL,
                expires_at REAL,
                size_bytes INTEGER,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL
            )
        ''')
        self.conn.commit()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key"""
        # Use hash to avoid filesystem issues with special characters
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        with self.lock:
            # Check metadata
            cursor = self.conn.execute('''
                SELECT filename, expires_at FROM cache_entries WHERE key = ?
            ''', (key,))
            result = cursor.fetchone()
            
            if not result:
                self.miss_count += 1
                return None
            
            filename, expires_at = result
            
            # Check if expired
            if expires_at is not None and time.time() > expires_at:
                self.delete(key)
                self.miss_count += 1
                return None
            
            # Read file
            cache_path = self.cache_dir / filename
            if not cache_path.exists():
                self.delete(key)
                self.miss_count += 1
                return None
            
            try:
                with open(cache_path, 'rb') as f:
                    compressed_data = f.read()
                
                # Decompress and deserialize
                decompressed = zlib.decompress(compressed_data)
                value = pickle.loads(decompressed)
                
                # Update access stats
                self.conn.execute('''
                    UPDATE cache_entries 
                    SET access_count = access_count + 1, last_accessed = ?
                    WHERE key = ?
                ''', (time.time(), key))
                self.conn.commit()
                
                self.hit_count += 1
                return value
                
            except Exception as e:
                self.logger.error(f"Error reading cache file {cache_path}: {e}")
                self.delete(key)
                self.miss_count += 1
                return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in disk cache"""
        with self.lock:
            # Serialize and compress value
            try:
                serialized = pickle.dumps(value)
                compressed = zlib.compress(serialized)
            except Exception as e:
                self.logger.error(f"Error serializing cache value: {e}")
                return False
            
            # Get cache path
            cache_path = self._get_cache_path(key)
            filename = cache_path.name
            
            # Write file
            try:
                with open(cache_path, 'wb') as f:
                    f.write(compressed)
            except Exception as e:
                self.logger.error(f"Error writing cache file {cache_path}: {e}")
                return False
            
            # Get file size
            size_bytes = cache_path.stat().st_size
            
            # Set expiration time
            expires_at = time.time() + ttl if ttl is not None else None
            
            # Update metadata
            self.conn.execute('''
                INSERT OR REPLACE INTO cache_entries 
                (key, filename, created_at, expires_at, size_bytes, access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            ''', (key, filename, time.time(), expires_at, size_bytes, time.time()))
            self.conn.commit()
            
            self.set_count += 1
            
            # Check cache size and cleanup if needed
            self._cleanup_cache()
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete value from disk cache"""
        with self.lock:
            cursor = self.conn.execute('''
                SELECT filename FROM cache_entries WHERE key = ?
            ''', (key,))
            result = cursor.fetchone()
            
            if result:
                filename = result[0]
                cache_path = self.cache_dir / filename
                
                # Delete file
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                    except Exception as e:
                        self.logger.error(f"Error deleting cache file {cache_path}: {e}")
                
                # Delete metadata
                self.conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                self.conn.commit()
                
                return True
            
            return False
    
    def clear(self) -> bool:
        """Clear all values from disk cache"""
        with self.lock:
            # Delete all cache files
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    self.logger.error(f"Error deleting cache file {cache_file}: {e}")
            
            # Clear metadata
            self.conn.execute('DELETE FROM cache_entries')
            self.conn.commit()
            
            return True
    
    def _cleanup_cache(self):
        """Clean up cache if it exceeds size limit"""
        cursor = self.conn.execute('''
            SELECT key, filename, size_bytes FROM cache_entries
            ORDER BY last_accessed ASC
        ''')
        results = cursor.fetchall()
        
        total_size = sum(row[2] for row in results)
        
        if total_size > self.max_size_bytes:
            # Delete oldest entries until we're under the limit
            for key, filename, size_bytes in results:
                if total_size <= self.max_size_bytes * 0.8:  # Stop at 80% of limit
                    break
                
                # Delete file
                cache_path = self.cache_dir / filename
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                    except Exception as e:
                        self.logger.error(f"Error deleting cache file {cache_path}: {e}")
                
                # Delete metadata
                self.conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                total_size -= size_bytes
            
            self.conn.commit()

class MultiLevelCache:
    """Multi-level cache with fallback strategies"""
    
    def __init__(self, config=None):
        self.config = config or get_performance_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache levels
        self.levels = {}
        self._setup_cache_levels()
        
        # Cache key prefixes
        self.prefixes = {
            'user': 'user_',
            'order': 'order_',
            'menu': 'menu_',
            'table': 'table_',
            'settings': 'settings_',
            'reports': 'reports_'
        }
        
        # Cache invalidation callbacks
        self.invalidation_callbacks = {}
        self.lock = threading.RLock()
        
    def _setup_cache_levels(self):
        """Setup cache levels based on configuration"""
        # Memory cache (always enabled)
        self.levels['memory'] = MemoryCache(
            name="memory",
            max_size=self.config.get_setting('cache.memory.max_size', 1000)
        )
        
        # Disk cache (optional)
        if self.config.get_setting('cache.disk.enabled', True):
            self.levels['disk'] = DiskCache(
                name="disk",
                cache_dir=self.config.get_setting('cache.disk.directory', 'cache'),
                max_size_mb=self.config.get_setting('cache.disk.max_size_mb', 100)
            )
    
    def _generate_cache_key(self, prefix: str, key: str) -> str:
        """Generate cache key with prefix"""
        return f"{prefix}{key}"
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for caching"""
        if isinstance(value, (str, int, float, bool, dict, list)):
            return value
        return pickle.dumps(value)
    
    def _deserialize_value(self, value: Any) -> Any:
        """Deserialize value from cache"""
        if isinstance(value, bytes):
            try:
                return pickle.loads(value)
            except:
                return value
        return value
    
    def get(self, prefix: str, key: str, default: Any = None) -> Any:
        """Get value from cache with fallback strategy"""
        cache_key = self._generate_cache_key(prefix, key)
        
        # Try memory cache first
        if 'memory' in self.levels:
            value = self.levels['memory'].get(cache_key)
            if value is not None:
                return self._deserialize_value(value)
        
        # Try disk cache as fallback
        if 'disk' in self.levels:
            value = self.levels['disk'].get(cache_key)
            if value is not None:
                # Store in memory cache for faster access
                self.set(prefix, key, value, ttl=300)  # 5 minutes
                return self._deserialize_value(value)
        
        return default
    
    def set(self, prefix: str, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache"""
        cache_key = self._generate_cache_key(prefix, key)
        serialized_value = self._serialize_value(value)
        
        success = True
        
        # Set in memory cache
        if 'memory' in self.levels:
            if not self.levels['memory'].set(cache_key, serialized_value, ttl):
                success = False
        
        # Set in disk cache
        if 'disk' in self.levels:
            if not self.levels['disk'].set(cache_key, serialized_value, ttl or 3600):  # 1 hour default
                success = False
        
        return success
    
    def delete(self, prefix: str, key: str) -> bool:
        """Delete value from cache"""
        cache_key = self._generate_cache_key(prefix, key)
        success = True
        
        # Delete from memory cache
        if 'memory' in self.levels:
            if not self.levels['memory'].delete(cache_key):
                success = False
        
        # Delete from disk cache
        if 'disk' in self.levels:
            if not self.levels['disk'].delete(cache_key):
                success = False
        
        return success
    
    def clear(self, prefix: str = None) -> bool:
        """Clear cache values"""
        if prefix:
            # Clear specific prefix
            cache_key = self._generate_cache_key(prefix, "")
            success = True
            
            for level in self.levels.values():
                # This is a simplified implementation - in practice, you'd need to scan all keys
                if not level.clear():
                    success = False
            
            return success
        else:
            # Clear all caches
            success = True
            
            for level in self.levels.values():
                if not level.clear():
                    success = False
            
            return success
    
    def invalidate(self, prefix: str, key: str = None):
        """Invalidate cache entries"""
        with self.lock:
            if key:
                self.delete(prefix, key)
            else:
                self.clear(prefix)
            
            # Call invalidation callbacks
            callback_key = f"{prefix}_{key}" if key else prefix
            if callback_key in self.invalidation_callbacks:
                for callback in self.invalidation_callbacks[callback_key]:
                    try:
                        callback()
                    except Exception as e:
                        self.logger.error(f"Cache invalidation callback error: {e}")
    
    def register_invalidation_callback(self, prefix: str, key: str, callback: Callable):
        """Register callback for cache invalidation"""
        callback_key = f"{prefix}_{key}"
        if callback_key not in self.invalidation_callbacks:
            self.invalidation_callbacks[callback_key] = []
        
        self.invalidation_callbacks[callback_key].append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'levels': {},
            'total_hit_rate': 0,
            'total_requests': 0,
            'total_hits': 0
        }
        
        total_requests = 0
        total_hits = 0
        
        for name, level in self.levels.items():
            level_stats = level.get_stats()
            stats['levels'][name] = level_stats
            total_requests += level_stats['total_requests']
            total_hits += level_stats['hit_count']
        
        stats['total_requests'] = total_requests
        stats['total_hits'] = total_hits
        stats['total_hit_rate'] = (total_hits / total_requests) if total_requests > 0 else 0
        
        return stats
    
    def cache_decorator(self, prefix: str, ttl: int = None):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key from function arguments
                cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # Try to get from cache
                cached_result = self.get(prefix, cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(prefix, cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator

# Global cache instance
_cache_manager = None

def get_cache_manager(config=None) -> MultiLevelCache:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = MultiLevelCache(config)
    return _cache_manager

def cache_result(prefix: str, ttl: int = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            cached_result = cache_manager.get(prefix, cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache_manager.set(prefix, cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator