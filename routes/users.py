from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User
from utils.permissions import require_permission, Permissions, require_admin
from datetime import datetime
import logging

users_bp = Blueprint('users', __name__)

# Configure logging
logger = logging.getLogger(__name__)

@users_bp.route('/')
@require_admin()
def index():
    """Users management page"""
    try:
        # Get all users with their information
        users = User.query.all()
        
        # Get role statistics
        role_stats = {}
        for user in users:
            role = user.role
            if role not in role_stats:
                role_stats[role] = {'count': 0, 'active': 0}
            role_stats[role]['count'] += 1
            if user.is_active:
                role_stats[role]['active'] += 1
        
        return render_template('users/index.html', 
                             users=users, 
                             role_stats=role_stats,
                             valid_roles=User.get_valid_roles())
    except Exception as e:
        logger.error(f"Error loading users page: {str(e)}")
        flash('Error loading users page', 'error')
        return redirect(url_for('dashboard.index'))

@users_bp.route('/create', methods=['GET', 'POST'])
@require_admin()
def create_user():
    """Create new user"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No data provided'
                }), 400
            
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '')
            role = data.get('role', 'cashier')
            
            # Validation
            if not username or not password:
                return jsonify({
                    'success': False,
                    'message': 'Username and password are required'
                }), 400
            
            if role not in User.get_valid_roles():
                return jsonify({
                    'success': False,
                    'message': 'Invalid role selected'
                }), 400
            
            # Check if username already exists
            if User.query.filter_by(username=username).first():
                return jsonify({
                    'success': False,
                    'message': 'Username already exists'
                }), 400
            
            # Check if email already exists (if provided)
            if email and User.query.filter_by(email=User._encrypt_email(email)).first():
                return jsonify({
                    'success': False,
                    'message': 'Email already exists'
                }), 400
            
            # Create user
            user = User.create_user(username, password, role, email)
            
            if user:
                logger.info(f"User {current_user.username} created new user: {username}")
                return jsonify({
                    'success': True,
                    'message': 'User created successfully',
                    'user_id': user.id
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create user'
                }), 500
                
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error creating user'
            }), 500
    
    # GET request - return form
    return render_template('users/create.html', 
                         valid_roles=User.get_valid_roles())

@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@require_admin()
def edit_user(user_id):
    """Edit existing user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No data provided'
                }), 400
            
            email = data.get('email', '').strip()
            role = data.get('role', user.role)
            is_active = data.get('is_active', user.is_active)
            
            # Validation
            if role not in User.get_valid_roles():
                return jsonify({
                    'success': False,
                    'message': 'Invalid role selected'
                }), 400
            
            # Check if email already exists (if changed)
            if email != user.email_decrypted:
                existing_user = User.query.filter_by(email=User._encrypt_email(email)).first()
                if existing_user and existing_user.id != user.id:
                    return jsonify({
                        'success': False,
                        'message': 'Email already exists'
                    }), 400
            
            # Update user
            user.email = user._encrypt_email(email) if email else None
            user.role = role
            user.is_active = is_active
            db.session.commit()
            
            logger.info(f"User {current_user.username} edited user: {user.username}")
            return jsonify({
                'success': True,
                'message': 'User updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error updating user'
            }), 500
    
    # GET request - return form
    return render_template('users/edit.html', 
                         user=user,
                         valid_roles=User.get_valid_roles())

@users_bp.route('/<int:user_id>/delete', methods=['POST'])
@require_admin()
def delete_user(user_id):
    """Delete user (soft delete - deactivate)"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting yourself
        if user.id == current_user.id:
            return jsonify({
                'success': False,
                'message': 'You cannot delete your own account'
            }), 400
        
        # Soft delete - deactivate user
        user.is_active = False
        user.role = 'readonly'  # Move to read-only role
        db.session.commit()
        
        logger.warning(f"User {current_user.username} deactivated user: {user.username}")
        return jsonify({
            'success': True,
            'message': 'User deactivated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deactivating user: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error deactivating user'
        }), 500

@users_bp.route('/<int:user_id>/activate', methods=['POST'])
@require_admin()
def activate_user(user_id):
    """Activate user"""
    try:
        user = User.query.get_or_404(user_id)
        
        user.is_active = True
        if user.role == 'readonly':
            user.role = 'cashier'  # Reset to default role
        db.session.commit()
        
        logger.info(f"User {current_user.username} activated user: {user.username}")
        return jsonify({
            'success': True,
            'message': 'User activated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error activating user: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error activating user'
        }), 500

@users_bp.route('/<int:user_id>/reset_password', methods=['POST'])
@require_admin()
def reset_password(user_id):
    """Reset user password"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        new_password = data.get('password', '')
        
        if not new_password or len(new_password) < 6:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters long'
            }), 400
        
        user.set_password(new_password)
        db.session.commit()
        
        logger.info(f"User {current_user.username} reset password for user: {user.username}")
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        })
        
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error resetting password'
        }), 500

@users_bp.route('/api/users')
@require_admin()
def get_users_api():
    """Get users via API"""
    try:
        users = User.query.all()
        
        user_list = []
        for user in users:
            user_data = user.to_dict()
            user_data['role_display_name'] = User.get_role_display_name(user.role)
            user_list.append(user_data)
        
        return jsonify({
            'success': True,
            'users': user_list,
            'total': len(user_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting users via API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error retrieving users'
        }), 500

@users_bp.route('/api/users/<int:user_id>')
@require_admin()
def get_user_api(user_id):
    """Get specific user via API"""
    try:
        user = User.query.get_or_404(user_id)
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting user via API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error retrieving user'
        }), 500

@users_bp.route('/api/roles')
@require_admin()
def get_roles_api():
    """Get available roles via API"""
    try:
        roles = []
        for role in User.get_valid_roles():
            roles.append({
                'value': role,
                'label': User.get_role_display_name(role),
                'level': User.ROLE_HIERARCHY.index(role)
            })
        
        return jsonify({
            'success': True,
            'roles': roles
        })
        
    except Exception as e:
        logger.error(f"Error getting roles via API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error retrieving roles'
        }), 500

@users_bp.route('/api/validate_username', methods=['POST'])
@require_admin()
def validate_username():
    """Validate username availability"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({
                'valid': False,
                'message': 'Username is required'
            }), 400
        
        existing_user = User.query.filter_by(username=username).first()
        
        return jsonify({
            'valid': existing_user is None,
            'available': existing_user is None,
            'message': 'Username is available' if existing_user is None else 'Username already exists'
        })
        
    except Exception as e:
        logger.error(f"Error validating username: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Error validating username'
        }), 500

@users_bp.route('/api/validate_email', methods=['POST'])
@require_admin()
def validate_email():
    """Validate email availability"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        user_id = data.get('user_id')
        
        if not email:
            return jsonify({
                'valid': False,
                'message': 'Email is required'
            }), 400
        
        query = User.query.filter_by(email=User._encrypt_email(email))
        if user_id:
            query = query.filter(User.id != user_id)
        
        existing_user = query.first()
        
        return jsonify({
            'valid': existing_user is None,
            'available': existing_user is None,
            'message': 'Email is available' if existing_user is None else 'Email already exists'
        })
        
    except Exception as e:
        logger.error(f"Error validating email: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Error validating email'
        }), 500
