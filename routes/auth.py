from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from forms import LoginForm
from datetime import datetime

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
    """User profile page"""
    try:
        return render_template('auth/profile.html')
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

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate input
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('auth/change_password.html')
        
        # Check current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return render_template('auth/change_password.html')
        
        # Check new password confirmation
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('auth/change_password.html')
        
        # Check password length
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('auth/change_password.html')
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password changed successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html')

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

@auth_bp.route('/api/keep_alive')
@login_required
def keep_alive():
    """Keep session alive (for AJAX)"""
    return jsonify({'status': 'alive', 'timestamp': datetime.utcnow().isoformat()})
