"""
Performance Monitoring and Security Enhancement Utilities for Flask POS Application
Provides caching, rate limiting, performance tracking, and security features
"""

import time
import psutil
import gc
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from collections import defaultdict, deque
from flask import request, g, current_app, session, jsonify
from werkzeug.local import LocalProxy
import hashlib
import hmac
import secrets

class PerformanceMonitor:
    """Performance monitoring and optimization system"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.slow_queries = deque(maxlen=100)
        self.memory_usage = deque(maxlen=60)
        self.response_times = deque(maxlen=1000)
        self.error_rates = defaultdict(lambda: deque(maxlen=100))
        self.cache_hits = 0
        self.cache_misses = 0
        self.active_connections = 0
        self.start_time = time.time()
        
        # Start background monitoring
        self.monitor_thread = threading.Thread(target=self._background_monitor, daemon=True)
        self.monitor_thread.start()
    
    def track_request(self, endpoint: str, response_time: float, status_code: int):
        """Track request metrics"""
        self.response_times.append(response_time)
        
        if status_code >= 400:
            self.error_rates[endpoint].append({
                'timestamp': datetime.utcnow(),
                'status_code': status_code
            })
        
        # Track slow requests
        if response_time > 2.0:  # Slow if > 2 seconds
            self.slow_queries.append({
                'endpoint': endpoint,
                'response_time': response_time,
                'timestamp': datetime.utcnow(),
                'status_code': status_code,
                'user_agent': request.headers.get('User-Agent', ''),
                'ip': request.remote_addr
            })
    
    def track_cache_hit(self):
        """Track cache hit"""
        self.cache_hits += 1
    
    def track_cache_miss(self):
        """Track cache miss"""
        self.cache_misses += 1
    
    def _background_monitor(self):
        """Background performance monitoring"""
        while True:
            try:
                # Track memory usage
                memory_info = psutil.virtual_memory()
                self.memory_usage.append({
                    'timestamp': datetime.utcnow(),
                    'percent': memory_info.percent,
                    'available': memory_info.available,
                    'used': memory_info.used
                })
                
                # Clean up old error data
                self._cleanup_old_data()
                
                # Suggest optimizations
                self._suggest_optimizations()
                
                time.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                current_app.logger.error(f"Performance monitoring error: {e}")
                time.sleep(60)
    
    def _cleanup_old_data(self):
        """Clean up old performance data"""
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        # Clean error rates
        for endpoint in self.error_rates:
            self.error_rates[endpoint] = deque(
                [err for err in self.error_rates[endpoint] 
                 if err['timestamp'] > cutoff_time],
                maxlen=100
            )
    
    def _suggest_optimizations(self):
        """Suggest performance optimizations"""
        if len(self.memory_usage) > 10:
            avg_memory = sum(m['percent'] for m in self.memory_usage) / len(self.memory_usage)
            
            if avg_memory > 80:
                current_app.logger.warning("High memory usage detected. Consider optimizing queries or increasing memory.")
            
            if avg_memory > 90:
                # Force garbage collection
                gc.collect()
        
        # Check for slow queries
        recent_slow = [q for q in self.slow_queries 
                      if q['timestamp'] > datetime.utcnow() - timedelta(minutes=5)]
        
        if len(recent_slow) > 5:
            current_app.logger.warning(f"Multiple slow queries detected: {len(recent_slow)} in last 5 minutes")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.response_times:
            return {}
        
        avg_response_time = sum(self.response_times) / len(self.response_times)
        cache_total = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / cache_total * 100) if cache_total > 0 else 0
        
        return {
            'uptime': time.time() - self.start_time,
            'avg_response_time': avg_response_time,
            'total_requests': len(self.response_times),
            'cache_hit_rate': cache_hit_rate,
            'memory_usage': list(self.memory_usage)[-10:],  # Last 10 readings
            'slow_queries_count': len(self.slow_queries),
            'error_rate': self._calculate_error_rate(),
            'active_connections': self.active_connections
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate overall error rate"""
        total_errors = sum(len(errors) for errors in self.error_rates.values())
        total_requests = len(self.response_times)
        
        if total_requests == 0:
            return 0.0
        
        return (total_errors / total_requests) * 100

class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self):
        self.requests = defaultdict(deque)
        self.blocked_ips = defaultdict(lambda: {'until': None, 'count': 0})
    
    def is_allowed(self, key: str, limit: int = 100, window: int = 60) -> bool:
        """Check if request is allowed based on rate limit"""
        now = time.time()
        request_window = deque(
            [req_time for req_time in self.requests[key] 
             if now - req_time < window],
            maxlen=limit
        )
        
        # Check if IP is blocked
        ip_block_info = self.blocked_ips[request.remote_addr]
        if ip_block_info['until'] and now < ip_block_info['until']:
            return False
        
        if len(request_window) >= limit:
            # Block the IP temporarily
            self.blocked_ips[request.remote_addr]['until'] = now + (window * 2)
            self.blocked_ips[request.remote_addr]['count'] += 1
            
            # Log rate limit violation
            current_app.logger.warning(
                f"Rate limit exceeded for {key} from IP {request.remote_addr}"
            )
            
            return False
        
        self.requests[key].append(now)
        return True
    
    def get_block_info(self, ip: str) -> Dict[str, Any]:
        """Get block information for an IP"""
        block_info = self.blocked_ips[ip]
        return {
            'is_blocked': block_info['until'] and time.time() < block_info['until'],
            'blocked_until': block_info['until'],
            'block_count': block_info['count']
        }

class SecurityManager:
    """Security enhancement utilities"""
    
    def __init__(self):
        self.failed_attempts = defaultdict(deque)
        self.suspicious_ips = set()
        self.session_tokens = {}
        
    def validate_csrf_token(self, token: str, session_token: str) -> bool:
        """Validate CSRF token"""
        if not token or not session_token:
            return False
        
        try:
            return hmac.compare_digest(token, session_token)
        except Exception:
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use HMAC with SHA-256 for password hashing
        password_hash = hmac.new(
            salt.encode('utf-8'),
            password.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return password_hash, salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        computed_hash = hmac.new(
            salt.encode('utf-8'),
            password.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(computed_hash, password_hash)
    
    def check_suspicious_activity(self, ip: str) -> bool:
        """Check for suspicious activity from IP"""
        # Check for failed login attempts
        failed_attempts = [attempt for attempt in self.failed_attempts[ip] 
                          if time.time() - attempt < 300]  # Last 5 minutes
        
        if len(failed_attempts) >= 5:
            self.suspicious_ips.add(ip)
            current_app.logger.warning(f"Suspicious activity detected from IP: {ip}")
            return True
        
        return False
    
    def record_failed_attempt(self, ip: str, username: str = None):
        """Record failed login attempt"""
        self.failed_attempts[ip].append({
            'timestamp': time.time(),
            'username': username
        })
        
        # Keep only last 24 hours of attempts
        cutoff = time.time() - 86400
        self.failed_attempts[ip] = deque(
            [attempt for attempt in self.failed_attempts[ip] 
             if attempt['timestamp'] > cutoff],
            maxlen=100
        )
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        return ip in self.suspicious_ips
    
    def sanitize_input(self, data: Any) -> Any:
        """Sanitize input data"""
        if isinstance(data, str):
            # Basic XSS prevention
            dangerous_chars = ['<', '>', '"', "'", '&', 'javascript:', 'vbscript:']
            for char in dangerous_chars:
                data = data.replace(char, '')
            return data.strip()
        elif isinstance(data, dict):
            return {k: self.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]
        return data

class CacheManager:
    """Simple in-memory cache with TTL"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Any:
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                return None
            
            item = self.cache[key]
            if item['expires'] and time.time() > item['expires']:
                del self.cache[key]
                del self.access_times[key]
                return None
            
            self.access_times[key] = time.time()
            return item['value']
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL"""
        with self.lock:
            # Remove oldest item if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.access_times.keys(), 
                              key=lambda k: self.access_times[k])
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            expires = time.time() + ttl if ttl > 0 else None
            self.cache[key] = {
                'value': value,
                'created': time.time(),
                'expires': expires
            }
            self.access_times[key] = time.time()
    
    def delete(self, key: str):
        """Delete item from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.access_times[key]
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            expired_items = sum(
                1 for item in self.cache.values()
                if item['expires'] and time.time() > item['expires']
            )
            
            return {
                'total_items': len(self.cache),
                'expired_items': expired_items,
                'memory_usage': len(str(self.cache))  # Rough estimate
            }

# Global instances
performance_monitor = PerformanceMonitor()
rate_limiter = RateLimiter()
security_manager = SecurityManager()
cache_manager = CacheManager()

# Decorators
def performance_track(f):
    """Decorator to track performance"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            # Track active connections
            performance_monitor.active_connections += 1
            
            # Execute function
            result = f(*args, **kwargs)
            
            # Track metrics
            response_time = time.time() - start_time
            performance_monitor.track_request(
                request.endpoint if hasattr(request, 'endpoint') else 'unknown',
                response_time,
                getattr(g, 'status_code', 200)
            )
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            performance_monitor.track_request(
                request.endpoint if hasattr(request, 'endpoint') else 'unknown',
                response_time,
                500
            )
            raise e
        finally:
            performance_monitor.active_connections -= 1
    
    return decorated_function

def rate_limit(limit: int = 100, window: int = 60):
    """Decorator for rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use IP and endpoint as rate limit key
            key = f"{request.remote_addr}:{request.endpoint}"
            
            if not rate_limiter.is_allowed(key, limit, window):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': window
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def secure_route(f):
    """Decorator for security enhancements"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Add security headers
        g.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'"
        }
        
        # Check for suspicious activity
        if security_manager.check_suspicious_activity(request.remote_addr):
            return jsonify({'error': 'Access denied'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def cache_result(ttl: int = 300, key_prefix: str = ''):
    """Decorator for caching function results"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{f.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                performance_monitor.track_cache_hit()
                return cached_result
            
            # Execute function and cache result
            performance_monitor.track_cache_miss()
            result = f(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return decorated_function
    return decorator

def validate_csrf(f):
    """Decorator for CSRF validation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            session_token = session.get('csrf_token')
            
            if not security_manager.validate_csrf_token(token, session_token):
                return jsonify({'error': 'Invalid CSRF token'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Utility functions
def get_client_info() -> Dict[str, Any]:
    """Get client information for security monitoring"""
    return {
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'referer': request.headers.get('Referer', ''),
        'accept_language': request.headers.get('Accept-Language', ''),
        'timestamp': datetime.utcnow().isoformat()
    }

def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log security events"""
    client_info = get_client_info()
    
    current_app.logger.warning(
        f"Security Event: {event_type} | "
        f"IP: {client_info['ip']} | "
        f"User-Agent: {client_info['user_agent']} | "
        f"Details: {details}"
    )

def generate_csrf_token() -> str:
    """Generate and store CSRF token"""
    token = security_manager.generate_secure_token()
    session['csrf_token'] = token
    return token

def sanitize_form_data() -> Dict[str, Any]:
    """Sanitize all form data"""
    sanitized = {}
    for key, value in request.form.items():
        sanitized[key] = security_manager.sanitize_input(value)
    return sanitized

def validate_json_data(required_fields: List[str]) -> tuple:
    """Validate JSON data with required fields"""
    if not request.is_json:
        return None, 'Invalid JSON'
    
    data = request.get_json()
    if not data:
        return None, 'Empty JSON data'
    
    sanitized = security_manager.sanitize_input(data)
    
    # Check required fields
    missing_fields = [field for field in required_fields if field not in sanitized]
    if missing_fields:
        return None, f'Missing required fields: {missing_fields}'
    
    return sanitized, None
