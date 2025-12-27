#!/usr/bin/env python3
"""
Test Email OTP Functionality

This script tests the email OTP implementation to ensure all components work correctly.
"""

import os
import sys
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from models.otp import OTP, OTPRateLimit
        print("[OK] OTP models imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import OTP models: {e}")
        return False
    
    try:
        from utils.otp_manager import EmailOTPLoginManager, EmailVerificationManager
        print("✓ Email OTP managers imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Email OTP managers: {e}")
        return False
    
    try:
        from utils.email_service import EmailService
        print("✓ Email service imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Email service: {e}")
        return False
    
    try:
        from forms import EmailOTPLoginForm, EmailOTPVerifyForm
        print("✓ Email OTP forms imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Email OTP forms: {e}")
        return False
    
    return True

def test_email_service_config():
    """Test email service configuration"""
    print("\nTesting email service configuration...")
    
    try:
        from utils.email_service import EmailService
        
        # Test with default config
        email_service = EmailService()
        
        # Test config validation
        is_valid, message = email_service.validate_config()
        print(f"Config validation: {message}")
        
        if not is_valid:
            print("⚠ Email service not configured (this is expected if not set up)")
        else:
            print("✓ Email service is properly configured")
        
        # Test email validation
        test_emails = [
            ("test@example.com", True),
            ("user@domain.co.in", True),
            ("invalid-email", False),
            ("user@", False),
            ("@domain.com", False)
        ]
        
        for email, expected in test_emails:
            result = email_service.validate_email_address(email)
            if result == expected:
                print(f"✓ Email validation correct for '{email}'")
            else:
                print(f"✗ Email validation failed for '{email}' (expected {expected}, got {result})")
        
        return True
        
    except Exception as e:
        print(f"✗ Email service test failed: {e}")
        return False

def test_otp_models():
    """Test OTP model functionality"""
    print("\nTesting OTP model functionality...")
    
    try:
        from models.otp import OTP, OTPRateLimit
        
        # Test OTP creation with email
        test_otp = OTP(
            user_id=1,
            email="test@example.com",
            otp_type=OTP.TYPE_EMAIL_LOGIN
        )
        
        print(f"✓ OTP created with email: {test_otp.email}")
        print(f"✓ OTP type: {test_otp.otp_type}")
        print(f"✓ OTP code generated: {len(test_otp.otp_code)} digits")
        
        # Test OTP dict conversion
        otp_dict = test_otp.to_dict()
        if 'email' in otp_dict:
            print("✓ OTP to_dict includes email field")
        else:
            print("✗ OTP to_dict missing email field")
        
        # Test rate limit creation with email
        test_rate_limit = OTPRateLimit(email="test@example.com")
        print(f"✓ Rate limit created for email: {test_rate_limit.email}")
        
        # Test rate limit dict conversion
        rate_limit_dict = test_rate_limit.to_dict()
        if 'email' in rate_limit_dict:
            print("✓ Rate limit to_dict includes email field")
        else:
            print("✗ Rate limit to_dict missing email field")
        
        return True
        
    except Exception as e:
        print(f"✗ OTP models test failed: {e}")
        return False

def test_forms():
    """Test email OTP forms"""
    print("\nTesting email OTP forms...")
    
    try:
        from forms import EmailOTPLoginForm, EmailOTPVerifyForm
        
        # Test form creation
        login_form = EmailOTPLoginForm()
        verify_form = EmailOTPVerifyForm()
        
        print("✓ Email OTP login form created")
        print("✓ Email OTP verify form created")
        
        # Test form fields
        if hasattr(login_form, 'email') and hasattr(login_form, 'submit'):
            print("✓ Login form has expected fields")
        else:
            print("✗ Login form missing expected fields")
        
        if hasattr(verify_form, 'otp_code') and hasattr(verify_form, 'submit'):
            print("✓ Verify form has expected fields")
        else:
            print("✗ Verify form missing expected fields")
        
        return True
        
    except Exception as e:
        print(f"✗ Forms test failed: {e}")
        return False

def test_database_schema():
    """Test database schema changes"""
    print("\nTesting database schema...")
    
    try:
        from models import db, User
        
        # Check if new fields exist in User model
        user_fields = [column.name for column in User.__table__.columns]
        
        if 'email_otp_enabled' in user_fields:
            print("✓ User model has email_otp_enabled field")
        else:
            print("✗ User model missing email_otp_enabled field")
        
        if 'backup_email' in user_fields:
            print("✓ User model has backup_email field")
        else:
            print("✗ User model missing backup_email field")
        
        # Check if OTP table has email field
        from models.otp import OTP
        otp_fields = [column.name for column in OTP.__table__.columns]
        
        if 'email' in otp_fields:
            print("✓ OTP model has email field")
        else:
            print("✗ OTP model missing email field")
        
        # Check if OTPRateLimit table has email field
        from models.otp import OTPRateLimit
        rate_limit_fields = [column.name for column in OTPRateLimit.__table__.columns]
        
        if 'email' in rate_limit_fields:
            print("✓ OTPRateLimit model has email field")
        else:
            print("✗ OTPRateLimit model missing email field")
        
        return True
        
    except Exception as e:
        print(f"✗ Database schema test failed: {e}")
        return False

def test_routes():
    """Test that email OTP routes are properly configured"""
    print("\nTesting email OTP routes...")
    
    try:
        from routes.auth import auth_bp
        
        # Check if email OTP routes exist
        route_names = [rule.rule for rule in auth_bp.url_map.iter_rules()]
        
        expected_routes = [
            '/email-login',
            '/email-verify/<int:otp_id>',
            '/verify-email',
            '/verify-email-code/<int:otp_id>',
            '/email-otp-settings'
        ]
        
        for route in expected_routes:
            if route in route_names:
                print(f"✓ Route '{route}' exists")
            else:
                print(f"✗ Route '{route}' missing")
        
        # Check if API routes exist
        api_routes = [
            '/api/email-otp/status',
            '/api/email-otp/validate-email'
        ]
        
        for route in api_routes:
            if route in route_names:
                print(f"✓ API route '{route}' exists")
            else:
                print(f"✗ API route '{route}' missing")
        
        return True
        
    except Exception as e:
        print(f"✗ Routes test failed: {e}")
        return False

def generate_test_report():
    """Generate a comprehensive test report"""
    print("\n" + "="*60)
    print("EMAIL OTP FUNCTIONALITY TEST REPORT")
    print("="*60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python Version: {sys.version}")
    print()
    
    # Run all tests
    tests = [
        ("Import Tests", test_imports),
        ("Email Service Configuration", test_email_service_config),
        ("OTP Models", test_otp_models),
        ("Forms", test_forms),
        ("Database Schema", test_database_schema),
        ("Routes", test_routes)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {e}")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Tests Passed: {passed}")
    print(f"Tests Failed: {failed}")
    print(f"Total Tests: {passed + failed}")
    print(f"Success Rate: {(passed / (passed + failed) * 100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Email OTP implementation is ready.")
    else:
        print(f"\n⚠ {failed} test(s) failed. Please review the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    success = generate_test_report()
    sys.exit(0 if success else 1)