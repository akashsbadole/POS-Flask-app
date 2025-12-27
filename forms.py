from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, DateField, SelectField, FileField
from wtforms.validators import DataRequired, Length, ValidationError, Email, EqualTo, Optional, Regexp
from models import User
import re

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember me')
    submit = SubmitField('Sign In')
    user = None
    
    def validate_username(self, username):
        user = User.get_by_username(username.data)
        if not user:
            raise ValidationError('Username does not exist')
        self.user = user
    
    def validate_password(self, password):
        if self.user and not self.user.check_password(password.data):
            raise ValidationError('Password is incorrect')

class ProfileEditForm(FlaskForm):
    full_name = StringField('Full Name', validators=[Optional(), Length(max=120)])
    email = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=1000)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()], format='%Y-%m-%d')
    preferred_language = SelectField('Preferred Language', 
                                   choices=[('en', 'English'), ('hi', 'Hindi'), ('es', 'Spanish'), ('fr', 'French')],
                                   default='en')
    preferred_timezone = SelectField('Preferred Timezone',
                                   choices=[('UTC', 'UTC'), ('Asia/Calcutta', 'Asia/Calcutta'), 
                                           ('America/New_York', 'America/New_York'), ('Europe/London', 'Europe/London')],
                                   default='UTC')
    avatar = FileField('Profile Picture')
    submit = SubmitField('Update Profile')
    
    def validate_phone(self, field):
        if field.data:
            # Basic phone validation
            phone_pattern = r'^[+]?[1-9][\d]{0,15}$'
            
            if not re.match(phone_pattern, field.data.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                raise ValidationError('Please enter a valid phone number.')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')
    
    def validate_new_password(self, field):
        password = field.data
        
        # Check password strength requirements
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
        
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter.')
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter.')
        
        if not re.search(r'\d', password):
            raise ValidationError('Password must contain at least one number.')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('Password must contain at least one special character.')

class NotificationPreferencesForm(FlaskForm):
    email_notifications = BooleanField('Email Notifications', default=True)
    order_updates = BooleanField('Order Updates', default=True)
    marketing_emails = BooleanField('Marketing Emails', default=False)
    system_alerts = BooleanField('System Alerts', default=True)
    submit = SubmitField('Update Preferences')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Send Reset Link')
    
    def validate_email(self, field):
        # Find user by email (decrypting the stored email)
        user = User.get_by_email_encrypted(field.data)
        if not user:
            # Don't reveal whether email exists for security
            raise ValidationError('If an account exists with this email, a password reset link will be sent.')
        
        # Check if user can request reset
        can_request, message = user.can_request_password_reset()
        if not can_request:
            raise ValidationError(message)

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Reset Password')
    
    def validate_new_password(self, field):
        password = field.data
        
        # Check password strength requirements
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
        
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter.')
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter.')
        
        if not re.search(r'\d', password):
            raise ValidationError('Password must contain at least one number.')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('Password must contain at least one special character.')

# Mobile OTP Forms

class MobileOTPLoginForm(FlaskForm):
    phone = StringField('Phone Number', validators=[
        DataRequired(),
        Length(max=20),
        Regexp(r'^[+]?[1-9][\d\s\-\(\)]{7,15}$', message='Please enter a valid phone number')
    ])
    remember = BooleanField('Remember me')
    submit = SubmitField('Send OTP')
    
    def validate_phone(self, field):
        # Check if user exists with this phone number
        from models import User
        from utils.otp_manager import OTPManager
        
        # Validate phone number format
        is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(field.data)
        if not is_valid:
            raise ValidationError(error_msg)
        
        # Check if user exists with this phone number
        user = User.query.filter_by(phone=formatted_phone).first()
        if not user:
            raise ValidationError('No account found with this phone number')
        
        # Check if mobile OTP is enabled for this user
        if not user.mobile_otp_enabled:
            raise ValidationError('Mobile OTP is not enabled for this account. Please contact your administrator.')
        
        # Check if account is active
        if not user.is_active or user.account_status != 'active':
            raise ValidationError('Account is not active. Please contact your administrator.')

class MobileOTPVerifyForm(FlaskForm):
    otp_code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6),
        Regexp(r'^[0-9]{6}$', message='Please enter a valid 6-digit code')
    ])
    remember = BooleanField('Remember me')
    submit = SubmitField('Verify OTP')
    
    def validate_otp_code(self, field):
        # Additional validation for OTP code format
        if not field.data.isdigit():
            raise ValidationError('OTP code must contain only numbers')

class PhoneVerificationForm(FlaskForm):
    phone = StringField('Phone Number', validators=[
        DataRequired(),
        Length(max=20),
        Regexp(r'^[+]?[1-9][\d\s\-\(\)]{7,15}$', message='Please enter a valid phone number')
    ])
    submit = SubmitField('Send Verification Code')
    
    def validate_phone(self, field):
        from models import User
        from utils.otp_manager import OTPManager
        
        # Validate phone number format
        is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(field.data)
        if not is_valid:
            raise ValidationError(error_msg)
        
        # Check if phone number is already verified for another user
        existing_user = User.query.filter(
            User.phone == formatted_phone,
            User.phone_verified == True
        ).first()
        
        if existing_user:
            raise ValidationError('This phone number is already verified for another account')

class PhoneVerificationCodeForm(FlaskForm):
    verification_code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6),
        Regexp(r'^[0-9]{6}$', message='Please enter a valid 6-digit code')
    ])
    submit = SubmitField('Verify Phone Number')
    
    def validate_verification_code(self, field):
        # Additional validation for verification code format
        if not field.data.isdigit():
            raise ValidationError('Verification code must contain only numbers')

class MobileOTPSettingsForm(FlaskForm):
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(max=20),
        Regexp(r'^[+]?[1-9][\d\s\-\(\)]{7,15}$', message='Please enter a valid phone number')
    ])
    mobile_otp_enabled = BooleanField('Enable Mobile OTP Login')
    backup_phone = StringField('Backup Phone Number', validators=[
        Optional(),
        Length(max=20),
        Regexp(r'^[+]?[1-9][\d\s\-\(\)]{7,15}$', message='Please enter a valid phone number')
    ])
    submit = SubmitField('Update Settings')
    
    def validate_phone(self, field):
        if field.data:
            from utils.otp_manager import OTPManager
            is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(field.data)
            if not is_valid:
                raise ValidationError(error_msg)
    
    def validate_backup_phone(self, field):
        if field.data:
            from utils.otp_manager import OTPManager
            is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(field.data)
            if not is_valid:
                raise ValidationError(error_msg)
            
            # Backup phone should be different from main phone
            if field.data == self.phone.data:
                raise ValidationError('Backup phone number must be different from main phone number')

# Email OTP Forms

class EmailOTPLoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    remember = BooleanField('Remember me')
    submit = SubmitField('Send OTP')
    
    def validate_email(self, field):
        # Check if user exists with this email
        from models import User
        from utils.email_service import EmailService
        
        # Validate email format
        email_service = EmailService()
        if not email_service.validate_email_address(field.data):
            raise ValidationError('Please enter a valid email address')
        
        # Check if user exists with this email
        user = User.get_by_email_encrypted(field.data)
        if not user:
            raise ValidationError('No account found with this email address')
        
        # Check if email OTP is enabled for this user
        if not user.email_otp_enabled:
            raise ValidationError('Email OTP is not enabled for this account. Please contact your administrator.')
        
        # Check if account is active
        if not user.is_active or user.account_status != 'active':
            raise ValidationError('Account is not active. Please contact your administrator.')

class EmailOTPVerifyForm(FlaskForm):
    otp_code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6),
        Regexp(r'^[0-9]{6}$', message='Please enter a valid 6-digit code')
    ])
    remember = BooleanField('Remember me')
    submit = SubmitField('Verify OTP')
    
    def validate_otp_code(self, field):
        # Additional validation for OTP code format
        if not field.data.isdigit():
            raise ValidationError('OTP code must contain only numbers')

class EmailVerificationForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    submit = SubmitField('Send Verification Code')
    
    def validate_email(self, field):
        from models import User
        from utils.email_service import EmailService
        
        # Validate email format
        email_service = EmailService()
        if not email_service.validate_email_address(field.data):
            raise ValidationError('Please enter a valid email address')
        
        # Check if email is already verified for another user
        existing_users = User.query.filter(
            User.email.isnot(None),
            User.id != getattr(self, '_user_id', None)  # Will be set by the view
        ).all()
        
        for existing in existing_users:
            if existing.email_decrypted.lower() == field.data.lower():
                raise ValidationError('This email is already verified for another account')

class EmailVerificationCodeForm(FlaskForm):
    verification_code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6),
        Regexp(r'^[0-9]{6}$', message='Please enter a valid 6-digit code')
    ])
    submit = SubmitField('Verify Email')
    
    def validate_verification_code(self, field):
        # Additional validation for verification code format
        if not field.data.isdigit():
            raise ValidationError('Verification code must contain only numbers')

class EmailOTPSettingsForm(FlaskForm):
    email = StringField('Email Address', validators=[
        Optional(),
        Email(),
        Length(max=120)
    ])
    email_otp_enabled = BooleanField('Enable Email OTP Login')
    backup_email = StringField('Backup Email Address', validators=[
        Optional(),
        Email(),
        Length(max=120)
    ])
    submit = SubmitField('Update Settings')
    
    def validate_email(self, field):
        if field.data:
            from utils.email_service import EmailService
            email_service = EmailService()
            if not email_service.validate_email_address(field.data):
                raise ValidationError('Please enter a valid email address')
    
    def validate_backup_email(self, field):
        if field.data:
            from utils.email_service import EmailService
            email_service = EmailService()
            if not email_service.validate_email_address(field.data):
                raise ValidationError('Please enter a valid email address')
            
            # Backup email should be different from main email
            if field.data.lower() == self.email.data.lower():
                raise ValidationError('Backup email must be different from main email address')

# Registration Forms

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Username can only contain letters, numbers, and underscores')
    ])
    email = StringField('Email Address', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, max=128)
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    full_name = StringField('Full Name', validators=[
        DataRequired(),
        Length(min=2, max=120)
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(),
        Length(max=20),
        Regexp(r'^[+]?[1-9][\d\s\-\(\)]{7,15}$', message='Please enter a valid phone number')
    ])
    business_name = StringField('Business Name', validators=[
        Optional(),
        Length(max=120)
    ])
    business_type = SelectField('Business Type', choices=[
        ('restaurant', 'Restaurant'),
        ('cafe', 'Cafe'),
        ('fast_food', 'Fast Food'),
        ('bakery', 'Bakery'),
        ('other', 'Other')
    ], default='restaurant')
    agree_terms = BooleanField('I agree to the Terms of Service', validators=[
        DataRequired(message='You must agree to the Terms of Service')
    ])
    submit = SubmitField('Create Account')
    
    def validate_username(self, field):
        # Check if username already exists
        from models import User
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
        
        # Check if username is reserved
        reserved_usernames = ['admin', 'administrator', 'root', 'system', 'api', 'www', 'mail', 'ftp']
        if field.data.lower() in reserved_usernames:
            raise ValidationError('This username is reserved. Please choose a different one.')
    
    def validate_email(self, field):
        # Check if email already exists
        from models import User
        user = User.get_by_email_encrypted(field.data)
        if user:
            raise ValidationError('An account with this email already exists.')
        
        # Validate email domain (optional - can be configured)
        domain = field.data.split('@')[1].lower()
        blocked_domains = ['mailinator.com', 'tempmail.org', 'guerrillamail.com']
        if domain in blocked_domains:
            raise ValidationError('Temporary email addresses are not allowed.')
    
    def validate_password(self, field):
        password = field.data
        
        # Check password strength requirements
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
        
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter.')
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter.')
        
        if not re.search(r'\d', password):
            raise ValidationError('Password must contain at least one number.')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('Password must contain at least one special character.')
        
        # Check for common passwords
        common_passwords = ['password', 'password123', '123456', 'admin', 'welcome']
        if password.lower() in common_passwords:
            raise ValidationError('This password is too common. Please choose a more secure password.')
    
    def validate_phone(self, field):
        from utils.otp_manager import OTPManager
        
        # Validate phone number format
        is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(field.data)
        if not is_valid:
            raise ValidationError(error_msg)
        
        # Check if phone number is already registered
        from models import User
        user = User.query.filter_by(phone=formatted_phone).first()
        if user:
            raise ValidationError('This phone number is already registered.')

class EmailVerificationForm(FlaskForm):
    verification_code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6),
        Regexp(r'^[0-9]{6}$', message='Please enter a valid 6-digit code')
    ])
    submit = SubmitField('Verify Email')
    
    def validate_verification_code(self, field):
        # Additional validation for verification code format
        if not field.data.isdigit():
            raise ValidationError('Verification code must contain only numbers')

class ResendVerificationForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    submit = SubmitField('Resend Verification Email')
    
    def validate_email(self, field):
        from models import User
        user = User.get_by_email_encrypted(field.data)
        if not user:
            raise ValidationError('No registration found with this email address.')
        
        if user.email_verified:
            raise ValidationError('Email is already verified.')
        
        if user.registration_status == 'approved':
            raise ValidationError('Registration is already approved.')

class AdminApprovalForm(FlaskForm):
    action = SelectField('Action', choices=[
        ('approve', 'Approve Registration'),
        ('reject', 'Reject Registration')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[
        Optional(),
        Length(max=500)
    ])
    submit = SubmitField('Submit')