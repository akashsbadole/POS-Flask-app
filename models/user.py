from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from utils.encryption import get_encryption_manager
from . import db

class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    # Role constants for better maintainability
    ROLE_SUPER_ADMIN = 'super_admin'
    ROLE_ADMIN = 'admin'
    ROLE_MANAGER = 'manager'
    ROLE_HEAD_CHEF = 'head_chef'
    ROLE_CHEF = 'chef'
    ROLE_CASHIER = 'cashier'
    ROLE_WAITER = 'waiter'
    ROLE_KITCHEN_STAFF = 'kitchen_staff'
    ROLE_READONLY = 'readonly'
    
    # Role hierarchy for permission inheritance (higher index = higher privilege)
    ROLE_HIERARCHY = [
        ROLE_READONLY,
        ROLE_KITCHEN_STAFF,
        ROLE_WAITER,
        ROLE_CASHIER,
        ROLE_CHEF,
        ROLE_HEAD_CHEF,
        ROLE_MANAGER,
        ROLE_ADMIN,
        ROLE_SUPER_ADMIN
    ]
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cashier')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Profile management fields
    full_name = db.Column(db.String(120), nullable=True)
    avatar_path = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    
    # Phone verification fields
    phone_verified = db.Column(db.Boolean, default=False)
    phone_verification_token = db.Column(db.String(255), nullable=True)
    phone_verification_expires = db.Column(db.DateTime, nullable=True)
    phone_verification_attempts = db.Column(db.Integer, default=0)
    phone_verification_last_request = db.Column(db.DateTime, nullable=True)
    
    # Mobile OTP settings
    mobile_otp_enabled = db.Column(db.Boolean, default=False)
    backup_phone = db.Column(db.String(20), nullable=True)
    
    # Email OTP settings
    email_otp_enabled = db.Column(db.Boolean, default=False)
    backup_email = db.Column(db.String(120), nullable=True)
    
    # User preferences
    preferred_language = db.Column(db.String(10), default='en')
    preferred_timezone = db.Column(db.String(50), default='UTC')
    notification_preferences = db.Column(db.Text, default='{}')  # JSON string
    
    # Security and audit
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_password_change = db.Column(db.DateTime, default=datetime.utcnow)
    profile_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Password reset fields
    password_reset_token = db.Column(db.String(255), nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    password_reset_attempts = db.Column(db.Integer, default=0)
    password_reset_last_request = db.Column(db.DateTime, nullable=True)
    
    # Admin management fields
    account_status = db.Column(db.String(20), default='active')  # active, inactive, suspended
    admin_notes = db.Column(db.Text, nullable=True)  # Notes added by admin
    last_activity = db.Column(db.DateTime, nullable=True)  # Track user activity
    activity_count = db.Column(db.Integer, default=0)  # Number of activities
    password_expiry_date = db.Column(db.DateTime, nullable=True)  # Force password change
    must_change_password = db.Column(db.Boolean, default=False)
    
    # Relationships
    orders = db.relationship('Order', backref='created_by_user', lazy=True)
    
    def __init__(self, username, password, role='cashier', email=None):
        self.username = username
        self.email = self._encrypt_email(email) if email else None
        self.role = role
        self.set_password(password)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = self._encrypt_password_hash(generate_password_hash(password))
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        decrypted_hash = self._decrypt_password_hash(self.password_hash)
        return check_password_hash(decrypted_hash, password)
    
    def is_super_admin(self):
        """Check if user is super admin"""
        return self.role == self.ROLE_SUPER_ADMIN
    
    def is_admin(self):
        """Check if user is admin or super admin"""
        return self.role in [self.ROLE_ADMIN, self.ROLE_SUPER_ADMIN]
    
    def is_manager(self):
        """Check if user is manager or higher"""
        return self.role in [self.ROLE_MANAGER, self.ROLE_HEAD_CHEF, self.ROLE_ADMIN, self.ROLE_SUPER_ADMIN]
    
    def is_chef(self):
        """Check if user is chef or higher"""
        return self.role in [self.ROLE_CHEF, self.ROLE_HEAD_CHEF, self.ROLE_MANAGER, self.ROLE_ADMIN, self.ROLE_SUPER_ADMIN]
    
    def is_head_chef(self):
        """Check if user is head chef or higher"""
        return self.role in [self.ROLE_HEAD_CHEF, self.ROLE_MANAGER, self.ROLE_ADMIN, self.ROLE_SUPER_ADMIN]
    
    def is_kitchen_staff(self):
        """Check if user is kitchen staff or higher"""
        return self.role in [self.ROLE_KITCHEN_STAFF, self.ROLE_CHEF, self.ROLE_HEAD_CHEF, self.ROLE_MANAGER, self.ROLE_ADMIN, self.ROLE_SUPER_ADMIN]
    
    def is_waiter(self):
        """Check if user is waiter or higher"""
        return self.role in [self.ROLE_WAITER, self.ROLE_CASHIER, self.ROLE_CHEF, self.ROLE_HEAD_CHEF, self.ROLE_MANAGER, self.ROLE_ADMIN, self.ROLE_SUPER_ADMIN]
    
    def is_cashier(self):
        """Check if user is cashier or higher"""
        return self.role in [self.ROLE_CASHIER, self.ROLE_CHEF, self.ROLE_HEAD_CHEF, self.ROLE_MANAGER, self.ROLE_ADMIN, self.ROLE_SUPER_ADMIN]
    
    def get_role_level(self):
        """Get numeric role level (higher number = higher privilege)"""
        try:
            return self.ROLE_HIERARCHY.index(self.role)
        except ValueError:
            return 0  # Unknown role gets lowest level
    
    def has_role_or_higher(self, required_role):
        """Check if user has required role or higher privilege"""
        user_level = self.get_role_level()
        required_level = self.ROLE_HIERARCHY.index(required_role) if required_role in self.ROLE_HIERARCHY else 0
        return user_level >= required_level
    
    @staticmethod
    def get_valid_roles():
        """Get list of all valid roles"""
        return User.ROLE_HIERARCHY.copy()
    
    @staticmethod
    def get_admin_manageable_roles(admin_user):
        """Get roles that an admin can assign to users"""
        if not admin_user or not admin_user.is_admin():
            return []
        
        if admin_user.is_super_admin():
            return User.ROLE_HIERARCHY.copy()
        
        # Regular admin cannot assign admin or super_admin roles
        admin_level = User.ROLE_HIERARCHY.index('admin')
        return User.ROLE_HIERARCHY[:admin_level]  # All roles below admin
    
    @staticmethod
    def get_users_for_admin(admin_user, include_inactive=True):
        """Get users that can be managed by this admin"""
        if not admin_user or not admin_user.is_admin():
            return []
        
        if admin_user.is_super_admin():
            if include_inactive:
                return User.query.all()
            else:
                return User.query.filter(User.is_active == True).all()
        
        # Regular admin cannot see other admins
        query = User.query.filter(User.role.notin_(['admin', 'super_admin']))
        
        if not include_inactive:
            query = query.filter(User.is_active == True)
        
        return query.all()
    
    @staticmethod
    def search_users(search_term, admin_user=None, include_inactive=True):
        """Search users based on various criteria"""
        if not admin_user or not admin_user.is_admin():
            return []
        
        query = User.query
        
        # Regular admin cannot see other admins
        if not admin_user.is_super_admin():
            query = query.filter(User.role.notin_(['admin', 'super_admin']))
        
        if not include_inactive:
            query = query.filter(User.is_active == True)
        
        # Search in username, email, and full name
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                db.or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),  # This will work with encrypted emails
                    User.full_name.ilike(search_pattern)
                )
            )
        
        return query.all()
    
    @staticmethod
    def bulk_update_users(user_ids, update_data, admin_user=None):
        """Bulk update multiple users"""
        if not admin_user or not admin_user.is_admin():
            return False, "Insufficient permissions"
        
        updated_count = 0
        errors = []
        
        for user_id in user_ids:
            try:
                user = User.query.get(user_id)
                if not user or not user.can_be_managed_by(admin_user):
                    errors.append(f"Cannot manage user ID {user_id}")
                    continue
                
                # Apply updates
                if 'account_status' in update_data:
                    success, message = user.change_account_status(
                        update_data['account_status'],
                        f"Bulk update by {admin_user.username}",
                        admin_user
                    )
                    if not success:
                        errors.append(f"User {user.username}: {message}")
                        continue
                
                if 'role' in update_data and update_data['role'] != user.role:
                    success, message = user.change_role(
                        update_data['role'],
                        f"Bulk update by {admin_user.username}",
                        admin_user
                    )
                    if not success:
                        errors.append(f"User {user.username}: {message}")
                        continue
                
                if 'is_active' in update_data and update_data['is_active'] != user.is_active:
                    if update_data['is_active']:
                        success, message = user.activate(
                            f"Bulk update by {admin_user.username}",
                            admin_user
                        )
                    else:
                        success, message = user.deactivate(
                            f"Bulk update by {admin_user.username}",
                            admin_user
                        )
                    if not success:
                        errors.append(f"User {user.username}: {message}")
                        continue
                
                updated_count += 1
                
            except Exception as e:
                errors.append(f"User ID {user_id}: {str(e)}")
        
        return True, f"Updated {updated_count} users" + (" with " + ", ".join(errors) if errors else "")
    
    @staticmethod
    def get_role_display_name(role):
        """Get human-readable role name"""
        role_names = {
            'super_admin': 'Super Admin',
            'admin': 'Admin',
            'manager': 'Manager',
            'head_chef': 'Head Chef',
            'chef': 'Chef',
            'cashier': 'Cashier',
            'waiter': 'Waiter',
            'kitchen_staff': 'Kitchen Staff',
            'readonly': 'Read Only'
        }
        return role_names.get(role, role.title())
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def update_profile(self, **kwargs):
        """Update user profile fields"""
        allowed_fields = [
            'full_name', 'phone', 'address', 'bio', 'date_of_birth',
            'preferred_language', 'preferred_timezone'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == 'date_of_birth' and isinstance(value, str):
                    # Parse date string to datetime.date
                    try:
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    except ValueError:
                        continue
                setattr(self, field, value)
        
        self.profile_updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_notification_preferences(self):
        """Get notification preferences as dictionary"""
        if not self.notification_preferences or self.notification_preferences == '{}':
            return {
                'email_notifications': True,
                'order_updates': True,
                'marketing_emails': False,
                'system_alerts': True
            }
        
        import json
        try:
            return json.loads(self.notification_preferences)
        except (json.JSONDecodeError, TypeError):
            return {
                'email_notifications': True,
                'order_updates': True,
                'marketing_emails': False,
                'system_alerts': True
            }
    
    def set_notification_preferences(self, preferences):
        """Set notification preferences from dictionary"""
        import json
        self.notification_preferences = json.dumps(preferences)
        db.session.commit()
    
    def update_avatar(self, avatar_path):
        """Update user avatar path"""
        self.avatar_path = avatar_path
        self.profile_updated_at = datetime.utcnow()
        db.session.commit()
    
    # Phone verification methods
    def generate_phone_verification_token(self):
        """Generate a secure phone verification token"""
        import secrets
        import string
        
        # Generate a secure token
        token = secrets.token_urlsafe(32)
        
        # Set token expiration to 24 hours from now
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Update user with token and expiration
        self.phone_verification_token = token
        self.phone_verification_expires = expires_at
        self.phone_verification_last_request = datetime.utcnow()
        
        db.session.commit()
        
        return token
    
    def validate_phone_verification_token(self, token):
        """Validate phone verification token"""
        if not self.phone_verification_token or not self.phone_verification_expires:
            return False, "No verification token found"
        
        # Check if token matches
        if self.phone_verification_token != token:
            return False, "Invalid token"
        
        # Check if token has expired
        if datetime.utcnow() > self.phone_verification_expires:
            self.clear_phone_verification_token()
            db.session.commit()
            return False, "Token has expired"
        
        return True, "Token is valid"
    
    def increment_phone_verification_attempts(self):
        """Increment phone verification attempts for rate limiting"""
        self.phone_verification_attempts += 1
        self.phone_verification_last_request = datetime.utcnow()
        db.session.commit()
    
    def can_request_phone_verification(self):
        """Check if user can request phone verification (rate limiting)"""
        # Check if rate limit is exceeded
        if self.phone_verification_attempts >= 3:
            # Check if 1 hour has passed since last request
            if self.phone_verification_last_request:
                time_since_last = datetime.utcnow() - self.phone_verification_last_request
                if time_since_last < timedelta(hours=1):
                    remaining_time = timedelta(hours=1) - time_since_last
                    return False, f"Too many verification attempts. Try again in {int(remaining_time.total_seconds() / 60)} minutes"
        
        return True, "Can request verification"
    
    def clear_phone_verification_token(self):
        """Clear phone verification token after successful verification or expiration"""
        self.phone_verification_token = None
        self.phone_verification_expires = None
        self.phone_verification_attempts = 0
        self.phone_verification_last_request = None
        db.session.commit()
    
    def verify_phone_number(self, token):
        """Verify phone number using verification token"""
        # Validate token
        is_valid, message = self.validate_phone_verification_token(token)
        if not is_valid:
            return False, message
        
        # Mark phone as verified
        self.phone_verified = True
        self.phone_verification_attempts = 0
        
        # Clear verification token
        self.clear_phone_verification_token()
        
        db.session.commit()
        
        return True, "Phone number verified successfully"
    
    def update_phone_number(self, new_phone):
        """Update phone number (requires re-verification)"""
        self.phone = new_phone
        self.phone_verified = False
        self.clear_phone_verification_token()
        db.session.commit()
        
        return self.generate_phone_verification_token()
    
    def toggle_mobile_otp(self, enabled):
        """Toggle mobile OTP for this user"""
        if not self.phone_verified:
            return False, "Cannot enable mobile OTP for unverified phone number"
        
        self.mobile_otp_enabled = enabled
        db.session.commit()
        
        return True, f"Mobile OTP {'enabled' if enabled else 'disabled'} successfully"
    
    def get_phone_verification_info(self):
        """Get phone verification information for logging/monitoring"""
        return {
            'phone': self.phone,
            'phone_verified': self.phone_verified,
            'has_active_token': bool(self.phone_verification_token and self.phone_verification_expires),
            'token_expires_at': self.phone_verification_expires.isoformat() if self.phone_verification_expires else None,
            'last_verification_request': self.phone_verification_last_request.isoformat() if self.phone_verification_last_request else None,
            'verification_attempts': self.phone_verification_attempts,
            'can_request_verification': self.can_request_phone_verification()[0],
            'mobile_otp_enabled': self.mobile_otp_enabled
        }
    
    def get_profile_completion_percentage(self):
        """Calculate profile completion percentage"""
        required_fields = ['full_name', 'email_decrypted', 'phone']
        optional_fields = ['address', 'bio', 'date_of_birth', 'avatar_path']
        
        completed_required = sum(1 for field in required_fields if getattr(self, field))
        completed_optional = sum(1 for field in optional_fields if getattr(self, field))
        
        total_required = len(required_fields)
        total_optional = len(optional_fields)
        
        # Required fields weigh 70%, optional fields weigh 30%
        required_percentage = (completed_required / total_required) * 70 if total_required > 0 else 0
        optional_percentage = (completed_optional / total_optional) * 30 if total_optional > 0 else 0
        
        return min(int(required_percentage + optional_percentage), 100)
    
    def increment_failed_login_attempts(self):
        """Increment failed login attempts and lock account if necessary"""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts for 30 minutes
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
        
        db.session.commit()
    
    def reset_failed_login_attempts(self):
        """Reset failed login attempts counter"""
        self.failed_login_attempts = 0
        self.locked_until = None
        db.session.commit()
    
    def is_account_locked(self):
        """Check if account is currently locked"""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
    
    def update_password(self, new_password):
        """Update user password with security checks"""
        self.set_password(new_password)
        self.last_password_change = datetime.utcnow()
        self.reset_failed_login_attempts()
        self.clear_password_reset_token()  # Clear any pending reset tokens
        db.session.commit()
    
    def generate_password_reset_token(self):
        """Generate a secure password reset token"""
        import secrets
        import string
        
        # Generate a secure token
        token = secrets.token_urlsafe(32)
        
        # Set token expiration to 1 hour from now
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Update user with token and expiration
        self.password_reset_token = token
        self.password_reset_expires = expires_at
        self.password_reset_last_request = datetime.utcnow()
        
        db.session.commit()
        
        return token
    
    def validate_password_reset_token(self, token):
        """Validate password reset token"""
        if not self.password_reset_token or not self.password_reset_expires:
            return False, "No reset token found"
        
        # Check if token matches
        if self.password_reset_token != token:
            return False, "Invalid token"
        
        # Check if token has expired
        if datetime.utcnow() > self.password_reset_expires:
            self.clear_password_reset_token()
            db.session.commit()
            return False, "Token has expired"
        
        return True, "Token is valid"
    
    def increment_password_reset_attempts(self):
        """Increment password reset attempts for rate limiting"""
        self.password_reset_attempts += 1
        self.password_reset_last_request = datetime.utcnow()
        db.session.commit()
    
    def can_request_password_reset(self):
        """Check if user can request a password reset (rate limiting)"""
        # Check if account is locked
        if self.is_account_locked():
            return False, "Account is locked"
        
        # Check if rate limit is exceeded
        if self.password_reset_attempts >= 3:
            # Check if 1 hour has passed since last request
            if self.password_reset_last_request:
                time_since_last = datetime.utcnow() - self.password_reset_last_request
                if time_since_last < timedelta(hours=1):
                    remaining_time = timedelta(hours=1) - time_since_last
                    return False, f"Too many reset attempts. Try again in {int(remaining_time.total_seconds() / 60)} minutes"
        
        return True, "Can request reset"
    
    def clear_password_reset_token(self):
        """Clear password reset token after successful reset or expiration"""
        self.password_reset_token = None
        self.password_reset_expires = None
        self.password_reset_attempts = 0
        self.password_reset_last_request = None
        db.session.commit()
    
    def reset_password_with_token(self, token, new_password):
        """Reset password using reset token"""
        # Validate token
        is_valid, message = self.validate_password_reset_token(token)
        if not is_valid:
            return False, message
        
        # Update password
        self.set_password(new_password)
        self.last_password_change = datetime.utcnow()
        
        # Clear reset token and attempts
        self.clear_password_reset_token()
        
        # Reset failed login attempts
        self.reset_failed_login_attempts()
        
        db.session.commit()
        
        return True, "Password reset successfully"
    
    def get_password_reset_info(self):
        """Get password reset information for logging/monitoring"""
        return {
            'has_active_token': bool(self.password_reset_token and self.password_reset_expires),
            'token_expires_at': self.password_reset_expires.isoformat() if self.password_reset_expires else None,
            'last_reset_request': self.password_reset_last_request.isoformat() if self.password_reset_last_request else None,
            'reset_attempts': self.password_reset_attempts,
            'can_request_reset': self.can_request_password_reset()[0]
        }
    
    # Admin Management Methods
    def can_be_managed_by(self, admin_user):
        """Check if this user can be managed by the specified admin"""
        if not admin_user or not admin_user.is_admin():
            return False
        
        # Super admin can manage everyone
        if admin_user.is_super_admin():
            return True
        
        # Regular admin cannot manage other admins or super admins
        if self.is_admin():
            return False
        
        return True
    
    def change_account_status(self, new_status, admin_notes=None, admin_user=None):
        """Change user account status with admin tracking"""
        valid_statuses = ['active', 'inactive', 'suspended']
        if new_status not in valid_statuses:
            return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        
        old_status = self.account_status
        self.account_status = new_status
        
        if new_status == 'inactive':
            self.is_active = False
        elif new_status == 'active':
            self.is_active = True
        
        if admin_notes:
            admin_note = f"[{datetime.utcnow().isoformat()}] {admin_user.username}: {admin_notes}"
            if self.admin_notes:
                self.admin_notes = f"{self.admin_notes}\n{admin_note}"
            else:
                self.admin_notes = admin_note
        
        db.session.commit()
        
        # Log the action
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User {admin_user.username if admin_user else 'System'} changed account status for {self.username} from {old_status} to {new_status}")
        
        return True, "Account status updated successfully"
    
    def change_role(self, new_role, admin_notes=None, admin_user=None):
        """Change user role with admin tracking"""
        if new_role not in self.get_valid_roles():
            return False, "Invalid role specified"
        
        old_role = self.role
        self.role = new_role
        
        # If role changed and user is active, ensure is_active is True
        if new_role != 'readonly':
            self.is_active = True
            self.account_status = 'active'
        
        if admin_notes:
            admin_note = f"[{datetime.utcnow().isoformat()}] {admin_user.username}: Role changed from {old_role} to {new_role}. {admin_notes}"
            if self.admin_notes:
                self.admin_notes = f"{self.admin_notes}\n{admin_note}"
            else:
                self.admin_notes = admin_note
        
        db.session.commit()
        
        # Log the action
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User {admin_user.username if admin_user else 'System'} changed role for {self.username} from {old_role} to {new_role}")
        
        return True, "Role updated successfully"
    
    def activate(self, admin_notes=None, admin_user=None):
        """Activate user account"""
        return self.change_account_status('active', admin_notes, admin_user)
    
    def deactivate(self, admin_notes=None, admin_user=None):
        """Deactivate user account"""
        return self.change_account_status('inactive', admin_notes, admin_user)
    
    def suspend(self, admin_notes=None, admin_user=None):
        """Suspend user account"""
        return self.change_account_status('suspended', admin_notes, admin_user)
    
    def toggle_status(self, admin_notes=None, admin_user=None):
        """Toggle between active and inactive status"""
        if self.account_status == 'active':
            return self.change_account_status('inactive', admin_notes, admin_user)
        else:
            return self.change_account_status('active', admin_notes, admin_user)
    
    def unlock_account(self, admin_user=None):
        """Unlock user account (reset failed attempts)"""
        self.reset_failed_login_attempts()
        self.locked_until = None
        db.session.commit()
        
        # Log the action
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User {admin_user.username if admin_user else 'System'} unlocked account for {self.username}")
        
        return True, "Account unlocked successfully"
    
    def force_password_change(self, admin_user=None):
        """Force user to change password on next login"""
        self.must_change_password = True
        self.password_expiry_date = datetime.utcnow() + timedelta(days=30)  # 30 days to change
        db.session.commit()
        
        # Log the action
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User {admin_user.username if admin_user else 'System'} forced password change for {self.username}")
        
        return True, "Password change forced successfully"
    
    def update_activity(self, activity_type='login'):
        """Update user activity tracking"""
        self.last_activity = datetime.utcnow()
        self.activity_count += 1
        
        if activity_type == 'login':
            self.update_last_login()
        
        db.session.commit()
    
    def get_admin_summary(self):
        """Get summary information for admin management"""
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email_decrypted,
            'role': self.role,
            'role_display_name': self.get_role_display_name(self.role),
            'role_level': self.get_role_level(),
            'account_status': self.account_status,
            'is_active': self.is_active,
            'is_admin': self.is_admin(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'activity_count': self.activity_count,
            'failed_login_attempts': self.failed_login_attempts,
            'is_account_locked': self.is_account_locked(),
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'must_change_password': self.must_change_password,
            'admin_notes': self.admin_notes
        }
    
    @staticmethod
    def cleanup_expired_tokens():
        """Clean up expired password reset tokens (for scheduled tasks)"""
        expired_users = User.query.filter(
            User.password_reset_expires < datetime.utcnow()
        ).all()
        
        for user in expired_users:
            user.clear_password_reset_token()
        
        return len(expired_users)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self._decrypt_email(self.email),
            'full_name': self.full_name,
            'phone': self.phone,
            'address': self.address,
            'bio': self.bio,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'avatar_path': self.avatar_path,
            'preferred_language': self.preferred_language,
            'preferred_timezone': self.preferred_timezone,
            'role': self.role,
            'role_display_name': self.get_role_display_name(self.role),
            'role_level': self.get_role_level(),
            'is_active': self.is_active,
            'account_status': self.account_status,
            'is_admin': self.is_admin(),
            'is_manager': self.is_manager(),
            'is_chef': self.is_chef(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'activity_count': self.activity_count,
            'last_password_change': self.last_password_change.isoformat() if self.last_password_change else None,
            'profile_updated_at': self.profile_updated_at.isoformat() if self.profile_updated_at else None,
            'profile_completion_percentage': self.get_profile_completion_percentage(),
            'failed_login_attempts': self.failed_login_attempts,
            'is_account_locked': self.is_account_locked(),
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'must_change_password': self.must_change_password,
            'password_expiry_date': self.password_expiry_date.isoformat() if self.password_expiry_date else None,
            'admin_notes': self.admin_notes
        }
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_by_email_encrypted(email_input):
        """Get user by email (decrypting stored emails for lookup)"""
        # Get all users and check if any match the email
        users = User.query.filter(User.email.isnot(None)).all()
        
        for user in users:
            if user.email_decrypted.lower() == email_input.lower():
                return user
        
        return None
    
    @staticmethod
    def create_user(username, password, role='cashier', email=None):
        """Create new user"""
        if User.query.filter_by(username=username).first():
            return None
        user = User(username, password, role, email)
        db.session.add(user)
        db.session.commit()
        return user
    
    def _encrypt_email(self, email):
        """Encrypt email address"""
        if not email:
            return None
        return get_encryption_manager().encrypt_field(email)
    
    def _decrypt_email(self, encrypted_email):
        """Decrypt email address"""
        if not encrypted_email:
            return None
        return get_encryption_manager().decrypt_field(encrypted_email)
    
    def _encrypt_password_hash(self, password_hash):
        """Encrypt password hash"""
        if not password_hash:
            return None
        return get_encryption_manager().encrypt_field(password_hash)
    
    def _decrypt_password_hash(self, encrypted_password_hash):
        """Decrypt password hash"""
        if not encrypted_password_hash:
            return None
        return get_encryption_manager().decrypt_field(encrypted_password_hash)
    
    @property
    def email_decrypted(self):
        """Get decrypted email address"""
        return self._decrypt_email(self.email)
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
