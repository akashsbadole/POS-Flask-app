from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from . import db
import secrets
import string

class OTP(db.Model):
    """OTP model for phone and email verification"""
    __tablename__ = 'otps'
    
    # OTP types
    TYPE_LOGIN = 'login'
    TYPE_MOBILE_LOGIN = 'mobile_login'
    TYPE_PHONE_VERIFICATION = 'phone_verification'
    TYPE_EMAIL_VERIFICATION = 'email_verification'
    TYPE_PASSWORD_RESET = 'password_reset'
    TYPE_EMAIL_LOGIN = 'email_login'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    otp_code = db.Column(db.String(6), nullable=False)
    otp_type = db.Column(db.String(20), nullable=False, default=TYPE_LOGIN)
    is_used = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('otps', lazy=True, cascade='all, delete-orphan'))
    
    def __init__(self, user_id, phone=None, email=None, otp_type=TYPE_LOGIN, max_attempts=3):
        self.user_id = user_id
        self.phone = phone
        self.email = email
        self.otp_type = otp_type
        self.max_attempts = max_attempts
        self.otp_code = self.generate_otp()
        self.expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes expiry
        self.is_used = False
        self.attempts = 0
    
    @staticmethod
    def generate_otp():
        """Generate a 6-digit OTP"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    def is_expired(self):
        """Check if OTP is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_max_attempts_reached(self):
        """Check if maximum attempts reached"""
        return self.attempts >= self.max_attempts
    
    def can_attempt(self):
        """Check if OTP can still be attempted"""
        return not self.is_used and not self.is_expired() and not self.is_max_attempts_reached()
    
    def verify_otp(self, input_code, ip_address=None, user_agent=None):
        """Verify the OTP code"""
        # Update IP and user agent on first verification attempt
        if self.attempts == 0:
            if ip_address:
                self.ip_address = ip_address
            if user_agent:
                self.user_agent = user_agent
        
        # Increment attempts
        self.attempts += 1
        
        # Check if OTP can be attempted
        if not self.can_attempt():
            db.session.commit()
            return False, "OTP has expired or maximum attempts reached"
        
        # Check if code matches
        if self.otp_code == input_code:
            self.is_used = True
            self.used_at = datetime.utcnow()
            db.session.commit()
            return True, "OTP verified successfully"
        
        # Code doesn't match
        db.session.commit()
        if self.is_max_attempts_reached():
            return False, "Maximum attempts reached. Please request a new OTP"
        else:
            remaining_attempts = self.max_attempts - self.attempts
            return False, f"Invalid OTP. {remaining_attempts} attempts remaining"
    
    def mark_as_used(self):
        """Manually mark OTP as used"""
        self.is_used = True
        self.used_at = datetime.utcnow()
        db.session.commit()
    
    def resend(self):
        """Generate a new OTP (for resend functionality)"""
        if self.is_used:
            return False, "Cannot resend used OTP"
        
        if self.is_expired():
            return False, "Cannot resend expired OTP"
        
        # Generate new OTP code
        self.otp_code = self.generate_otp()
        self.expires_at = datetime.utcnow() + timedelta(minutes=10)
        self.attempts = 0  # Reset attempts
        db.session.commit()
        
        return True, "New OTP generated successfully"
    
    def to_dict(self):
        """Convert OTP to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'phone': self.phone,
            'email': self.email,
            'otp_type': self.otp_type,
            'is_used': self.is_used,
            'attempts': self.attempts,
            'max_attempts': self.max_attempts,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'is_expired': self.is_expired(),
            'can_attempt': self.can_attempt()
        }
    
    def __repr__(self):
        return f'<OTP {self.otp_code} for user {self.user_id}>'

class OTPRateLimit(db.Model):
    """Rate limiting for OTP requests"""
    __tablename__ = 'otp_rate_limits'
    
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=True, unique=True)
    email = db.Column(db.String(120), nullable=True, unique=True)
    ip_address = db.Column(db.String(45), nullable=True)
    request_count = db.Column(db.Integer, default=0)
    window_start = db.Column(db.DateTime, default=datetime.utcnow)
    last_request = db.Column(db.DateTime, default=datetime.utcnow)
    blocked_until = db.Column(db.DateTime, nullable=True)
    
    # Rate limiting constants
    MAX_REQUESTS_PER_HOUR = 5
    MAX_REQUESTS_PER_DAY = 10
    BLOCK_DURATION_MINUTES = 60
    
    WINDOW_SIZE_HOURS = 1
    DAILY_WINDOW_HOURS = 24
    
    def __init__(self, phone=None, email=None, ip_address=None):
        self.phone = phone
        self.email = email
        self.ip_address = ip_address
        self.request_count = 1
        self.window_start = datetime.utcnow()
        self.last_request = datetime.utcnow()
    
    def can_request_otp(self):
        """Check if OTP request is allowed based on rate limits"""
        now = datetime.utcnow()
        
        # Check if currently blocked
        if self.blocked_until and now < self.blocked_until:
            return False, f"Rate limit exceeded. Try again after {self.blocked_until.strftime('%H:%M:%S')}"
        
        # Reset counters if window has passed
        if now >= self.window_start + timedelta(hours=self.WINDOW_SIZE_HOURS):
            self.request_count = 1
            self.window_start = now
        elif now >= self.window_start + timedelta(hours=self.DAILY_WINDOW_HOURS):
            self.request_count = 1
            self.window_start = now
        
        # Check hourly limit
        if self.request_count >= self.MAX_REQUESTS_PER_HOUR:
            # Block for the specified duration
            self.blocked_until = now + timedelta(minutes=self.BLOCK_DURATION_MINUTES)
            db.session.commit()
            return False, f"Too many OTP requests. Try again after {self.blocked_until.strftime('%H:%M:%S')}"
        
        # Check daily limit
        daily_requests = self.get_daily_request_count()
        if daily_requests >= self.MAX_REQUESTS_PER_DAY:
            return False, "Daily OTP request limit exceeded. Try again tomorrow."
        
        return True, "OTP request allowed"
    
    def record_request(self):
        """Record an OTP request"""
        self.request_count += 1
        self.last_request = datetime.utcnow()
        db.session.commit()
    
    def get_daily_request_count(self):
        """Get number of requests in the last 24 hours"""
        since = datetime.utcnow() - timedelta(hours=self.DAILY_WINDOW_HOURS)
        query = OTP.query.filter(OTP.created_at >= since)
        
        # Filter by phone or email based on what's set
        if self.phone:
            query = query.filter(OTP.phone == self.phone)
        elif self.email:
            query = query.filter(OTP.email == self.email)
        
        daily_otps = query.count()
        return daily_otps
    
    def reset_limits(self):
        """Reset rate limits (admin function)"""
        self.request_count = 0
        self.window_start = datetime.utcnow()
        self.blocked_until = None
        db.session.commit()
    
    @staticmethod
    def get_or_create_rate_limit(phone=None, email=None, ip_address=None):
        """Get existing rate limit or create new one"""
        # Check if we have a phone rate limit
        if phone:
            rate_limit = OTPRateLimit.query.filter_by(phone=phone).first()
        elif email:
            # Check if we have an email rate limit
            rate_limit = OTPRateLimit.query.filter_by(email=email).first()
        else:
            rate_limit = None
        
        if not rate_limit:
            rate_limit = OTPRateLimit(phone=phone, email=email, ip_address=ip_address)
            db.session.add(rate_limit)
            db.session.commit()
        
        return rate_limit
    
    @staticmethod
    def cleanup_expired_limits():
        """Clean up old rate limit records (for scheduled tasks)"""
        # Remove rate limits older than 7 days with no recent activity
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        expired_limits = OTPRateLimit.query.filter(
            OTPRateLimit.last_request < cutoff_date,
            OTPRateLimit.blocked_until.is_(None)
        ).all()
        
        for limit in expired_limits:
            db.session.delete(limit)
        
        db.session.commit()
        return len(expired_limits)
    
    def to_dict(self):
        """Convert rate limit to dictionary"""
        return {
            'phone': self.phone,
            'email': self.email,
            'ip_address': self.ip_address,
            'request_count': self.request_count,
            'window_start': self.window_start.isoformat() if self.window_start else None,
            'last_request': self.last_request.isoformat() if self.last_request else None,
            'blocked_until': self.blocked_until.isoformat() if self.blocked_until else None,
            'can_request': self.can_request_otp()[0]
        }
    
    def __repr__(self):
        return f'<OTPRateLimit for {self.phone}>'