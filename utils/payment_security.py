"""
Payment Security and PCI Compliance Utilities
"""

import secrets
import hashlib
import hmac
import time
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from flask import request, current_app
from functools import wraps
import redis
import jwt

class PaymentSecurityManager:
    """Manages security aspects of payment processing"""
    
    def __init__(self):
        """Initialize security manager"""
        self.redis_client = None
        self._redis_initialized = False
    
    def _initialize_redis(self):
        """Initialize Redis connection for rate limiting and caching"""
        if self._redis_initialized:
            return
        
        try:
            if hasattr(current_app, 'config'):
                redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()  # Test connection
                self._redis_initialized = True
            else:
                self.redis_client = None
        except Exception as e:
            print(f"Redis not available for payment security: {e}")
            self.redis_client = None
            self._redis_initialized = True
    
    def generate_secure_token(self, length=32):
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data):
        """Create hash of sensitive data for storage"""
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True)
        return hashlib.sha256(str(data).encode()).hexdigest()
    
    def verify_webhook_signature(self, payload, signature, secret, algorithm='sha256'):
        """Verify webhook signature using HMAC"""
        try:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.new(algorithm)
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False
    
    def check_rate_limit(self, identifier, limit=60, window=60):
        """
        Check rate limiting for payment operations
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
        """
        self._initialize_redis()
        if not self.redis_client:
            return True  # Allow if Redis not available
        
        try:
            key = f"payment_rate_limit:{identifier}:{int(time.time() // window)}"
            current_requests = self.redis_client.get(key)
            
            if current_requests is None:
                self.redis_client.setex(key, window, 1)
                return True
            elif int(current_requests) < limit:
                self.redis_client.incr(key)
                return True
            else:
                return False
        except Exception as e:
            current_app.logger.error(f"Rate limit check failed: {e}")
            return True  # Allow on error
    
    def check_ip_whitelist(self, ip_address, allowed_ips):
        """Check if IP address is in whitelist"""
        if not allowed_ips:
            return True
        
        return ip_address in allowed_ips
    
    def validate_card_number(self, card_number):
        """Validate credit card number using Luhn algorithm"""
        if not card_number or not card_number.isdigit():
            return False
        
        # Remove spaces and dashes
        card_number = re.sub(r'[\s-]', '', card_number)
        
        if len(card_number) < 13 or len(card_number) > 19:
            return False
        
        # Luhn algorithm
        total = 0
        reverse_digits = card_number[::-1]
        
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:  # Every second digit
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        return total % 10 == 0
    
    def mask_sensitive_data(self, data_type, value):
        """
        Mask sensitive payment data for logging
        
        Args:
            data_type: Type of data ('card_number', 'cvv', 'pin', etc.)
            value: The value to mask
        """
        if not value:
            return value
        
        if data_type == 'card_number':
            # Mask all but last 4 digits
            if len(value) > 4:
                return '*' * (len(value) - 4) + value[-4:]
            return '*' * len(value)
        
        elif data_type == 'cvv':
            # Mask CVV completely
            return '*' * len(value)
        
        elif data_type == 'pin':
            # Mask PIN completely
            return '*' * len(value)
        
        elif data_type == 'email':
            # Mask email partially
            if '@' in value:
                username, domain = value.split('@', 1)
                if len(username) <= 2:
                    masked_username = username[0] + '*'
                else:
                    masked_username = username[:2] + '*' * (len(username) - 2)
                return f"{masked_username}@{domain}"
            return '*' * len(value)
        
        elif data_type == 'mobile':
            # Mask mobile number except last 2 digits
            if len(value) >= 4:
                return '*' * (len(value) - 2) + value[-2:]
            return '*' * len(value)
        
        else:
            # Generic masking
            return '*' * len(value)
    
    def encrypt_sensitive_field(self, value):
        """Encrypt sensitive field using encryption manager"""
        from utils.encryption import get_encryption_manager
        return get_encryption_manager().encrypt_field(value)
    
    def decrypt_sensitive_field(self, encrypted_value):
        """Decrypt sensitive field using encryption manager"""
        from utils.encryption import get_encryption_manager
        return get_encryption_manager().decrypt_field(encrypted_value)
    
    def validate_amount(self, amount):
        """Validate payment amount"""
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return False, "Amount must be positive"
            
            # Check for reasonable limits
            if amount > Decimal('999999.99'):
                return False, "Amount exceeds maximum limit"
            
            if amount < Decimal('0.01'):
                return False, "Amount below minimum limit"
            
            return True, "Valid amount"
        except Exception:
            return False, "Invalid amount format"
    
    def validate_currency(self, currency):
        """Validate currency code"""
        supported_currencies = ['INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD']
        return currency.upper() in supported_currencies
    
    def check_suspicious_patterns(self, payment_data):
        """
        Check for suspicious payment patterns
        
        Args:
            payment_data: Dictionary containing payment information
            
        Returns:
            tuple: (is_suspicious, reasons)
        """
        self._initialize_redis()
        suspicious_reasons = []
        
        # Check for multiple rapid transactions
        user_id = payment_data.get('user_id')
        if user_id and self.redis_client:
            key = f"user_transactions:{user_id}:{datetime.now().strftime('%Y%m%d')}"
            try:
                count = self.redis_client.get(key)
                if count and int(count) > 10:  # More than 10 transactions per day
                    suspicious_reasons.append("High transaction frequency")
            except Exception:
                pass
        
        # Check for unusual amount patterns
        amount = payment_data.get('amount')
        if amount:
            try:
                amount_decimal = Decimal(str(amount))
                if amount_decimal % 1 == 0:  # Round numbers
                    suspicious_reasons.append("Round number amount")
                if amount_decimal > Decimal('50000'):  # High amount
                    suspicious_reasons.append("High transaction amount")
            except Exception:
                pass
        
        # Check for repeated failed attempts
        gateway_transaction_id = payment_data.get('gateway_transaction_id')
        if gateway_transaction_id and self.redis_client:
            key = f"failed_transactions:{gateway_transaction_id}"
            try:
                failures = self.redis_client.get(key)
                if failures and int(failures) > 3:
                    suspicious_reasons.append("Multiple failed attempts")
            except Exception:
                pass
        
        is_suspicious = len(suspicious_reasons) > 0
        return is_suspicious, suspicious_reasons
    
    def log_security_event(self, event_type, details):
        """
        Log security-related events
        
        Args:
            event_type: Type of security event
            details: Event details dictionary
        """
        try:
            # Create log entry
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'details': details,
                'ip_address': request.remote_addr if request else 'unknown',
                'user_agent': request.headers.get('User-Agent', 'unknown') if request else 'unknown'
            }
            
            # Log to application logger
            if hasattr(current_app, 'logger'):
                current_app.logger.warning(f"SECURITY_EVENT: {json.dumps(log_entry)}")
            else:
                print(f"SECURITY_EVENT: {json.dumps(log_entry)}")
            
            # Store in Redis for analysis
            if self.redis_client:
                key = f"security_events:{event_type}"
                self.redis_client.lpush(key, json.dumps(log_entry))
                self.redis_client.ltrim(key, 0, 999)  # Keep last 1000 events
                self.redis_client.expire(key, 86400)  # Expire after 24 hours
            
        except Exception as e:
            current_app.logger.error(f"Failed to log security event: {e}")
    
    def create_secure_session(self, user_id, duration_hours=24):
        """Create secure session for payment operations"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=duration_hours),
            'iat': datetime.utcnow(),
            'purpose': 'payment_session'
        }
        
        secret_key = current_app.config.get('SECRET_KEY')
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        return token
    
    def validate_secure_session(self, token):
        """Validate secure session token"""
        try:
            secret_key = current_app.config.get('SECRET_KEY')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Check if session is for payment purpose
            if payload.get('purpose') != 'payment_session':
                return False, None
            
            return True, payload.get('user_id')
        except jwt.ExpiredSignatureError:
            return False, "Session expired"
        except jwt.InvalidTokenError:
            return False, "Invalid session"
        except Exception as e:
            return False, f"Session validation error: {str(e)}"
    
    def sanitize_log_data(self, data):
        """
        Sanitize data for logging by removing sensitive information
        
        Args:
            data: Data to sanitize
            
        Returns:
            dict: Sanitized data
        """
        if not isinstance(data, dict):
            return data
        
        sensitive_fields = [
            'card_number', 'cvv', 'pin', 'password', 'api_key', 'secret_key',
            'webhook_secret', 'token', 'access_token', 'refresh_token'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_log_data(value)
            elif isinstance(value, list):
                sanitized[key] = [self.sanitize_log_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def check_compliance_requirements(self, payment_data):
        """
        Check PCI DSS and other compliance requirements
        
        Args:
            payment_data: Payment data dictionary
            
        Returns:
            dict: Compliance check results
        """
        results = {
            'compliant': True,
            'warnings': [],
            'errors': []
        }
        
        # Check data encryption
        if 'card_number' in payment_data:
            if not self._is_encrypted(payment_data['card_number']):
                results['errors'].append("Card number not encrypted")
                results['compliant'] = False
        
        # Check data retention
        retention_period = current_app.config.get('PAYMENT_DATA_RETENTION_DAYS', 365)
        if retention_period > 365:
            results['warnings'].append(f"Data retention period ({retention_period} days) exceeds recommended 365 days")
        
        # Check access controls
        user_role = payment_data.get('user_role')
        if user_role and user_role not in ['admin', 'payment_processor']:
            results['warnings'].append(f"User role '{user_role}' has payment access")
        
        # Check transaction limits
        amount = payment_data.get('amount')
        if amount:
            try:
                amount_decimal = Decimal(str(amount))
                daily_limit = current_app.config.get('DAILY_PAYMENT_LIMIT', Decimal('100000'))
                if amount_decimal > daily_limit:
                    results['warnings'].append(f"Amount exceeds daily limit")
            except Exception:
                pass
        
        return results
    
    def _is_encrypted(self, value):
        """Check if value appears to be encrypted"""
        if not isinstance(value, str):
            return False
        
        # Simple heuristic: encrypted values are typically longer and contain special characters
        return len(value) > 20 and any(c in value for c in ['=', '+', '/'])


# Decorators for payment security
def payment_security_required(f):
    """Decorator to require payment security validation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        security_manager = PaymentSecurityManager()
        
        # Check rate limiting
        client_ip = request.remote_addr
        if not security_manager.check_rate_limit(client_ip):
            security_manager.log_security_event('RATE_LIMIT_EXCEEDED', {
                'ip_address': client_ip,
                'endpoint': request.endpoint
            })
            return {'error': 'Rate limit exceeded'}, 429
        
        # Check for suspicious patterns
        payment_data = request.get_json() or {}
        payment_data['user_id'] = getattr(request, 'user_id', None)
        
        is_suspicious, reasons = security_manager.check_suspicious_patterns(payment_data)
        if is_suspicious:
            security_manager.log_security_event('SUSPICIOUS_ACTIVITY', {
                'ip_address': client_ip,
                'reasons': reasons,
                'payment_data': security_manager.sanitize_log_data(payment_data)
            })
        
        return f(*args, **kwargs)
    
    return decorated_function


def secure_payment_endpoint(f):
    """Decorator for secure payment endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        security_manager = PaymentSecurityManager()
        
        # Validate session if required
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            is_valid, user_id = security_manager.validate_secure_session(token)
            if not is_valid:
                security_manager.log_security_event('INVALID_SESSION', {
                    'token_hash': hashlib.sha256(token.encode()).hexdigest(),
                    'ip_address': request.remote_addr
                })
                return {'error': 'Invalid session'}, 401
        
        # Additional security checks can be added here
        return f(*args, **kwargs)
    
    return decorated_function


# Global security manager instance (initialized lazily)
_security_manager = None

def get_security_manager():
    """Get or create security manager instance"""
    global _security_manager
    if _security_manager is None:
        _security_manager = PaymentSecurityManager()
    return _security_manager