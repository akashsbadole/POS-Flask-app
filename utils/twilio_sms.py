import os
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioException, TwilioRestException
from datetime import datetime

class TwilioSMSService:
    """Twilio SMS service for OTP delivery"""
    
    def __init__(self, config=None):
        """
        Initialize Twilio SMS service
        
        Args:
            config (dict): Twilio configuration dict. If None, uses environment variables.
        """
        self.config = config or self._load_config_from_env()
        self.client = None
        self.enabled = False
        
        # Initialize Twilio client if credentials are available
        if self._has_valid_credentials():
            try:
                self.client = Client(
                    self.config.get('account_sid'),
                    self.config.get('auth_token')
                )
                self.enabled = True
            except Exception as e:
                logging.error(f"Failed to initialize Twilio client: {e}")
                self.enabled = False
    
    def _load_config_from_env(self):
        """Load Twilio configuration from environment variables"""
        return {
            'account_sid': os.environ.get('TWILIO_ACCOUNT_SID'),
            'auth_token': os.environ.get('TWILIO_AUTH_TOKEN'),
            'phone_number': os.environ.get('TWILIO_PHONE_NUMBER'),
            'verify_service_sid': os.environ.get('TWILIO_VERIFY_SERVICE_SID'),
            'enabled': os.environ.get('TWILIO_ENABLED', 'false').lower() in ['true', '1', 'yes']
        }
    
    def _has_valid_credentials(self):
        """Check if we have valid Twilio credentials"""
        required_fields = ['account_sid', 'auth_token', 'phone_number']
        
        # Check if all required fields are present and not empty
        has_creds = all(
            self.config.get(field) and 
            self.config.get(field).strip() != '' 
            for field in required_fields
        )
        
        # Check if Twilio is enabled (defaults to True if not set but credentials exist)
        if has_creds:
            return self.config.get('enabled', True)
        
        return False
    
    def is_enabled(self):
        """Check if Twilio SMS service is enabled"""
        return self.enabled and self.client is not None
    
    def send_otp_sms(self, phone_number, otp_code, message_template=None):
        """
        Send OTP via SMS using Twilio
        
        Args:
            phone_number (str): Recipient phone number (E.164 format preferred)
            otp_code (str): 6-digit OTP code
            message_template (str): Custom message template (optional)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.is_enabled():
            return False, "Twilio SMS service is not enabled or configured"
        
        try:
            # Format phone number
            formatted_phone = self._format_phone_number(phone_number)
            
            # Use custom template or default
            if message_template:
                message_body = message_template.format(otp_code=otp_code)
            else:
                message_body = f"Your verification code is: {otp_code}. This code will expire in 10 minutes. Please don't share this code with anyone."
            
            # Send SMS via Twilio
            message = self.client.messages.create(
                body=message_body,
                from_=self.config.get('phone_number'),
                to=formatted_phone
            )
            
            # Log successful send
            logging.info(f"SMS sent successfully to {formatted_phone}, SID: {message.sid}")
            
            return True, f"SMS sent successfully. Message SID: {message.sid}"
            
        except TwilioRestException as e:
            error_msg = f"Twilio API error: {e.code} - {e.message}"
            logging.error(f"Failed to send SMS to {phone_number}: {error_msg}")
            return False, error_msg
            
        except TwilioException as e:
            error_msg = f"Twilio client error: {str(e)}"
            logging.error(f"Failed to send SMS to {phone_number}: {error_msg}")
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error sending SMS: {str(e)}"
            logging.error(f"Failed to send SMS to {phone_number}: {error_msg}")
            return False, error_msg
    
    def send_bulk_otp_sms(self, phone_numbers, otp_code, message_template=None):
        """
        Send OTP to multiple phone numbers
        
        Args:
            phone_numbers (list): List of phone numbers
            otp_code (str): 6-digit OTP code
            message_template (str): Custom message template (optional)
            
        Returns:
            dict: Results for each phone number
        """
        results = {}
        
        for phone_number in phone_numbers:
            success, message = self.send_otp_sms(phone_number, otp_code, message_template)
            results[phone_number] = {
                'success': success,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        return results
    
    def _format_phone_number(self, phone_number):
        """
        Format phone number for Twilio
        
        Args:
            phone_number (str): Raw phone number
            
        Returns:
            str: Formatted phone number
        """
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Add country code if missing (assuming +1 for US/Canada)
        if len(digits_only) == 10:
            return f"+1{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            return f"+{digits_only}"
        elif phone_number.startswith('+'):
            return phone_number
        else:
            # Assume it's already in international format
            return phone_number
    
    def validate_phone_number(self, phone_number):
        """
        Validate phone number format
        
        Args:
            phone_number (str): Phone number to validate
            
        Returns:
            tuple: (is_valid: bool, formatted_number: str, error_message: str)
        """
        if not phone_number or not phone_number.strip():
            return False, None, "Phone number is required"
        
        formatted_number = self._format_phone_number(phone_number)
        
        # Basic validation - should start with + and have 8-15 digits
        if not formatted_number.startswith('+'):
            return False, None, "Phone number must include country code (e.g., +1234567890)"
        
        digits_after_plus = formatted_number[1:]
        if not digits_after_plus.isdigit() or not (8 <= len(digits_after_plus) <= 15):
            return False, None, "Phone number must have 8-15 digits after country code"
        
        return True, formatted_number, None
    
    def get_message_status(self, message_sid):
        """
        Get status of a sent message
        
        Args:
            message_sid (str): Twilio message SID
            
        Returns:
            tuple: (success: bool, status_info: dict)
        """
        if not self.is_enabled():
            return False, {"error": "Twilio SMS service is not enabled"}
        
        try:
            message = self.client.messages(message_sid).fetch()
            
            status_info = {
                'sid': message.sid,
                'status': message.status,
                'direction': message.direction,
                'from_number': message.from_,
                'to_number': message.to,
                'date_created': message.date_created.isoformat() if message.date_created else None,
                'date_sent': message.date_sent.isoformat() if message.date_sent else None,
                'date_updated': message.date_updated.isoformat() if message.date_updated else None,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'price': message.price,
                'price_unit': message.price_unit
            }
            
            return True, status_info
            
        except TwilioRestException as e:
            error_msg = f"Failed to fetch message status: {e.code} - {e.message}"
            logging.error(error_msg)
            return False, {"error": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error fetching message status: {str(e)}"
            logging.error(error_msg)
            return False, {"error": error_msg}
    
    def get_service_info(self):
        """Get information about the Twilio service configuration"""
        return {
            'enabled': self.is_enabled(),
            'has_credentials': self._has_valid_credentials(),
            'account_sid': self.config.get('account_sid', ''),
            'phone_number': self.config.get('phone_number', ''),
            'verify_service_sid': self.config.get('verify_service_sid', ''),
            'twilio_version': '1.0.0'  # Would need to check actual version if available
        }

# Global instance
_twilio_service = None

def get_twilio_service():
    """Get global Twilio SMS service instance"""
    global _twilio_service
    if _twilio_service is None:
        _twilio_service = TwilioSMSService()
    return _twilio_service

# SMS Templates
SMS_TEMPLATES = {
    'otp_login': "Your {app_name} login code is: {otp_code}. This code expires in 10 minutes. Don't share this code.",
    'otp_verification': "Your {app_name} phone verification code is: {otp_code}. This code expires in 10 minutes. Don't share this code.",
    'otp_reset': "Your {app_name} password reset code is: {otp_code}. This code expires in 10 minutes. Don't share this code.",
    'custom': "{otp_code}"  # For custom messages
}

def send_otp_sms(phone_number, otp_code, template_type='otp_login', app_name='POS System', custom_message=None):
    """
    Convenience function to send OTP SMS
    
    Args:
        phone_number (str): Recipient phone number
        otp_code (str): 6-digit OTP code
        template_type (str): Template type ('otp_login', 'otp_verification', 'otp_reset', 'custom')
        app_name (str): Application name for templates
        custom_message (str): Custom message template
        
    Returns:
        tuple: (success: bool, message: str)
    """
    service = get_twilio_service()
    
    if custom_message:
        message_template = custom_message
    else:
        template = SMS_TEMPLATES.get(template_type, SMS_TEMPLATES['custom'])
        message_template = template.format(
            app_name=app_name,
            otp_code=otp_code
        )
    
    return service.send_otp_sms(phone_number, otp_code, message_template)