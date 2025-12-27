import secrets
import string
import logging
from datetime import datetime, timedelta
from models.otp import OTP, OTPRateLimit
from models import db, User
from utils.twilio_sms import get_twilio_service, send_otp_sms
from utils.email_service import EmailService

class OTPManager:
    """Manager class for OTP operations"""
    
    # OTP configuration constants
    OTP_EXPIRY_MINUTES = 10
    MAX_VERIFICATION_ATTEMPTS = 3
    MAX_REQUESTS_PER_HOUR = 5
    MAX_REQUESTS_PER_DAY = 10
    
    @staticmethod
    def generate_otp():
        """Generate a 6-digit OTP"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    @staticmethod
    def create_otp(user_id, phone_number=None, email=None, otp_type=OTP.TYPE_LOGIN, max_attempts=3):
        """
        Create a new OTP for a user
        
        Args:
            user_id (int): User ID
            phone_number (str): Phone number (for SMS OTP)
            email (str): Email address (for email OTP)
            otp_type (str): Type of OTP ('login', 'phone_verification', 'email_verification', 'password_reset')
            max_attempts (int): Maximum verification attempts
            
        Returns:
            tuple: (otp_record: OTP, success: bool, message: str)
        """
        try:
            # Validate input and check rate limiting
            if phone_number:
                # Validate phone number with Twilio service
                twilio_service = get_twilio_service()
                is_valid, formatted_phone, error_msg = twilio_service.validate_phone_number(phone_number)
                
                if not is_valid:
                    return None, False, f"Invalid phone number: {error_msg}"
                
                # Check rate limiting
                rate_limit = OTPRateLimit.get_or_create_rate_limit(phone=formatted_phone)
                can_request, rate_message = rate_limit.can_request_otp()
                
                if not can_request:
                    return None, False, rate_message
            
            elif email:
                # Validate email format
                email_service = EmailService()
                if not email_service.validate_email_address(email):
                    return None, False, "Invalid email address format"
                
                # Check rate limiting
                rate_limit = OTPRateLimit.get_or_create_rate_limit(email=email)
                can_request, rate_message = rate_limit.can_request_otp()
                
                if not can_request:
                    return None, False, rate_message
            else:
                return None, False, "Either phone number or email is required"
            
            # Create OTP record
            otp = OTP(
                user_id=user_id,
                phone=formatted_phone if phone_number else None,
                email=email,
                otp_type=otp_type,
                max_attempts=max_attempts
            )
            
            # Add to database
            db.session.add(otp)
            db.session.commit()
            
            # Send OTP via appropriate channel
            if phone_number:
                # Send SMS
                sms_success, sms_message = OTPManager._send_otp_sms(otp, phone_number)
                
                # Record rate limit request
                rate_limit.record_request()
                
                if sms_success:
                    return otp, True, "OTP sent successfully"
                else:
                    # Remove OTP if SMS failed
                    db.session.delete(otp)
                    db.session.commit()
                    return None, False, f"Failed to send SMS: {sms_message}"
            
            elif email:
                # Send email
                email_success, email_message = OTPManager._send_otp_email(otp, email)
                
                # Record rate limit request
                rate_limit.record_request()
                
                if email_success:
                    return otp, True, "OTP sent successfully"
                else:
                    # Remove OTP if email failed
                    db.session.delete(otp)
                    db.session.commit()
                    return None, False, f"Failed to send email: {email_message}"
                
        except Exception as e:
            logging.error(f"Error creating OTP for user {user_id}: {e}")
            db.session.rollback()
            return None, False, "Internal error creating OTP"
    
    @staticmethod
    def verify_otp(otp_id, input_code, user_id=None, ip_address=None, user_agent=None):
        """
        Verify an OTP code
        
        Args:
            otp_id (int): OTP record ID
            input_code (str): User input OTP code
            user_id (int): Optional user ID to verify ownership
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (success: bool, message: str, otp_record: OTP)
        """
        try:
            # Get OTP record
            otp = OTP.query.get(otp_id)
            
            if not otp:
                return False, "Invalid OTP ID", None
            
            # Verify user ownership if user_id provided
            if user_id and otp.user_id != user_id:
                return False, "OTP does not belong to this user", None
            
            # Verify the OTP
            is_valid, verify_message = otp.verify_otp(input_code, ip_address, user_agent)
            
            return is_valid, verify_message, otp
            
        except Exception as e:
            logging.error(f"Error verifying OTP {otp_id}: {e}")
            return False, "Internal error verifying OTP", None
    
    @staticmethod
    def resend_otp(otp_id):
        """
        Resend an existing OTP (generates new code)
        
        Args:
            otp_id (int): OTP record ID
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Get OTP record
            otp = OTP.query.get(otp_id)
            
            if not otp:
                return False, "Invalid OTP ID"
            
            # Resend OTP (generates new code)
            success, message = otp.resend()
            
            if success:
                # Send SMS with new code
                sms_success, sms_message = OTPManager._send_otp_sms(otp, otp.phone)
                
                if not sms_success:
                    return False, f"Failed to send SMS: {sms_message}"
            
            return success, message
            
        except Exception as e:
            logging.error(f"Error resending OTP {otp_id}: {e}")
            return False, "Internal error resending OTP"
    
    @staticmethod
    def cleanup_expired_otps():
        """Clean up expired OTP records"""
        try:
            expired_otps = OTP.query.filter(
                OTP.expires_at < datetime.utcnow(),
                OTP.is_used == False
            ).all()
            
            for otp in expired_otps:
                db.session.delete(otp)
            
            db.session.commit()
            return len(expired_otps)
            
        except Exception as e:
            logging.error(f"Error cleaning up expired OTPs: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def get_user_active_otp(user_id, otp_type=OTP.TYPE_LOGIN):
        """
        Get user's active (unused and not expired) OTP of specified type
        
        Args:
            user_id (int): User ID
            otp_type (str): Type of OTP
            
        Returns:
            OTP: Active OTP record or None
        """
        return OTP.query.filter(
            OTP.user_id == user_id,
            OTP.otp_type == otp_type,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        ).first()
    
    @staticmethod
    def get_user_latest_otp(user_id, otp_type=OTP.TYPE_LOGIN, limit=1):
        """
        Get user's latest OTP records of specified type
        
        Args:
            user_id (int): User ID
            otp_type (str): Type of OTP
            limit (int): Number of records to return
            
        Returns:
            list: List of OTP records
        """
        return OTP.query.filter(
            OTP.user_id == user_id,
            OTP.otp_type == otp_type
        ).order_by(OTP.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def _send_otp_sms(otp, phone_number):
        """Send OTP via SMS using Twilio service"""
        try:
            # Get template based on OTP type
            template_map = {
                OTP.TYPE_LOGIN: 'otp_login',
                OTP.TYPE_PHONE_VERIFICATION: 'otp_verification',
                OTP.TYPE_PASSWORD_RESET: 'otp_reset'
            }
            
            template_type = template_map.get(otp.otp_type, 'otp_login')
            
            # Send SMS
            success, message = send_otp_sms(
                phone_number=phone_number,
                otp_code=otp.otp_code,
                template_type=template_type,
                app_name="POS System"
            )
            
            return success, message
            
        except Exception as e:
            logging.error(f"Error sending OTP SMS: {e}")
            return False, f"SMS service error: {str(e)}"
    
    @staticmethod
    def validate_phone_number(phone_number):
        """
        Validate phone number format
        
        Args:
            phone_number (str): Phone number to validate
            
        Returns:
            tuple: (is_valid: bool, formatted_number: str, error_message: str)
        """
        twilio_service = get_twilio_service()
        return twilio_service.validate_phone_number(phone_number)
    
    @staticmethod
    def _send_otp_email(otp, email):
        """Send OTP via email using email service"""
        try:
            # Get template based on OTP type
            template_map = {
                OTP.TYPE_LOGIN: 'otp_login',
                OTP.TYPE_EMAIL_LOGIN: 'otp_login',
                OTP.TYPE_EMAIL_VERIFICATION: 'otp_verification',
                OTP.TYPE_PASSWORD_RESET: 'otp_reset'
            }
            
            template_type = template_map.get(otp.otp_type, 'otp_login')
            
            # Get email service instance
            email_service = EmailService()
            
            # Send email
            success, message = email_service.send_otp_email(
                email=email,
                otp_code=otp.otp_code,
                template_type=template_type,
                user_id=otp.user_id
            )
            
            return success, message
            
        except Exception as e:
            logging.error(f"Error sending OTP email: {e}")
            return False, f"Email service error: {str(e)}"

class MobileOTPLoginManager:
    """Manager for mobile OTP login functionality"""
    
    @staticmethod
    def initiate_login(phone_number, ip_address=None, user_agent=None):
        """
        Initiate mobile OTP login
        
        Args:
            phone_number (str): Phone number
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (success: bool, message: str, otp_id: int or None)
        """
        try:
            # Validate phone number
            is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(phone_number)
            
            if not is_valid:
                return False, error_msg, None
            
            # Find user by phone number
            user = User.query.filter_by(phone=formatted_phone).first()
            
            if not user:
                return False, "No account found with this phone number", None
            
            # Check if user has mobile OTP enabled
            if not user.mobile_otp_enabled:
                return False, "Mobile OTP is not enabled for this account. Please contact your administrator.", None
            
            # Check if account is active
            if not user.is_active or user.account_status != 'active':
                return False, "Account is not active. Please contact your administrator.", None
            
            # Check if account is locked
            if user.is_account_locked():
                return False, "Account is temporarily locked due to multiple failed attempts. Please try again later.", None
            
            # Create OTP
            otp, success, message = OTPManager.create_otp(
                user_id=user.id,
                phone_number=formatted_phone,
                otp_type=OTP.TYPE_LOGIN
            )
            
            if success:
                return True, f"OTP sent to {formatted_phone}", otp.id
            else:
                return False, message, None
                
        except Exception as e:
            logging.error(f"Error initiating mobile OTP login: {e}")
            return False, "Internal error initiating login", None
    
    @staticmethod
    def complete_login(otp_id, otp_code, ip_address=None, user_agent=None):
        """
        Complete mobile OTP login
        
        Args:
            otp_id (int): OTP record ID
            otp_code (str): User input OTP code
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (success: bool, message: str, user: User or None)
        """
        try:
            # Verify OTP
            is_valid, message, otp = OTPManager.verify_otp(
                otp_id=otp_id,
                input_code=otp_code,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if not is_valid:
                return False, message, None
            
            # Get user
            user = User.query.get(otp.user_id)
            
            if not user:
                return False, "User not found", None
            
            # Update user login info
            user.update_last_login()
            user.update_activity('login')
            user.reset_failed_login_attempts()  # Reset failed attempts on successful login
            
            return True, "Login successful", user
            
        except Exception as e:
            logging.error(f"Error completing mobile OTP login: {e}")
            return False, "Internal error completing login", None
    
    @staticmethod
    def get_user_by_phone(phone_number):
        """
        Get user by phone number
        
        Args:
            phone_number (str): Phone number
            
        Returns:
            User: User object or None
        """
        # Validate and format phone number
        is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(phone_number)
        
        if not is_valid:
            return None
        
        return User.query.filter_by(phone=formatted_phone).first()

class PhoneVerificationManager:
    """Manager for phone verification functionality"""
    
    @staticmethod
    def initiate_verification(user, phone_number):
        """
        Initiate phone verification process
        
        Args:
            user (User): User object
            phone_number (str): Phone number to verify
            
        Returns:
            tuple: (success: bool, message: str, otp_id: int or None)
        """
        try:
            # Validate phone number
            is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(phone_number)
            
            if not is_valid:
                return False, error_msg, None
            
            # Check if phone number is already verified for another user
            existing_user = User.query.filter(
                User.phone == formatted_phone,
                User.phone_verified == True,
                User.id != user.id
            ).first()
            
            if existing_user:
                return False, "This phone number is already verified for another account", None
            
            # Update user's phone number
            user.phone = formatted_phone
            
            # Generate verification token (not OTP, just for reference)
            verification_token = user.generate_phone_verification_token()
            
            # Create OTP for verification
            otp, success, message = OTPManager.create_otp(
                user_id=user.id,
                phone_number=formatted_phone,
                otp_type=OTP.TYPE_PHONE_VERIFICATION
            )
            
            if success:
                return True, f"Verification code sent to {formatted_phone}", otp.id
            else:
                # Rollback phone update if OTP creation failed
                user.phone = None
                db.session.commit()
                return False, message, None
                
        except Exception as e:
            logging.error(f"Error initiating phone verification: {e}")
            return False, "Internal error initiating verification", None
    
    @staticmethod
    def complete_verification(otp_id, otp_code, user):
        """
        Complete phone verification process
        
        Args:
            otp_id (int): OTP record ID
            otp_code (str): User input OTP code
            user (User): User object
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Verify OTP
            is_valid, message, otp = OTPManager.verify_otp(
                otp_id=otp_id,
                input_code=otp_code,
                user_id=user.id
            )
            
            if not is_valid:
                return False, message
            
            # Check OTP type
            if otp.otp_type != OTP.TYPE_PHONE_VERIFICATION:
                return False, "Invalid verification code type"
            
            # Mark phone as verified
            user.phone_verified = True
            user.clear_phone_verification_token()
            
            # Optionally enable mobile OTP automatically
            # This can be controlled by configuration
            if not user.mobile_otp_enabled:
                user.mobile_otp_enabled = True
            
            db.session.commit()
            
            return True, "Phone number verified successfully"
            
        except Exception as e:
            logging.error(f"Error completing phone verification: {e}")
            return False, "Internal error completing verification"

class EmailOTPLoginManager:
    """Manager for email OTP login functionality"""
    
    @staticmethod
    def initiate_login(email, ip_address=None, user_agent=None):
        """
        Initiate email OTP login
        
        Args:
            email (str): Email address
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (success: bool, message: str, otp_id: int or None)
        """
        try:
            # Validate email format
            email_service = EmailService()
            if not email_service.validate_email_address(email):
                return False, "Invalid email address format", None
            
            # Find user by email (decrypting stored emails for lookup)
            user = User.get_by_email_encrypted(email)
            
            if not user:
                return False, "No account found with this email address", None
            
            # Check if user has email OTP enabled
            if not user.email_otp_enabled:
                return False, "Email OTP is not enabled for this account. Please contact your administrator.", None
            
            # Check if account is active
            if not user.is_active or user.account_status != 'active':
                return False, "Account is not active. Please contact your administrator.", None
            
            # Check if account is locked
            if user.is_account_locked():
                return False, "Account is temporarily locked due to multiple failed attempts. Please try again later.", None
            
            # Create OTP
            otp, success, message = OTPManager.create_otp(
                user_id=user.id,
                email=email,
                otp_type=OTP.TYPE_EMAIL_LOGIN
            )
            
            if success:
                return True, f"OTP sent to {email}", otp.id
            else:
                return False, message, None
                
        except Exception as e:
            logging.error(f"Error initiating email OTP login: {e}")
            return False, "Internal error initiating login", None
    
    @staticmethod
    def complete_login(otp_id, otp_code, ip_address=None, user_agent=None):
        """
        Complete email OTP login
        
        Args:
            otp_id (int): OTP record ID
            otp_code (str): User input OTP code
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (success: bool, message: str, user: User or None)
        """
        try:
            # Verify OTP
            is_valid, message, otp = OTPManager.verify_otp(
                otp_id=otp_id,
                input_code=otp_code,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if not is_valid:
                return False, message, None
            
            # Get user
            user = User.query.get(otp.user_id)
            
            if not user:
                return False, "User not found", None
            
            # Update user login info
            user.update_last_login()
            user.update_activity('login')
            user.reset_failed_login_attempts()  # Reset failed attempts on successful login
            
            return True, "Login successful", user
            
        except Exception as e:
            logging.error(f"Error completing email OTP login: {e}")
            return False, "Internal error completing login", None
    
    @staticmethod
    def get_user_by_email(email):
        """
        Get user by email address
        
        Args:
            email (str): Email address
            
        Returns:
            User: User object or None
        """
        # Validate email format
        email_service = EmailService()
        if not email_service.validate_email_address(email):
            return None
        
        return User.get_by_email_encrypted(email)

class EmailVerificationManager:
    """Manager for email verification functionality"""
    
    @staticmethod
    def initiate_verification(user, email):
        """
        Initiate email verification process
        
        Args:
            user (User): User object
            email (str): Email address to verify
            
        Returns:
            tuple: (success: bool, message: str, otp_id: int or None)
        """
        try:
            # Validate email format
            email_service = EmailService()
            if not email_service.validate_email_address(email):
                return False, "Invalid email address format", None
            
            # Check if email is already verified for another user
            existing_user = User.query.filter(
                User.email.isnot(None),
                User.id != user.id
            ).all()
            
            for existing in existing_user:
                if existing.email_decrypted.lower() == email.lower():
                    return False, "This email is already verified for another account", None
            
            # Update user's email
            user.email = user._encrypt_email(email)
            
            # Create OTP for verification
            otp, success, message = OTPManager.create_otp(
                user_id=user.id,
                email=email,
                otp_type=OTP.TYPE_EMAIL_VERIFICATION
            )
            
            if success:
                return True, f"Verification code sent to {email}", otp.id
            else:
                # Rollback email update if OTP creation failed
                user.email = None
                db.session.commit()
                return False, message, None
                
        except Exception as e:
            logging.error(f"Error initiating email verification: {e}")
            return False, "Internal error initiating verification", None
    
    @staticmethod
    def complete_verification(otp_id, otp_code, user):
        """
        Complete email verification process
        
        Args:
            otp_id (int): OTP record ID
            otp_code (str): User input OTP code
            user (User): User object
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Verify OTP
            is_valid, message, otp = OTPManager.verify_otp(
                otp_id=otp_id,
                input_code=otp_code,
                user_id=user.id
            )
            
            if not is_valid:
                return False, message
            
            # Check OTP type
            if otp.otp_type != OTP.TYPE_EMAIL_VERIFICATION:
                return False, "Invalid verification code type"
            
            # Mark email as verified (we don't have a separate email_verified field, but we can use email existence)
            # Optionally enable email OTP automatically
            if not user.email_otp_enabled:
                user.email_otp_enabled = True
            
            db.session.commit()
            
            return True, "Email verified successfully"
            
        except Exception as e:
            logging.error(f"Error completing email verification: {e}")
            return False, "Internal error completing verification"

# Global instance
_otp_manager = None

def get_otp_manager():
    """Get global OTP manager instance"""
    global _otp_manager
    if _otp_manager is None:
        _otp_manager = OTPManager()
    return _otp_manager