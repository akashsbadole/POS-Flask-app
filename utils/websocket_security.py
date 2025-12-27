"""
WebSocket Security and Authentication
Handles secure WebSocket connections, authentication, and authorization
"""

from datetime import datetime, timedelta
from functools import wraps
from flask import current_app, request, session, jsonify
from flask_login import current_user
from werkzeug.security import check_password_hash
import jwt
import secrets
import hashlib
import hmac
import time
from collections import defaultdict, deque
from models import User, KitchenDisplay

class WebSocketSecurityManager:
    """Manages WebSocket security and authentication"""
    
    def __init__(self, app=None):
        self.app = app
        self.active_tokens = {}  # token -> user_id mapping
        self.token_expiry = {}   # token -> expiry timestamp
        self.connection_attempts = defaultdict(deque)  # IP -> recent attempts
        self.rate_limits = defaultdict(lambda: {'count': 0, 'window_start': time.time()})
        self.blocked_ips = set()
        self.session_tokens = {}  # session_id -> auth_data
        
        # Rate limiting configuration
        self.max_connection_attempts = 5
        self.attempt_window = 300  # 5 minutes
        self.block_duration = 1800  # 30 minutes
        
        # Event rate limiting
        self.max_events_per_minute = 60
        self.event_rate_limits = defaultdict(lambda: {'count': 0, 'window_start': time.time()})
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
        # Get secret key for JWT
        self.secret_key = app.config.get('SECRET_KEY', 'fallback-secret-key')
        
        # JWT configuration
        self.jwt_algorithm = 'HS256'
        self.token_expiry_hours = 24
    
    def generate_auth_token(self, user_id, role, display_name=None, station_type='general'):
        """Generate authentication token for WebSocket connection"""
        try:
            # Create token payload
            payload = {
                'user_id': user_id,
                'role': role,
                'display_name': display_name,
                'station_type': station_type,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
                'jti': secrets.token_hex(16)  # JWT ID for token tracking
            }
            
            # Generate token
            token = jwt.encode(payload, self.secret_key, algorithm=self.jwt_algorithm)
            
            # Store token for validation
            self.active_tokens[token] = {
                'user_id': user_id,
                'role': role,
                'display_name': display_name,
                'station_type': station_type,
                'created_at': datetime.utcnow(),
                'jti': payload['jti']
            }
            
            self.token_expiry[token] = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
            
            return token
            
        except Exception as e:
            current_app.logger.error(f"Failed to generate auth token: {str(e)}")
            return None
    
    def validate_auth_token(self, token):
        """Validate authentication token"""
        try:
            if not token:
                return False, {'error': 'No token provided'}
            
            # Check if token is blocked
            if token in self.blocked_ips:
                return False, {'error': 'Token is blocked'}
            
            # Validate JWT token
            try:
                payload = jwt.decode(token, self.secret_key, algorithms=[self.jwt_algorithm])
            except jwt.ExpiredSignatureError:
                return False, {'error': 'Token has expired'}
            except jwt.InvalidTokenError:
                return False, {'error': 'Invalid token'}
            
            # Check if token is in active tokens
            if token not in self.active_tokens:
                return False, {'error': 'Token not found in active sessions'}
            
            # Verify token data matches
            stored_data = self.active_tokens[token]
            if stored_data['jti'] != payload['jti']:
                return False, {'error': 'Token ID mismatch'}
            
            # Check expiry
            if datetime.utcnow() > self.token_expiry.get(token, datetime.utcnow()):
                self.revoke_token(token)
                return False, {'error': 'Token has expired'}
            
            # Get user information
            user = User.query.get(payload['user_id'])
            if not user or not user.is_active:
                return False, {'error': 'User not found or inactive'}
            
            return True, {
                'user': user,
                'token_data': payload,
                'auth_data': stored_data
            }
            
        except Exception as e:
            current_app.logger.error(f"Token validation error: {str(e)}")
            return False, {'error': 'Token validation failed'}
    
    def authenticate_websocket_connection(self, auth_data):
        """Authenticate WebSocket connection with comprehensive security checks"""
        try:
            client_ip = request.environ.get('HTTP_X_REAL_IP', request.environ.get('REMOTE_ADDR'))
            
            # Rate limiting check
            if self.is_rate_limited(client_ip):
                return False, {'error': 'Too many connection attempts. Please try again later.'}
            
            # IP blocking check
            if client_ip in self.blocked_ips:
                return False, {'error': 'IP address is temporarily blocked.'}
            
            # Extract token
            token = auth_data.get('token') or request.args.get('token')
            if not token:
                return False, {'error': 'Authentication token required'}
            
            # Validate token
            token_valid, token_result = self.validate_auth_token(token)
            if not token_valid:
                self.record_failed_attempt(client_ip)
                return False, token_result
            
            # Additional security checks
            user = token_result['user']
            auth_info = token_result['auth_data']
            
            # Check if user has kitchen access
            if not self.has_kitchen_access(user.role):
                return False, {'error': 'Insufficient permissions for kitchen access'}
            
            # Validate display configuration
            display_name = auth_data.get('display_name') or request.args.get('display_name')
            station_type = auth_data.get('station_type') or request.args.get('station_type', 'general')
            
            if not self.validate_display_config(user.role, display_name, station_type):
                return False, {'error': 'Invalid display configuration'}
            
            # Record successful authentication
            self.clear_failed_attempts(client_ip)
            
            # Create session data
            session_data = {
                'user_id': user.id,
                'username': user.username,
                'role': user.role,
                'display_name': display_name,
                'station_type': station_type,
                'authenticated_at': datetime.utcnow(),
                'client_ip': client_ip,
                'user_agent': request.headers.get('User-Agent', ''),
                'jti': auth_info['jti']
            }
            
            return True, {
                'user': user,
                'session_data': session_data,
                'token_data': token_result['token_data']
            }
            
        except Exception as e:
            current_app.logger.error(f"WebSocket authentication error: {str(e)}")
            return False, {'error': 'Authentication failed'}
    
    def has_kitchen_access(self, user_role):
        """Check if user role has kitchen access"""
        allowed_roles = [
            'admin', 'manager', 'head_chef', 'chef', 'kitchen_staff', 
            'waiter', 'waitress', 'supervisor'
        ]
        return user_role in allowed_roles
    
    def validate_display_config(self, user_role, display_name, station_type):
        """Validate display configuration based on user role"""
        # Basic validation
        if not display_name or len(display_name.strip()) < 2:
            return False
        
        if len(display_name) > 50:
            return False
        
        # Station type validation
        valid_stations = ['general', 'grill', 'fry', 'salad', 'dessert', 'beverage', 'expo']
        if station_type not in valid_stations:
            return False
        
        # Role-based access control
        if user_role == 'kitchen_staff':
            # Kitchen staff can only access general or specific assigned stations
            # This would be enhanced with user-station assignments
            return station_type in ['general']
        
        if user_role in ['chef', 'head_chef']:
            # Chefs can access all stations
            return True
        
        if user_role in ['admin', 'manager']:
            # Admin and managers have full access
            return True
        
        if user_role in ['waiter', 'waitress', 'supervisor']:
            # Service staff can access general display
            return station_type == 'general'
        
        return False
    
    def is_rate_limited(self, client_ip):
        """Check if IP is rate limited"""
        current_time = time.time()
        
        # Clean old attempts
        self._clean_old_attempts(client_ip)
        
        attempts = self.connection_attempts[client_ip]
        if len(attempts) >= self.max_connection_attempts:
            # Check if within block period
            oldest_attempt = attempts[0]
            if current_time - oldest_attempt < self.block_duration:
                return True
            else:
                # Clear old attempts
                self.connection_attempts[client_ip] = deque(maxlen=self.max_connection_attempts)
        
        return False
    
    def record_failed_attempt(self, client_ip):
        """Record failed authentication attempt"""
        current_time = time.time()
        self.connection_attempts[client_ip].append(current_time)
        
        # Block IP if too many attempts
        if len(self.connection_attempts[client_ip]) >= self.max_connection_attempts:
            self.blocked_ips.add(client_ip)
            current_app.logger.warning(f"IP {client_ip} blocked due to failed authentication attempts")
    
    def clear_failed_attempts(self, client_ip):
        """Clear failed attempts after successful authentication"""
        if client_ip in self.connection_attempts:
            del self.connection_attempts[client_ip]
    
    def _clean_old_attempts(self, client_ip):
        """Clean old attempts outside the time window"""
        if client_ip not in self.connection_attempts:
            return
        
        current_time = time.time()
        attempts = self.connection_attempts[client_ip]
        
        # Remove attempts outside the window
        while attempts and current_time - attempts[0] > self.attempt_window:
            attempts.popleft()
    
    def check_event_rate_limit(self, user_id, event_type):
        """Check if user is within event rate limits"""
        current_time = time.time()
        user_limit = self.event_rate_limits[user_id]
        
        # Clean old events outside the window
        if current_time - user_limit['window_start'] > 60:  # 1 minute window
            user_limit['count'] = 0
            user_limit['window_start'] = current_time
        
        # Check limit
        if user_limit['count'] >= self.max_events_per_minute:
            return False
        
        user_limit['count'] += 1
        return True
    
    def authorize_kitchen_event(self, user, event_data, event_type):
        """Authorize kitchen event based on user permissions"""
        try:
            user_role = user.role
            
            # Event type authorization matrix
            event_permissions = {
                'new_order': ['admin', 'manager', 'head_chef', 'chef', 'waiter', 'waitress'],
                'order_update': ['admin', 'manager', 'head_chef', 'chef', 'kitchen_staff'],
                'item_update': ['admin', 'manager', 'head_chef', 'chef', 'kitchen_staff'],
                'order_complete': ['admin', 'manager', 'head_chef', 'chef', 'kitchen_staff'],
                'kitchen_alert': ['admin', 'manager', 'head_chef', 'chef', 'kitchen_staff', 'supervisor'],
                'display_status': ['admin', 'manager', 'head_chef', 'chef']
            }
            
            # Check if user has permission for this event type
            if event_type not in event_permissions:
                return False, {'error': 'Unknown event type'}
            
            allowed_roles = event_permissions[event_type]
            if user_role not in allowed_roles:
                return False, {'error': 'Insufficient permissions for this event'}
            
            # Additional authorization checks based on event type
            if event_type == 'order_update':
                return self.authorize_order_update(user, event_data)
            elif event_type == 'item_update':
                return self.authorize_item_update(user, event_data)
            elif event_type == 'kitchen_alert':
                return self.authorize_kitchen_alert(user, event_data)
            
            return True, {'message': 'Event authorized'}
            
        except Exception as e:
            current_app.logger.error(f"Event authorization error: {str(e)}")
            return False, {'error': 'Authorization failed'}
    
    def authorize_order_update(self, user, event_data):
        """Authorize order status update"""
        try:
            from models import Order
            order_id = event_data.get('order_id')
            new_status = event_data.get('status')
            
            if not order_id or not new_status:
                return False, {'error': 'Missing order information'}
            
            order = Order.query.get(order_id)
            if not order:
                return False, {'error': 'Order not found'}
            
            user_role = user.role
            
            # Status transition authorization
            status_transitions = {
                'New': ['In Progress'],
                'In Progress': ['Ready', 'Cancelled'],
                'Ready': ['Completed', 'Cancelled'],
                'Completed': [],  # No transitions from completed
                'Cancelled': []   # No transitions from cancelled
            }
            
            allowed_transitions = status_transitions.get(order.status, [])
            if new_status not in allowed_transitions:
                return False, {'error': f'Invalid status transition from {order.status} to {new_status}'}
            
            # Role-based restrictions
            if user_role == 'kitchen_staff':
                # Kitchen staff can only update certain statuses
                if new_status not in ['In Progress', 'Ready']:
                    return False, {'error': 'Kitchen staff cannot perform this status change'}
            
            return True, {'message': 'Order update authorized'}
            
        except Exception as e:
            return False, {'error': f'Authorization check failed: {str(e)}'}
    
    def authorize_item_update(self, user, event_data):
        """Authorize item status update"""
        try:
            from models import OrderItem
            item_id = event_data.get('item_id')
            new_status = event_data.get('status')
            
            if not item_id or not new_status:
                return False, {'error': 'Missing item information'}
            
            item = OrderItem.query.get(item_id)
            if not item:
                return False, {'error': 'Item not found'}
            
            user_role = user.role
            
            # Item status transitions
            item_status_transitions = {
                'Pending': ['In Progress', 'Cancelled'],
                'In Progress': ['Ready', 'Cancelled'],
                'Ready': ['Completed', 'Cancelled'],
                'Completed': [],  # No transitions from completed
                'Cancelled': []   # No transitions from cancelled
            }
            
            allowed_transitions = item_status_transitions.get(item.status, [])
            if new_status not in allowed_transitions:
                return False, {'error': f'Invalid item status transition from {item.status} to {new_status}'}
            
            return True, {'message': 'Item update authorized'}
            
        except Exception as e:
            return False, {'error': f'Item authorization check failed: {str(e)}'}
    
    def authorize_kitchen_alert(self, user, event_data):
        """Authorize kitchen alert"""
        try:
            user_role = user.role
            alert_type = event_data.get('type', 'info')
            
            # Only certain roles can send urgent alerts
            if alert_type == 'urgent' and user_role not in ['admin', 'manager', 'head_chef']:
                return False, {'error': 'Only authorized personnel can send urgent alerts'}
            
            return True, {'message': 'Kitchen alert authorized'}
            
        except Exception as e:
            return False, {'error': f'Alert authorization check failed: {str(e)}'}
    
    def revoke_token(self, token):
        """Revoke authentication token"""
        try:
            if token in self.active_tokens:
                del self.active_tokens[token]
            
            if token in self.token_expiry:
                del self.token_expiry[token]
            
            if token in self.blocked_ips:
                self.blocked_ips.remove(token)
            
            current_app.logger.info(f"Token revoked: {token[:20]}...")
            
        except Exception as e:
            current_app.logger.error(f"Failed to revoke token: {str(e)}")
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        try:
            current_time = datetime.utcnow()
            expired_tokens = []
            
            for token, expiry in self.token_expiry.items():
                if current_time > expiry:
                    expired_tokens.append(token)
            
            for token in expired_tokens:
                self.revoke_token(token)
            
            if expired_tokens:
                current_app.logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
            
        except Exception as e:
            current_app.logger.error(f"Failed to cleanup expired tokens: {str(e)}")
    
    def get_connection_info(self, session_id):
        """Get connection information for monitoring"""
        return self.session_tokens.get(session_id, {})
    
    def create_secure_display_session(self, user, display_name, station_type):
        """Create secure display session"""
        try:
            # Generate secure token
            token = self.generate_auth_token(
                user_id=user.id,
                role=user.role,
                display_name=display_name,
                station_type=station_type
            )
            
            if not token:
                return None
            
            # Create kitchen display record
            from models.realtime_kot import KitchenDisplay
            display = KitchenDisplay(
                session_id=secrets.token_hex(16),
                display_name=display_name,
                station_type=station_type,
                kitchen_role=user.role,
                created_by=user.id
            )
            
            return {
                'token': token,
                'display': display,
                'session_info': {
                    'user_id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'display_name': display_name,
                    'station_type': station_type,
                    'created_at': datetime.utcnow()
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to create secure display session: {str(e)}")
            return None

# Security decorators for WebSocket events
def require_websocket_auth(f):
    """Decorator to require WebSocket authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This would be used in WebSocket event handlers
        # Implementation depends on the specific WebSocket framework
        return f(*args, **kwargs)
    return decorated_function

def require_kitchen_role(required_roles):
    """Decorator to require specific kitchen roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check user role
            if not hasattr(current_user, 'role') or current_user.role not in required_roles:
                return {'error': 'Insufficient permissions'}, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Global security manager instance
websocket_security = WebSocketSecurityManager()

def get_websocket_security():
    """Get the global WebSocket security manager"""
    return websocket_security

# Authentication helper functions
def create_websocket_auth_token(user, display_name=None, station_type='general'):
    """Create authentication token for WebSocket connection"""
    security = get_websocket_security()
    return security.generate_auth_token(
        user_id=user.id,
        role=user.role,
        display_name=display_name or f"{user.username}'s Display",
        station_type=station_type
    )

def validate_websocket_token(token):
    """Validate WebSocket authentication token"""
    security = get_websocket_security()
    return security.validate_auth_token(token)

# Utility functions for frontend
def get_auth_token_for_display(user, display_config):
    """Get authentication token for kitchen display"""
    try:
        security = get_websocket_security()
        session_data = security.create_secure_display_session(
            user=user,
            display_name=display_config.get('display_name', 'Kitchen Display'),
            station_type=display_config.get('station_type', 'general')
        )
        
        if session_data:
            return {
                'success': True,
                'token': session_data['token'],
                'session_id': session_data['display'].session_id,
                'config': {
                    'display_name': display_config.get('display_name'),
                    'station_type': display_config.get('station_type'),
                    'auto_refresh': display_config.get('auto_refresh', True),
                    'sound_enabled': display_config.get('sound_enabled', True)
                }
            }
        else:
            return {'success': False, 'error': 'Failed to create secure session'}
            
    except Exception as e:
        current_app.logger.error(f"Failed to get auth token for display: {str(e)}")
        return {'success': False, 'error': 'Authentication setup failed'}