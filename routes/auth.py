from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from forms import LoginForm, ProfileEditForm, ChangePasswordForm, NotificationPreferencesForm, ForgotPasswordForm, ResetPasswordForm, MobileOTPLoginForm, MobileOTPVerifyForm, PhoneVerificationForm, PhoneVerificationCodeForm, MobileOTPSettingsForm, EmailOTPLoginForm, EmailOTPVerifyForm, EmailVerificationForm, EmailVerificationCodeForm, EmailOTPSettingsForm
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/test')
def test():
    """Simple test route to debug"""
    return "Test route working!"

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login with enhanced features"""
    try:
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        
        form = LoginForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    login_user(form.user, remember=form.remember.data)
                    form.user.update_last_login()
                    
                    # Determine redirect URL
                    next_page = request.args.get('next')
                    redirect_url = next_page if next_page and next_page.startswith('/') else url_for('dashboard.index')
                    
                    return jsonify({
                        'success': True,
                        'message': f'Welcome back, {form.user.username}!',
                        'redirect': redirect_url
                    })
                else:
                    return jsonify({
                        'success': False,
                        'errors': form.errors,
                        'message': 'Invalid username or password'
                    }), 400
            
            # Regular form submission
            if form.validate_on_submit():
                login_user(form.user, remember=form.remember.data)
                form.user.update_last_login()
                
                # Redirect to requested page or dashboard
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                
                flash(f'Welcome back, {form.user.username}!', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                # Provide more specific error messages
                if form.username.errors:
                    for error in form.username.errors:
                        flash(error, 'error')
                elif form.password.errors:
                    for error in form.password.errors:
                        flash(error, 'error')
                else:
                    flash('Invalid username or password', 'error')
        
        return render_template('auth/login.html', form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'form_data': dict(request.form) if request.method == 'POST' else None,
            'csrf_token': request.form.get('csrf_token', 'Not found') if request.method == 'POST' else None
        }
        
        # In production, you'd log this properly instead of printing
        print(f"Login error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """Enhanced user profile page with edit capabilities"""
    try:
        # Get user preferences
        preferences = current_user.get_notification_preferences()
        
        # Calculate profile completion
        completion_percentage = current_user.get_profile_completion_percentage()
        
        # Get missing required fields
        missing_fields = []
        if not current_user.full_name:
            missing_fields.append('full_name')
        if not current_user.email_decrypted:
            missing_fields.append('email')
        if not current_user.phone:
            missing_fields.append('phone')
        
        return render_template('auth/profile.html', 
                             preferences=preferences,
                             completion_percentage=completion_percentage,
                             missing_fields=missing_fields)
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'user_id': current_user.id if current_user.is_authenticated else None
        }
        
        # In production, you'd log this properly instead of printing
        print(f"Profile page error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'Error loading profile page',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('Error loading profile page', 'error')
        return redirect(url_for('dashboard.index'))

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    form = ProfileEditForm()
    
    # Pre-populate form with current user data
    if request.method == 'GET':
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email_decrypted
        form.phone.data = current_user.phone
        form.address.data = current_user.address
        form.bio.data = current_user.bio
        form.date_of_birth.data = current_user.date_of_birth
        form.preferred_language.data = current_user.preferred_language
        form.preferred_timezone.data = current_user.preferred_timezone
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Handle avatar upload
            avatar_filename = None
            if form.avatar.data:
                avatar_filename = save_avatar_upload(form.avatar.data, current_user.id)
                if avatar_filename:
                    # Remove old avatar if exists
                    if current_user.avatar_path:
                        try:
                            old_avatar_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars', current_user.avatar_path)
                            if os.path.exists(old_avatar_path):
                                os.remove(old_avatar_path)
                        except Exception as e:
                            print(f"Error removing old avatar: {e}")
                    
                    current_user.update_avatar(avatar_filename)
            
            # Update profile data
            profile_data = {
                'full_name': form.full_name.data,
                'phone': form.phone.data,
                'address': form.address.data,
                'bio': form.bio.data,
                'date_of_birth': form.date_of_birth.data,
                'preferred_language': form.preferred_language.data,
                'preferred_timezone': form.preferred_timezone.data
            }
            
            # Handle email separately due to encryption
            if form.email.data != current_user.email_decrypted:
                current_user.email = current_user._encrypt_email(form.email.data)
            
            current_user.update_profile(**profile_data)
            
            # Log profile update
            log_profile_activity(current_user.id, 'profile_updated', 'User updated profile information')
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            # Log error
            import traceback
            error_details = {
                'error': str(e),
                'traceback': traceback.format_exc(),
                'user_id': current_user.id
            }
            print(f"Profile update error: {error_details}")
            
            flash('Error updating profile. Please try again.', 'error')
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if form.errors:
            return jsonify({
                'success': False,
                'errors': form.errors,
                'message': 'Please fix the errors below'
            }), 400
        else:
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            })
    
    return render_template('auth/edit_profile.html', form=form)

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Enhanced change password with strong validation"""
    form = ChangePasswordForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Check if current password is correct
            if not current_user.check_password(form.current_password.data):
                current_user.increment_failed_login_attempts()
                flash('Current password is incorrect', 'error')
                return render_template('auth/change_password.html', form=form)
            
            # Check if account is locked
            if current_user.is_account_locked():
                flash('Account is temporarily locked due to multiple failed attempts. Please try again later.', 'error')
                return render_template('auth/change_password.html', form=form)
            
            # Check if new password is different from current
            if current_user.check_password(form.new_password.data):
                flash('New password must be different from current password', 'error')
                return render_template('auth/change_password.html', form=form)
            
            # Update password using the enhanced method
            current_user.update_password(form.new_password.data)
            
            # Log password change
            log_profile_activity(current_user.id, 'password_changed', 'User changed password')
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            # Log error
            import traceback
            error_details = {
                'error': str(e),
                'traceback': traceback.format_exc(),
                'user_id': current_user.id
            }
            print(f"Password change error: {error_details}")
            
            flash('Error changing password. Please try again.', 'error')
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if form.errors:
            return jsonify({
                'success': False,
                'errors': form.errors,
                'message': 'Please fix the errors below'
            }), 400
        else:
            return jsonify({
                'success': True,
                'message': 'Password changed successfully'
            })
    
    return render_template('auth/change_password.html', form=form)

# API endpoints for AJAX requests
@auth_bp.route('/api/check_session')
def check_session():
    """Check if user is logged in (for AJAX)"""
    if current_user.is_authenticated:
        return jsonify({
            'logged_in': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'role': current_user.role
            }
        })
    return jsonify({'logged_in': False})

@auth_bp.route('/profile/preferences', methods=['GET', 'POST'])
@login_required
def notification_preferences():
    """Manage user notification preferences"""
    form = NotificationPreferencesForm()
    
    # Load current preferences
    if request.method == 'GET':
        preferences = current_user.get_notification_preferences()
        form.email_notifications.data = preferences.get('email_notifications', True)
        form.order_updates.data = preferences.get('order_updates', True)
        form.marketing_emails.data = preferences.get('marketing_emails', False)
        form.system_alerts.data = preferences.get('system_alerts', True)
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Update preferences
            preferences = {
                'email_notifications': form.email_notifications.data,
                'order_updates': form.order_updates.data,
                'marketing_emails': form.marketing_emails.data,
                'system_alerts': form.system_alerts.data
            }
            
            current_user.set_notification_preferences(preferences)
            
            # Log preference update
            log_profile_activity(current_user.id, 'preferences_updated', 'User updated notification preferences')
            
            flash('Notification preferences updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            # Log error
            import traceback
            error_details = {
                'error': str(e),
                'traceback': traceback.format_exc(),
                'user_id': current_user.id
            }
            print(f"Preferences update error: {error_details}")
            
            flash('Error updating preferences. Please try again.', 'error')
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if form.errors:
            return jsonify({
                'success': False,
                'errors': form.errors,
                'message': 'Please fix the errors below'
            }), 400
        else:
            return jsonify({
                'success': True,
                'message': 'Preferences updated successfully'
            })
    
    return render_template('auth/notification_preferences.html', form=form)

@auth_bp.route('/profile/avatar/<int:user_id>')
def get_avatar(user_id):
    """Serve user avatar image"""
    user = User.query.get_or_404(user_id)
    
    if not user.avatar_path:
        # Return default avatar based on username
        return redirect(url_for('static', filename='images/default-avatar.png'))
    
    avatar_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'avatars', user.avatar_path)
    
    if os.path.exists(avatar_path):
        return send_from_directory(os.path.dirname(avatar_path), os.path.basename(avatar_path))
    else:
        return redirect(url_for('static', filename='images/default-avatar.png'))

# Helper Functions

def save_avatar_upload(file_data, user_id):
    """Save uploaded avatar file"""
    try:
        # Create upload directories
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        avatar_folder = os.path.join(upload_folder, 'avatars')
        os.makedirs(avatar_folder, exist_ok=True)
        
        # Check file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if '.' not in file_data.filename:
            return None
        
        file_ext = file_data.filename.rsplit('.', 1)[1].lower()
        if file_ext not in allowed_extensions:
            flash('Invalid file type. Please upload PNG, JPG, JPEG, or GIF files.', 'error')
            return None
        
        # Check file size (max 5MB)
        file_data.stream.seek(0, 2)  # Seek to end
        file_size = file_data.stream.tell()
        file_data.stream.seek(0)  # Reset to beginning
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            flash('File size too large. Maximum size is 5MB.', 'error')
            return None
        
        # Generate unique filename
        filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
        filepath = os.path.join(avatar_folder, filename)
        
        # Save file
        file_data.save(filepath)
        
        return filename
        
    except Exception as e:
        print(f"Error saving avatar: {e}")
        flash('Error uploading avatar. Please try again.', 'error')
        return None

def log_profile_activity(user_id, activity_type, description):
    """Log profile activity for audit purposes"""
    try:
        from models.audit_log import AuditLog
        
        log_entry = AuditLog(
            user_id=user_id,
            action=activity_type,
            description=description,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
    except Exception as e:
        print(f"Error logging profile activity: {e}")
        # Don't fail the main operation if logging fails

def log_password_activity(user_id, activity_type, description):
    """Log password activity for audit purposes"""
    try:
        from models.audit_log import AuditLog
        
        log_entry = AuditLog(
            user_id=user_id,
            action=activity_type,
            description=description,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
    except Exception as e:
        print(f"Error logging password activity: {e}")
        # Don't fail the main operation if logging fails

# API endpoints for password reset
@auth_bp.route('/api/auth/forgot_password', methods=['POST'])
def api_forgot_password():
    """API endpoint for forgot password (AJAX)"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        # Find user by email
        user = User.get_by_email_encrypted(data['email'])
        
        if not user:
            # Don't reveal whether email exists for security
            return jsonify({
                'success': True,
                'message': 'If an account exists with this email, a password reset link will be sent.'
            })
        
        # Check if user can request reset
        can_request, message = user.can_request_password_reset()
        if not can_request:
            return jsonify({
                'success': False,
                'message': message
            }), 429  # Too Many Requests
        
        # Generate reset token
        reset_token = user.generate_password_reset_token()
        
        # Get email service instance
        from utils.email_service import EmailService
        email_service = EmailService()
        
        # Create reset URL
        reset_url = url_for('auth.reset_password', token=reset_token, _external=True)
        
        # Send password reset email
        success, email_message = email_service.send_password_reset_email(
            email=user.email_decrypted,
            reset_url=reset_url,
            username=user.username
        )
        
        if success:
            # Log the password reset request
            log_password_activity(user.id, 'password_reset_requested', 
                                f'Password reset requested for {user.email_decrypted}')
            
            return jsonify({
                'success': True,
                'message': 'Password reset instructions have been sent to your email.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to send reset email. Please try again later.'
            }), 500
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'request_data': data if 'data' in locals() else None
        }
        
        print(f"API forgot password error details: {error_details}")
        
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'debug': str(e) if current_app.debug else None
        }), 500

@auth_bp.route('/api/auth/reset_password', methods=['POST'])
def api_reset_password():
    """API endpoint for password reset (AJAX)"""
    try:
        data = request.get_json()
        
        if not data or 'token' not in data or 'new_password' not in data:
            return jsonify({
                'success': False,
                'message': 'Token and new password are required'
            }), 400
        
        # Find user with this token
        user = User.query.filter_by(password_reset_token=data['token']).first()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired reset link. Please request a new password reset.'
            }), 400
        
        # Validate token
        is_valid, message = user.validate_password_reset_token(data['token'])
        
        if not is_valid:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # Reset password using token
        success, reset_message = user.reset_password_with_token(data['token'], data['new_password'])
        
        if success:
            # Log successful password reset
            log_password_activity(user.id, 'password_reset_completed', 
                                f'Password reset completed for {user.email_decrypted}')
            
            return jsonify({
                'success': True,
                'message': 'Password reset successfully! You can now login with your new password.'
            })
        else:
            return jsonify({
                'success': False,
                'message': reset_message
            }), 400
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'request_data': data if 'data' in locals() else None
        }
        
        print(f"API reset password error details: {error_details}")
        
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'debug': str(e) if current_app.debug else None
        }), 500

@auth_bp.route('/api/auth/validate_reset_token', methods=['POST'])
def api_validate_reset_token():
    """API endpoint to validate reset token"""
    try:
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({
                'success': False,
                'message': 'Token is required'
            }), 400
        
        # Find user with this token
        user = User.query.filter_by(password_reset_token=data['token']).first()
        
        if not user:
            return jsonify({
                'success': False,
                'valid': False,
                'message': 'Invalid reset token'
            }), 400
        
        # Validate token
        is_valid, message = user.validate_password_reset_token(data['token'])
        
        if is_valid:
            return jsonify({
                'success': True,
                'valid': True,
                'message': 'Token is valid'
            })
        else:
            return jsonify({
                'success': True,
                'valid': False,
                'message': message
            })
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'request_data': data if 'data' in locals() else None
        }
        
        print(f"API validate token error details: {error_details}")
        
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'debug': str(e) if current_app.debug else None
        }), 500

@auth_bp.route('/api/keep_alive')
@login_required
def keep_alive():
    """Keep session alive (for AJAX)"""
    return jsonify({'status': 'alive', 'timestamp': datetime.utcnow().isoformat()})

# Password Reset Routes
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password request"""
    try:
        form = ForgotPasswordForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Get the user from the validated email
                    user = User.get_by_email_encrypted(form.email.data)
                    
                    # Generate reset token
                    reset_token = user.generate_password_reset_token()
                    
                    # Get email service instance
                    from utils.email_service import EmailService
                    email_service = EmailService()
                    
                    # Create reset URL
                    reset_url = url_for('auth.reset_password', token=reset_token, _external=True)
                    
                    # Send password reset email
                    success, message = email_service.send_password_reset_email(
                        email=user.email_decrypted,
                        reset_url=reset_url,
                        username=user.username
                    )
                    
                    if success:
                        # Log the password reset request
                        log_password_activity(user.id, 'password_reset_requested', 
                                            f'Password reset requested for {user.email_decrypted}')
                        
                        return jsonify({
                            'success': True,
                            'message': 'Password reset instructions have been sent to your email.'
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'message': 'Unable to send reset email. Please try again later.'
                        }), 500
                else:
                    return jsonify({
                        'success': False,
                        'errors': form.errors,
                        'message': 'Please fix the errors below'
                    }), 400
            
            # Regular form submission
            if form.validate_on_submit():
                # Get the user from the validated email
                user = User.get_by_email_encrypted(form.email.data)
                
                # Generate reset token
                reset_token = user.generate_password_reset_token()
                
                # Get email service instance
                from utils.email_service import EmailService
                email_service = EmailService()
                
                # Create reset URL
                reset_url = url_for('auth.reset_password', token=reset_token, _external=True)
                
                # Send password reset email
                success, message = email_service.send_password_reset_email(
                    email=user.email_decrypted,
                    reset_url=reset_url,
                    username=user.username
                )
                
                if success:
                    # Log the password reset request
                    log_password_activity(user.id, 'password_reset_requested', 
                                        f'Password reset requested for {user.email_decrypted}')
                    
                    flash('Password reset instructions have been sent to your email.', 'success')
                    return redirect(url_for('auth.login'))
                else:
                    flash('Unable to send reset email. Please try again later.', 'error')
        
        return render_template('auth/forgot_password.html', form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Forgot password error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    try:
        # Find user with this token
        user = User.query.filter_by(password_reset_token=token).first()
        
        if not user:
            flash('Invalid or expired reset link. Please request a new password reset.', 'error')
            return redirect(url_for('auth.forgot_password'))
        
        # Validate token
        is_valid, message = user.validate_password_reset_token(token)
        
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('auth.forgot_password'))
        
        form = ResetPasswordForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Reset password using token
                    success, message = user.reset_password_with_token(token, form.new_password.data)
                    
                    if success:
                        # Log successful password reset
                        log_password_activity(user.id, 'password_reset_completed', 
                                            f'Password reset completed for {user.email_decrypted}')
                        
                        return jsonify({
                            'success': True,
                            'message': 'Password reset successfully! Redirecting to login...',
                            'redirect': url_for('auth.login')
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
                # Reset password using token
                success, message = user.reset_password_with_token(token, form.new_password.data)
                
                if success:
                    # Log successful password reset
                    log_password_activity(user.id, 'password_reset_completed', 
                                        f'Password reset completed for {user.email_decrypted}')
                    
                    flash('Password reset successfully! Please login with your new password.', 'success')
                    return redirect(url_for('auth.login'))
                else:
                    flash(message, 'error')
        
        return render_template('auth/reset_password.html', form=form, token=token)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'token': token,
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Reset password error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('auth.forgot_password'))

# Mobile OTP Authentication Routes

@auth_bp.route('/mobile-login', methods=['GET', 'POST'])
def mobile_login():
    """Handle mobile OTP login"""
    try:
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        
        form = MobileOTPLoginForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Get IP and user agent for security
                    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                    user_agent = request.headers.get('User-Agent')
                    
                    # Initiate mobile OTP login
                    from utils.otp_manager import MobileOTPLoginManager
                    
                    success, message, otp_id = MobileOTPLoginManager.initiate_login(
                        phone_number=form.phone.data,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    if success:
                        return jsonify({
                            'success': True,
                            'message': message,
                            'redirect': url_for('auth.mobile_verify', otp_id=otp_id)
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
                
                # Initiate mobile OTP login
                from utils.otp_manager import MobileOTPLoginManager
                
                success, message, otp_id = MobileOTPLoginManager.initiate_login(
                    phone_number=form.phone.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    flash(message, 'success')
                    return redirect(url_for('auth.mobile_verify', otp_id=otp_id))
                else:
                    flash(message, 'error')
        
        return render_template('auth/mobile_login.html', form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Mobile login error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('auth/mobile_login.html', form=form)

@auth_bp.route('/mobile-verify/<int:otp_id>', methods=['GET', 'POST'])
def mobile_verify(otp_id):
    """Handle mobile OTP verification"""
    try:
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        
        # Get OTP record
        from models.otp import OTP
        otp = OTP.query.get(otp_id)
        
        if not otp:
            flash('Invalid verification link. Please try again.', 'error')
            return redirect(url_for('auth.mobile_login'))
        
        # Check if OTP is expired
        if otp.is_expired():
            flash('Verification code has expired. Please request a new one.', 'error')
            return redirect(url_for('auth.mobile_login'))
        
        form = MobileOTPVerifyForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Get IP and user agent for security
                    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                    user_agent = request.headers.get('User-Agent')
                    
                    # Complete mobile OTP login
                    from utils.otp_manager import MobileOTPLoginManager
                    
                    success, message, user = MobileOTPLoginManager.complete_login(
                        otp_id=otp_id,
                        otp_code=form.otp_code.data,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    if success:
                        # Login user
                        login_user(user, remember=form.remember.data)
                        
                        return jsonify({
                            'success': True,
                            'message': 'Login successful!',
                            'redirect': url_for('dashboard.index')
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
                
                # Complete mobile OTP login
                from utils.otp_manager import MobileOTPLoginManager
                
                success, message, user = MobileOTPLoginManager.complete_login(
                    otp_id=otp_id,
                    otp_code=form.otp_code.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    # Login user
                    login_user(user, remember=form.remember.data)
                    
                    flash('Login successful!', 'success')
                    return redirect(url_for('dashboard.index'))
                else:
                    flash(message, 'error')
        
        return render_template('auth/mobile_verify.html', form=form, otp=otp)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'otp_id': otp_id,
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Mobile verify error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('auth.mobile_login'))

@auth_bp.route('/resend-otp/<int:otp_id>', methods=['POST'])
def resend_otp(otp_id):
    """Resend OTP code"""
    try:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Resend OTP
            from utils.otp_manager import OTPManager
            
            success, message = OTPManager.resend_otp(otp_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message
                })
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 400
        
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'otp_id': otp_id
        }
        
        print(f"Resend OTP error details: {error_details}")
        
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.'
        }), 500

# Phone Verification Routes

@auth_bp.route('/verify-phone', methods=['GET', 'POST'])
@login_required
def verify_phone():
    """Handle phone verification"""
    try:
        form = PhoneVerificationForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Initiate phone verification
                    from utils.otp_manager import PhoneVerificationManager
                    
                    success, message, otp_id = PhoneVerificationManager.initiate_verification(
                        user=current_user,
                        phone_number=form.phone.data
                    )
                    
                    if success:
                        return jsonify({
                            'success': True,
                            'message': message,
                            'redirect': url_for('auth.verify_phone_code', otp_id=otp_id)
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
                # Initiate phone verification
                from utils.otp_manager import PhoneVerificationManager
                
                success, message, otp_id = PhoneVerificationManager.initiate_verification(
                    user=current_user,
                    phone_number=form.phone.data
                )
                
                if success:
                    flash(message, 'success')
                    return redirect(url_for('auth.verify_phone_code', otp_id=otp_id))
                else:
                    flash(message, 'error')
        
        return render_template('auth/verify_phone.html', form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Phone verification error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('auth/verify_phone.html', form=form)

@auth_bp.route('/verify-phone-code/<int:otp_id>', methods=['GET', 'POST'])
@login_required
def verify_phone_code(otp_id):
    """Handle phone verification code"""
    try:
        # Get OTP record
        from models.otp import OTP
        otp = OTP.query.get(otp_id)
        
        if not otp:
            flash('Invalid verification link. Please try again.', 'error')
            return redirect(url_for('auth.verify_phone'))
        
        # Check if OTP is expired
        if otp.is_expired():
            flash('Verification code has expired. Please request a new one.', 'error')
            return redirect(url_for('auth.verify_phone'))
        
        form = PhoneVerificationCodeForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Complete phone verification
                    from utils.otp_manager import PhoneVerificationManager
                    
                    success, message = PhoneVerificationManager.complete_verification(
                        otp_id=otp_id,
                        otp_code=form.verification_code.data,
                        user=current_user
                    )
                    
                    if success:
                        return jsonify({
                            'success': True,
                            'message': message,
                            'redirect': url_for('auth.profile')
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
                # Complete phone verification
                from utils.otp_manager import PhoneVerificationManager
                
                success, message = PhoneVerificationManager.complete_verification(
                    otp_id=otp_id,
                    otp_code=form.verification_code.data,
                    user=current_user
                )
                
                if success:
                    flash(message, 'success')
                    return redirect(url_for('auth.profile'))
                else:
                    flash(message, 'error')
        
        return render_template('auth/verify_phone_code.html', form=form, otp=otp)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'otp_id': otp_id,
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Phone verification code error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('auth.verify_phone'))

# Mobile OTP Settings Routes

@auth_bp.route('/mobile-otp-settings', methods=['GET', 'POST'])
@login_required
def mobile_otp_settings():
    """Manage mobile OTP settings"""
    try:
        form = MobileOTPSettingsForm()
        
        # Load current settings
        if request.method == 'GET':
            form.phone.data = current_user.phone
            form.mobile_otp_enabled.data = current_user.mobile_otp_enabled
            form.backup_phone.data = current_user.backup_phone
        
        if request.method == 'POST' and form.validate_on_submit():
            try:
                # Update phone number if changed
                if form.phone.data != current_user.phone:
                    from utils.otp_manager import PhoneVerificationManager
                    
                    success, message, otp_id = PhoneVerificationManager.initiate_verification(
                        user=current_user,
                        phone_number=form.phone.data
                    )
                    
                    if success:
                        flash(f'Phone number updated. Please verify your new number: {message}', 'success')
                        return redirect(url_for('auth.verify_phone_code', otp_id=otp_id))
                    else:
                        flash(f'Error updating phone number: {message}', 'error')
                        return render_template('auth/mobile_otp_settings.html', form=form)
                
                # Update other settings
                current_user.mobile_otp_enabled = form.mobile_otp_enabled.data
                current_user.backup_phone = form.backup_phone.data if form.backup_phone.data else None
                
                db.session.commit()
                
                flash('Mobile OTP settings updated successfully!', 'success')
                return redirect(url_for('auth.profile'))
                
            except Exception as e:
                # Log error
                import traceback
                error_details = {
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'user_id': current_user.id
                }
                print(f"Mobile OTP settings update error: {error_details}")
                
                flash('Error updating settings. Please try again.', 'error')
        
        return render_template('auth/mobile_otp_settings.html', form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'user_id': current_user.id if current_user.is_authenticated else None
        }
        
        print(f"Mobile OTP settings error details: {error_details}")
        
        flash('Error loading mobile OTP settings', 'error')
        return redirect(url_for('auth.profile'))

# Email OTP Authentication Routes

@auth_bp.route('/email-login', methods=['GET', 'POST'])
def email_login():
    """Handle email OTP login"""
    try:
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        
        form = EmailOTPLoginForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Get IP and user agent for security
                    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                    user_agent = request.headers.get('User-Agent')
                    
                    # Initiate email OTP login
                    from utils.otp_manager import EmailOTPLoginManager
                    
                    success, message, otp_id = EmailOTPLoginManager.initiate_login(
                        email=form.email.data,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    if success:
                        return jsonify({
                            'success': True,
                            'message': message,
                            'redirect': url_for('auth.email_verify', otp_id=otp_id)
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
                
                # Initiate email OTP login
                from utils.otp_manager import EmailOTPLoginManager
                
                success, message, otp_id = EmailOTPLoginManager.initiate_login(
                    email=form.email.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    flash(message, 'success')
                    return redirect(url_for('auth.email_verify', otp_id=otp_id))
                else:
                    flash(message, 'error')
        
        return render_template('auth/email_login.html', form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Email login error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('auth/email_login.html', form=form)

@auth_bp.route('/email-verify/<int:otp_id>', methods=['GET', 'POST'])
def email_verify(otp_id):
    """Handle email OTP verification"""
    try:
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        
        # Get OTP record
        from models.otp import OTP
        otp = OTP.query.get(otp_id)
        
        if not otp:
            flash('Invalid verification link. Please try again.', 'error')
            return redirect(url_for('auth.email_login'))
        
        # Check if OTP is expired
        if otp.is_expired():
            flash('Verification code has expired. Please request a new one.', 'error')
            return redirect(url_for('auth.email_login'))
        
        # Check if OTP is for email
        if otp.otp_type not in [OTP.TYPE_EMAIL_LOGIN, OTP.TYPE_EMAIL_VERIFICATION]:
            flash('Invalid verification code type.', 'error')
            return redirect(url_for('auth.email_login'))
        
        form = EmailOTPVerifyForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Get IP and user agent for security
                    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                    user_agent = request.headers.get('User-Agent')
                    
                    # Complete email OTP login
                    from utils.otp_manager import EmailOTPLoginManager
                    
                    success, message, user = EmailOTPLoginManager.complete_login(
                        otp_id=otp_id,
                        otp_code=form.otp_code.data,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    if success:
                        # Login user
                        login_user(user, remember=form.remember.data)
                        
                        return jsonify({
                            'success': True,
                            'message': 'Login successful!',
                            'redirect': url_for('dashboard.index')
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
                
                # Complete email OTP login
                from utils.otp_manager import EmailOTPLoginManager
                
                success, message, user = EmailOTPLoginManager.complete_login(
                    otp_id=otp_id,
                    otp_code=form.otp_code.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    # Login user
                    login_user(user, remember=form.remember.data)
                    
                    flash('Login successful!', 'success')
                    return redirect(url_for('dashboard.index'))
                else:
                    flash(message, 'error')
        
        return render_template('auth/email_verify.html', form=form, otp=otp)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'otp_id': otp_id,
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Email verify error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('auth.email_login'))

# Email Verification Routes

@auth_bp.route('/verify-email', methods=['GET', 'POST'])
@login_required
def verify_email():
    """Handle email verification"""
    try:
        form = EmailVerificationForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Set user ID for validation
                    form._user_id = current_user.id
                    
                    # Initiate email verification
                    from utils.otp_manager import EmailVerificationManager
                    
                    success, message, otp_id = EmailVerificationManager.initiate_verification(
                        user=current_user,
                        email=form.email.data
                    )
                    
                    if success:
                        return jsonify({
                            'success': True,
                            'message': message,
                            'redirect': url_for('auth.verify_email_code', otp_id=otp_id)
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
                # Set user ID for validation
                form._user_id = current_user.id
                
                # Initiate email verification
                from utils.otp_manager import EmailVerificationManager
                
                success, message, otp_id = EmailVerificationManager.initiate_verification(
                    user=current_user,
                    email=form.email.data
                )
                
                if success:
                    flash(message, 'success')
                    return redirect(url_for('auth.verify_email_code', otp_id=otp_id))
                else:
                    flash(message, 'error')
        
        return render_template('auth/verify_email.html', form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'form_data': dict(request.form) if request.method == 'POST' else None
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
        return render_template('auth/verify_email.html', form=form)

@auth_bp.route('/verify-email-code/<int:otp_id>', methods=['GET', 'POST'])
@login_required
def verify_email_code(otp_id):
    """Handle email verification code"""
    try:
        # Get OTP record
        from models.otp import OTP
        otp = OTP.query.get(otp_id)
        
        if not otp:
            flash('Invalid verification link. Please try again.', 'error')
            return redirect(url_for('auth.verify_email'))
        
        # Check if OTP is expired
        if otp.is_expired():
            flash('Verification code has expired. Please request a new one.', 'error')
            return redirect(url_for('auth.verify_email'))
        
        # Check if OTP is for email verification
        if otp.otp_type != OTP.TYPE_EMAIL_VERIFICATION:
            flash('Invalid verification code type.', 'error')
            return redirect(url_for('auth.verify_email'))
        
        form = EmailVerificationCodeForm()
        
        if request.method == 'POST':
            # Handle AJAX requests for better UX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if form.validate_on_submit():
                    # Complete email verification
                    from utils.otp_manager import EmailVerificationManager
                    
                    success, message = EmailVerificationManager.complete_verification(
                        otp_id=otp_id,
                        otp_code=form.verification_code.data,
                        user=current_user
                    )
                    
                    if success:
                        return jsonify({
                            'success': True,
                            'message': message,
                            'redirect': url_for('auth.profile')
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
                # Complete email verification
                from utils.otp_manager import EmailVerificationManager
                
                success, message = EmailVerificationManager.complete_verification(
                    otp_id=otp_id,
                    otp_code=form.verification_code.data,
                    user=current_user
                )
                
                if success:
                    flash(message, 'success')
                    return redirect(url_for('auth.profile'))
                else:
                    flash(message, 'error')
        
        return render_template('auth/verify_email_code.html', form=form, otp=otp)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'otp_id': otp_id,
            'form_data': dict(request.form) if request.method == 'POST' else None
        }
        
        print(f"Email verification code error details: {error_details}")
        
        # Handle AJAX error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'debug': str(e) if current_app.debug else None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('auth.verify_email'))

# Email OTP Settings Routes

@auth_bp.route('/email-otp-settings', methods=['GET', 'POST'])
@login_required
def email_otp_settings():
    """Manage email OTP settings"""
    try:
        form = EmailOTPSettingsForm()
        
        # Load current settings
        if request.method == 'GET':
            form.email.data = current_user.email_decrypted
            form.email_otp_enabled.data = current_user.email_otp_enabled
            form.backup_email.data = current_user.backup_email
        
        if request.method == 'POST' and form.validate_on_submit():
            try:
                # Update email if changed
                if form.email.data != current_user.email_decrypted:
                    from utils.otp_manager import EmailVerificationManager
                    
                    success, message, otp_id = EmailVerificationManager.initiate_verification(
                        user=current_user,
                        email=form.email.data
                    )
                    
                    if success:
                        flash(f'Email address updated. Please verify your new email: {message}', 'success')
                        return redirect(url_for('auth.verify_email_code', otp_id=otp_id))
                    else:
                        flash(f'Error updating email address: {message}', 'error')
                        return render_template('auth/email_otp_settings.html', form=form)
                
                # Update other settings
                current_user.email_otp_enabled = form.email_otp_enabled.data
                current_user.backup_email = form.backup_email.data if form.backup_email.data else None
                
                db.session.commit()
                
                flash('Email OTP settings updated successfully!', 'success')
                return redirect(url_for('auth.profile'))
                
            except Exception as e:
                # Log error
                import traceback
                error_details = {
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'user_id': current_user.id
                }
                print(f"Email OTP settings update error: {error_details}")
                
                flash('Error updating settings. Please try again.', 'error')
        
        return render_template('auth/email_otp_settings.html', form=form)
    
    except Exception as e:
        # Log error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'user_id': current_user.id if current_user.is_authenticated else None
        }
        
        print(f"Email OTP settings error details: {error_details}")
        
        flash('Error loading email OTP settings', 'error')
        return redirect(url_for('auth.profile'))

# API endpoints for mobile OTP

@auth_bp.route('/api/mobile-otp/status')
def api_mobile_otp_status():
    """API endpoint to check mobile OTP status"""
    try:
        # Check if Twilio service is enabled
        from utils.twilio_sms import get_twilio_service
        twilio_service = get_twilio_service()
        
        return jsonify({
            'success': True,
            'twilio_enabled': twilio_service.is_enabled(),
            'service_info': twilio_service.get_service_info()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error checking mobile OTP status'
        }), 500

@auth_bp.route('/api/mobile-otp/validate-phone', methods=['POST'])
def api_validate_phone():
    """API endpoint to validate phone number format"""
    try:
        data = request.get_json()
        
        if not data or 'phone' not in data:
            return jsonify({
                'success': False,
                'message': 'Phone number is required'
            }), 400
        
        # Validate phone number
        from utils.otp_manager import OTPManager
        is_valid, formatted_phone, error_msg = OTPManager.validate_phone_number(data['phone'])
        
        if is_valid:
            return jsonify({
                'success': True,
                'formatted_phone': formatted_phone,
                'message': 'Valid phone number'
            })
        else:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error validating phone number'
        }), 500

@auth_bp.route('/api/email-otp/status')
def api_email_otp_status():
    """API endpoint to check email OTP status"""
    try:
        # Check if email service is enabled
        from utils.email_service import EmailService
        email_service = EmailService()
        
        is_valid, message = email_service.validate_config()
        
        return jsonify({
            'success': True,
            'email_service_enabled': is_valid,
            'service_info': email_service.get_queue_status() if is_valid else {'error': message}
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error checking email OTP status'
        }), 500

@auth_bp.route('/api/email-otp/validate-email', methods=['POST'])
def api_validate_email():
    """API endpoint to validate email address format"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'message': 'Email address is required'
            }), 400
        
        # Validate email address
        from utils.email_service import EmailService
        email_service = EmailService()
        
        if email_service.validate_email_address(data['email']):
            return jsonify({
                'success': True,
                'message': 'Valid email address'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid email address format'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error validating email address'
        }), 500
