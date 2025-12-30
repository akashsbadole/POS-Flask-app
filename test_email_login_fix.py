#!/usr/bin/env python3
"""
Test script to verify the email login page fix
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from flask import url_for

def test_email_login_route():
    """Test that the email login route works and renders properly"""
    try:
        app = create_app()
        with app.test_client() as client:
            with app.app_context():
                # Test GET request to email-login route
                response = client.get('/email-login')
                print(f"Status Code: {response.status_code}")
                print(f"Content Length: {len(response.data)}")
                
                # Check if response is successful
                if response.status_code == 200:
                    content = response.data.decode('utf-8')
                    
                    # Check for key elements that should be present
                    if 'Email OTP Login' in content:
                        print("✅ Page title found")
                    else:
                        print("❌ Page title not found")
                        
                    if 'email-otp-form' in content:
                        print("✅ Email OTP form found")
                    else:
                        print("❌ Email OTP form not found")
                        
                    if 'Enter your email address' in content:
                        print("✅ Email input placeholder found")
                    else:
                        print("❌ Email input placeholder not found")
                        
                    if len(content) > 1000:  # Should have substantial content
                        print("✅ Page has substantial content")
                    else:
                        print("❌ Page content seems too short")
                        
                    print("\n🎉 Email login page is now working!")
                    return True
                else:
                    print(f"❌ Route returned status code {response.status_code}")
                    print(f"Response data: {response.data.decode('utf-8')}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing email login route: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing email login page fix...")
    success = test_email_login_route()
    if success:
        print("\n✅ Email login page fix verified!")
    else:
        print("\n❌ Email login page still has issues")
        sys.exit(1)