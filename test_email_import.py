#!/usr/bin/env python3
"""
Test script to check email OTP import issues
"""

def test_email_otp_import():
    """Test importing EmailOTPLoginManager"""
    try:
        print("Testing EmailOTPLoginManager import...")
        from utils.otp_manager import EmailOTPLoginManager
        print("PASS: EmailOTPLoginManager imported successfully")
        
        print("Testing EmailService import...")
        from utils.email_service import EmailService
        print("PASS: EmailService imported successfully")
        
        print("Testing EmailService instantiation...")
        email_service = EmailService()
        print("PASS: EmailService instantiated successfully")
        
        print("Testing EmailOTPLoginManager method call...")
        # Test static method call
        result = EmailOTPLoginManager.get_user_by_email("test@example.com")
        print(f"PASS: EmailOTPLoginManager.get_user_by_email() returned: {result}")
        
        print("\nSUCCESS: All imports and basic functionality working!")
        return True
        
    except ImportError as e:
        print(f"FAIL: Import Error: {e}")
        return False
    except Exception as e:
        print(f"FAIL: Runtime Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_email_otp_import()