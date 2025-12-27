from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from flask_login import current_user, login_required
from models import db, User
from forms import RegistrationForm, EmailVerificationForm, ResendVerificationForm, AdminApprovalForm
from datetime import datetime
from werkzeug.exceptions import RequestEntityTooLarge
import secrets
import string
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

registration_bp = Blueprint('registration', __name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

@registration_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")  # Rate limiting for registration
def register():
    """Handle user self-registration"""
    try:
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        
        form = RegistrationForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Get IP and user agent for security
                    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                    user_agent = request.headers.get('User-Agent')
                    
                    # Create new user
                    user = User(username=form.username.data)
                    user.set_password(form.password.data)
                    user.full_name = form.full_name.data
                    
                    # Format phone number
                    from utils.otp_manager import OTPManager
                    is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(form.phone.data)
                    if is_valid:
                        user.phone = formatted_phone
                    
                    # Set default role
                    user.role = 'cashier'  # Default role for new registrations
                    user.is_active = False  # User needs approval
                    
                    # Initialize registration process
                    success, message = user.initiate_registration(
                        email=form.email.data,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    if success:
                        # Send verification email
                        from utils.email_service import EmailService
                        email_service = EmailService()
                        
                        verification_url = url_for('registration.verify_email', 
                                                token=user.email_verification_token, 
                                                _external=True)
                        
                        success, email_message = email_service.send_registration_verification_email(
                            email=user.email_decrypted,
                            username=user.username,
                            verification_url=verification_url
                        )
                        
                        if success:
                            return jsonify({
                                'success': True,
                                'message': 'Registration successful! Please check your email for verification.',
                                'redirect': url_for('registration.registration_success')
                            })
                        else:
                            # Log the email failure but don't fail registration
                            print(f"Email sending failed: {email_message}")
                            return jsonify({
                                'success': True,
                                'message': 'Registration successful! Please check your email for verification.',
                                'redirect': url_for('registration.registration_success')
                            })
                    else:
                        return jsonify({
                            'success': False,
                            'message': message
                        }), 400
                else:
                    return jsonify({
                        'success': False,
                        'errors': form.errors,
                        'message': 'Please fix the errors below'
                    }), 400
            
            # Regular form submission
            if form.validate_on_submit():
                # Get IP and user agent for security
                ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                user_agent = request.headers.get('User-Agent')
                
                # Create new user
                user = User(username=form.username.data)
                user.set_password(form.password.data)
                user.full_name = form.full_name.data
                
                # Format phone number
                from utils.otp_manager import OTPManager
                is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(form.phone.data)
                if is_valid:
                    user.phone = formatted_phone
                
                # Set default role
                user.role = 'cashier'  # Default role for new registrations
                user.is_active = False  # User needs approval
                
                # Initialize registration process
                success, message = user.initiate_registration(
                    email=form.email.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    # Send verification email
                    from utils.email_service import EmailService
                    email_service = EmailService()
                    
                    verification_url = url_for('registration.verify_email', 
                                            token=user.email_verification_token, 
                                            _external=True)
                    
                    success, email_message = email_service.send_registration_verification_email(
                        email=user.email_decrypted,
                        username=user.username,
                        verification_url=verification_url
                    )
                    
                    if success:
                        flash('Registration successful! Please check your email for verification.', 'success')
                        return redirect(url_for('registration.registration_success'))
                    else:
                        # Log the email failure but don't fail registration
                        print(f"Email sending failed: {email_message}")
                        flash('Registration successful! Please check your email for verification.', 'success')
                        return redirect(url_for('registration.registration_success'))
                else:
                    flash(message, 'error')
        
        return render_template('auth/register.html', form=form)
    
    except RequestEntityTooLarge:
        flash('File size too large. Please reduce the file size and try again.', 'error')
        return render_template('auth/register.html', form=form)
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Registration error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('auth/register.html', form=form)

@registration_bp.route('/registration-success')
def registration_success():
    """Show registration success page"""
    return render_template('auth/registration-success.html')

@registration_bp.route('/register/verify-email', methods=['GET', 'POST'])
@limiter.limit("10 per hour")  # Rate limiting for email verification
def verify_email():
    """Handle email verification"""
    try:
        # Get token from URL parameters or form
        token = request.args.get('token') or request.form.get('token')
        
        if not token:
            flash('Invalid verification link.', 'error')
            return redirect(url_for('auth.login'))
        
        # Find user with this token
        user = User.query.filter_by(email_verification_token=token).first()
        
        if not user:
            flash('Invalid verification link.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if email is already verified
        if user.email_verified:
            flash('Email is already verified. You can proceed to login.', 'info')
            return redirect(url_for('auth.login'))
        
        # Check if token has expired
        if user.email_verification_expires and datetime.utcnow() > user.email_verification_expires:
            flash('Verification link has expired. Please request a new one.', 'error')
            return render_template('auth/verify-registration-email.html', user=user, token=token)
        
        form = EmailVerificationForm()
        
        # Handle GET request with token
        if request.method == 'GET' and token:
            return render_template('auth/verify-registration-email.html', user=user, token=token)
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Verify email
                    success, message = user.verify_email(token)
                    
                    if success:
                        return jsonify({
                            'success': True,
                            'message': 'Email verified successfully! Your registration is now pending admin approval.',
                            'redirect': url_for('registration.email_verified_success')
                        })
                    else:
                        # Increment attempts
                        user.increment_email_verification_attempts()
                        return jsonify({
                            'success': False,
                            'message': message
                        }), 400
                else:
                    return jsonify({
                        'success': False,
                        'errors': form.errors,
                        'message': 'Please fix the errors below'
                    }), 400
            
            # Regular form submission
            if form.validate_on_submit():
                # Verify email
                success, message = user.verify_email(token)
                
                if success:
                    flash('Email verified successfully! Your registration is now pending admin approval.', 'success')
                    return redirect(url_for('registration.email_verified_success'))
                else:
                    # Increment attempts
                    user.increment_email_verification_attempts()
                    flash(message, 'error')
        
        return render_template('auth/verify-registration-email.html', user=user, token=token, form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'token': token if 'token' in locals() else None
        }
        
        print(f"Email verification error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@registration_bp.route('/register/email-verified-success')
def email_verified_success():
    """Show email verification success page"""
    return render_template('auth/email-verified-success.html')

@registration_bp.route('/register/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    """Resend verification email"""
    try:
        form = ResendVerificationForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Find user
                    user = User.get_by_email_encrypted(form.email.data)
                    
                    if user and not user.email_verified:
                        # Resend verification email
                        success, token = user.resend_verification_email()
                        
                        if success:
                            # Send verification email
                            from utils.email_service import EmailService
                            email_service = EmailService()
                            
                            verification_url = url_for('registration.verify_email', 
                                                    token=token, 
                                                    _external=True)
                            
                            email_success, email_message = email_service.send_registration_verification_email(
                                email=user.email_decrypted,
                                username=user.username,
                                verification_url=verification_url
                            )
                            
                            return jsonify({
                                'success': True,
                                'message': 'Verification email has been resent. Please check your inbox.'
                            })
                        else:
                            return jsonify({
                                'success': False,
                                'message': 'Unable to resend verification email. Please try again later.'
                            }), 500
                    else:
                        return jsonify({
                            'success': False,
                            'message': 'Invalid email address or email already verified.'
                        }), 400
                else:
                    return jsonify({
                        'success': False,
                        'errors': form.errors,
                        'message': 'Please fix the errors below'
                    }), 400
            
            # Regular form submission
            if form.validate_on_submit():
                # Find user
                user = User.get_by_email_encrypted(form.email.data)
                
                if user and not user.email_verified:
                    # Resend verification email
                    success, token = user.resend_verification_email()
                    
                    if success:
                        # Send verification email
                        from utils.email_service import EmailService
                        email_service = EmailService()
                        
                        verification_url = url_for('registration.verify_email', 
                                                token=token, 
                                                _external=True)
                        
                        email_success, email_message = email_service.send_registration_verification_email(
                            email=user.email_decrypted,
                            username=user.username,
                            verification_url=verification_url
                        )
                        
                        flash('Verification email has been resent. Please check your inbox.', 'success')
                        return redirect(url_for('registration.verify_email'))
                    else:
                        flash('Unable to resend verification email. Please try again later.', 'error')
                else:
                    flash('Invalid email address or email already verified.', 'error')
        
        return render_template('auth/resend-verification.html', form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Resend verification error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('auth/resend-verification.html', form=form)

# Admin Registration Management Routes

@registration_bp.route('/admin/registrations', methods=['GET'])
@login_required
def admin_registrations():
    """Admin view for managing registrations"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Get filter parameters
    status_filter = request.args.get('status', 'pending')
    search_term = request.args.get('search', '')
    
    # Build query
    query = User.query.filter(
        User.registration_status.in_(['pending', 'verified', 'pending_approval'])
    )
    
    # Apply status filter
    if status_filter != 'all':
        query = query.filter(User.registration_status == status_filter)
    
    # Apply search filter
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            db.or_(
                User.username.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )
    
    registrations = query.order_by(User.registration_timestamp.desc()).all()
    
    return render_template('auth/admin-registrations.html', 
                         registrations=registrations, 
                         status_filter=status_filter,
                         search_term=search_term)

@registration_bp.route('/admin/registrations/<int:user_id>/approve', methods=['POST'])
@login_required
def approve_registration(user_id):
    """Approve user registration"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'}), 403
    
    form = AdminApprovalForm()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if form.validate_on_submit():
            user = User.query.get_or_404(user_id)
            
            if form.action.data == 'approve':
                success, message = user.approve_registration(
                    admin_user=current_user,
                    admin_notes=form.notes.data
                )
                
                if success:
                    # Send approval email
                    from utils.email_service import EmailService
                    email_service = EmailService()
                    
                    email_service.send_registration_approval_email(
                        email=user.email_decrypted,
                        username=user.username
                    )
                    
                    return jsonify({
                        'success': True,
                        'message': 'Registration approved successfully!'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': message
                    }), 400
            
            elif form.action.data == 'reject':
                if not form.notes.data:
                    return jsonify({
                        'success': False,
                        'message': 'Reason for rejection is required.'
                    }), 400
                
                success, message = user.reject_registration(
                    admin_user=current_user,
                    reason=form.notes.data,
                    admin_notes=form.notes.data
                )
                
                if success:
                    # Send rejection email
                    from utils.email_service import EmailService
                    email_service = EmailService()
                    
                    email_service.send_registration_rejection_email(
                        email=user.email_decrypted,
                        username=user.username,
                        reason=form.notes.data
                    )
                    
                    return jsonify({
                        'success': True,
                        'message': 'Registration rejected successfully!'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': message
                    }), 400
        else:
            return jsonify({
                'success': False,
                'errors': form.errors,
                'message': 'Please fix the errors below'
            }), 400
    
    return jsonify({'success': False, 'message': 'Invalid request'}), 400

@registration_bp.route('/admin/registrations/<int:user_id>/details', methods=['GET'])
@login_required
def registration_details(user_id):
    """Get registration details for admin review"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'}), 403
    
    user = User.query.get_or_404(user_id)
    
    return jsonify({
        'success': True,
        'registration': user.get_registration_info()
    })

# API endpoints for registration

@registration_bp.route('/api/register/check-username', methods=['POST'])
def api_check_username():
    """API endpoint to check username availability"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data:
            return jsonify({
                'success': False,
                'message': 'Username is required'
            }), 400
        
        username = data['username']
        
        # Validate username format
        if len(username) < 3 or len(username) > 80:
            return jsonify({
                'success': False,
                'available': False,
                'message': 'Username must be between 3 and 80 characters'
            })
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return jsonify({
                'success': False,
                'available': False,
                'message': 'Username can only contain letters, numbers, and underscores'
            })
        
        # Check if username exists
        user = User.query.filter_by(username=username).first()
        
        if user:
            return jsonify({
                'success': True,
                'available': False,
                'message': 'Username is already taken'
            })
        else:
            return jsonify({
                'success': True,
                'available': True,
                'message': 'Username is available'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error checking username availability'
        }), 500

@registration_bp.route('/api/register/check-email', methods=['POST'])
def api_check_email():
    """API endpoint to check email availability"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        email = data['email']
        
        # Validate email format
        from utils.email_service import EmailService
        email_service = EmailService()
        
        if not email_service.validate_email_address(email):
            return jsonify({
                'success': False,
                'available': False,
                'message': 'Invalid email address format'
            })
        
        # Check if email exists
        user = User.get_by_email_encrypted(email)
        
        if user:
            return jsonify({
                'success': True,
                'available': False,
                'message': 'Email is already registered'
            })
        else:
            return jsonify({
                'success': True,
                'available': True,
                'message': 'Email is available'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error checking email availability'
        }), 500

@registration_bp.route('/api/register/check-phone', methods=['POST'])
def api_check_phone():
    """API endpoint to check phone availability"""
    try:
        data = request.get_json()
        
        if not data or 'phone' not in data:
            return jsonify({
                'success': False,
                'message': 'Phone number is required'
            }), 400
        
        phone = data['phone']
        
        # Validate phone number
        from utils.otp_manager import OTPManager
        is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(phone)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'available': False,
                'message': error_msg
            })
        
        # Check if phone exists
        user = User.query.filter_by(phone=formatted_phone).first()
        
        if user:
            return jsonify({
                'success': True,
                'available': False,
                'message': 'Phone number is already registered'
            })
        else:
            return jsonify({
                'success': True,
                'available': True,
                'message': 'Phone number is available'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error checking phone availability'
        }), 500