from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User
from utils.permissions import (
    require_permission, Permissions, require_admin, require_super_admin, 
    require_admin_only_user_management, check_user_management_permission
)
from datetime import datetime
import logging

users_bp = Blueprint('users', __name__)

# Configure logging
logger = logging.getLogger(__name__)

# Rate limiting for sensitive operations
rate_limits = {}

def check_rate_limit(identifier, max_requests, window_seconds):
    """Simple rate limiting function"""
    from time import time
    
    now = time()
    window_start = now - window_seconds
    
    if identifier not in rate_limits:
        rate_limits[identifier] = []
    
    # Remove old requests outside the window
    rate_limits[identifier] = [req_time for req_time in rate_limits[identifier] if req_time > window_start]
    
    # Check if limit exceeded
    if len(rate_limits[identifier]) >= max_requests:
        return False
    
    # Add current request
    rate_limits[identifier].append(now)
    return True

def cleanup_rate_limits():
    """Clean up old rate limit entries"""
    from time import time
    cutoff = time() - 3600  # 1 hour ago
    for key in list(rate_limits.keys()):
        rate_limits[key] = [req_time for req_time in rate_limits[key] if req_time > cutoff]
        if not rate_limits[key]:
            del rate_limits[key]

@users_bp.route('/')
@require_admin_only_user_management()
def index():
    """Users management page"""
    try:
        # Get users that current admin can manage
        users = User.get_users_for_admin(current_user, include_inactive=True)
        
        # Get role statistics
        role_stats = {}
        for user in users:
            role = user.role
            if role not in role_stats:
                role_stats[role] = {'count': 0, 'active': 0, 'inactive': 0, 'suspended': 0}
            role_stats[role]['count'] += 1
            if user.account_status == 'active':
                role_stats[role]['active'] += 1
            elif user.account_status == 'inactive':
                role_stats[role]['inactive'] += 1
            elif user.account_status == 'suspended':
                role_stats[role]['suspended'] += 1
        
        return render_template('users/index.html', 
                             users=users, 
                             role_stats=role_stats,
                             valid_roles=User.get_valid_roles(),
                             manageable_roles=User.get_admin_manageable_roles(current_user),
                             is_super_admin=current_user.is_super_admin())
    except Exception as e:
        logger.error(f"Error loading users page: {str(e)}")
        flash('Error loading users page', 'error')
        return redirect(url_for('dashboard.index'))

@users_bp.route('/admin')
@require_admin_only_user_management()
def admin_dashboard():
    """Comprehensive admin user management dashboard"""
    try:
        # Get all users that admin can manage
        users = User.get_users_for_admin(current_user, include_inactive=True)
        
        # Get statistics
        total_users = len(users)
        active_users = len([u for u in users if u.account_status == 'active'])
        inactive_users = len([u for u in users if u.account_status == 'inactive'])
        suspended_users = len([u for u in users if u.account_status == 'suspended'])
        locked_accounts = len([u for u in users if u.is_account_locked()])
        
        # Role distribution
        role_distribution = {}
        for user in users:
            role = user.role
            role_distribution[role] = role_distribution.get(role, 0) + 1
        
        # Recent activity (users with recent activity)
        recent_activity = []
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        for user in users:
            if user.last_activity and user.last_activity > cutoff_date:
                recent_activity.append(user)
        
        # Users needing attention (locked, suspended, etc.)
        users_needing_attention = [u for u in users if u.is_account_locked() or u.account_status == 'suspended']
        
        return render_template('users/admin_user_management.html',
                             users=users,
                             total_users=total_users,
                             active_users=active_users,
                             inactive_users=inactive_users,
                             suspended_users=suspended_users,
                             locked_accounts=locked_accounts,
                             role_distribution=role_distribution,
                             recent_activity=recent_activity,
                             users_needing_attention=users_needing_attention,
                             valid_roles=User.get_valid_roles(),
                             manageable_roles=User.get_admin_manageable_roles(current_user),
                             is_super_admin=current_user.is_super_admin())
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}")
        flash('Error loading admin dashboard', 'error')
        return redirect(url_for('dashboard.index'))

@users_bp.route('/admin/create', methods=['GET', 'POST'])
@require_admin_only_user_management()
def create_user():
    """Create new user with admin controls"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No data provided'
                }), 400
            
            # Rate limiting check
            if not check_rate_limit(f'create_user_{current_user.id}', 5, 300):  # 5 users per 5 minutes
                return jsonify({
                    'success': False,
                    'message': 'Rate limit exceeded. Try again later.'
                }), 429
            
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
            
            # Check if role is manageable by current admin
            if role not in User.get_admin_manageable_roles(current_user):
                return jsonify({
                    'success': False,
                    'message': 'You cannot assign this role'
                }), 403
            
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
                # Log admin action
                logger.info(f"Admin {current_user.username} created new user: {username} with role: {role}")
                
                # Add admin notes
                user.admin_notes = f"[{datetime.utcnow().isoformat()}] {current_user.username}: User created"
                db.session.commit()
                
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
                         valid_roles=User.get_admin_manageable_roles(current_user),
                         is_super_admin=current_user.is_super_admin())

@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@require_admin_only_user_management()
def edit_user(user_id):
    """Edit existing user"""
    user = User.query.get_or_404(user_id)
    
    # Check if admin can manage this user
    can_manage, message = check_user_management_permission(user, current_user)
    if not can_manage:
        return jsonify({
            'success': False,
            'message': message
        }), 403
    
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
            account_status = data.get('account_status', user.account_status)
            admin_notes = data.get('admin_notes', '')
            
            # Validation
            if role not in User.get_admin_manageable_roles(current_user):
                return jsonify({
                    'success': False,
                    'message': 'You cannot assign this role'
                }), 403
            
            # Check if email already exists (if changed)
            if email != user.email_decrypted:
                existing_user = User.query.filter_by(email=User._encrypt_email(email)).first()
                if existing_user and existing_user.id != user.id:
                    return jsonify({
                        'success': False,
                        'message': 'Email already exists'
                    }), 400
            
            # Update user with proper tracking
            success, message = user.change_role(role, admin_notes, current_user)
            if not success:
                return jsonify({
                    'success': False,
                    'message': message
                }), 400
            
            user.email = user._encrypt_email(email) if email else None
            
            if account_status != user.account_status:
                success, message = user.change_account_status(account_status, admin_notes, current_user)
                if not success:
                    return jsonify({
                        'success': False,
                        'message': message
                    }), 400
            
            logger.info(f"Admin {current_user.username} edited user: {user.username}")
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
                         valid_roles=User.get_admin_manageable_roles(current_user),
                         is_super_admin=current_user.is_super_admin())

@users_bp.route('/<int:user_id>/activate', methods=['POST'])
@require_admin_only_user_management()
def activate_user(user_id):
    """Activate user account"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        data = request.get_json() or {}
        admin_notes = data.get('admin_notes', '')
        
        success, message = user.activate(admin_notes, current_user)
        
        if success:
            logger.info(f"Admin {current_user.username} activated user: {user.username}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error activating user: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error activating user'
        }), 500

@users_bp.route('/<int:user_id>/deactivate', methods=['POST'])
@require_admin_only_user_management()
def deactivate_user(user_id):
    """Deactivate user account"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        data = request.get_json() or {}
        admin_notes = data.get('admin_notes', '')
        
        success, message = user.deactivate(admin_notes, current_user)
        
        if success:
            logger.warning(f"Admin {current_user.username} deactivated user: {user.username}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error deactivating user: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error deactivating user'
        }), 500

@users_bp.route('/<int:user_id>/suspend', methods=['POST'])
@require_admin_only_user_management()
def suspend_user(user_id):
    """Suspend user account"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        data = request.get_json() or {}
        admin_notes = data.get('admin_notes', '')
        
        success, message = user.suspend(admin_notes, current_user)
        
        if success:
            logger.warning(f"Admin {current_user.username} suspended user: {user.username}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error suspending user: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error suspending user'
        }), 500

@users_bp.route('/<int:user_id>/toggle_status', methods=['POST'])
@require_admin_only_user_management()
def toggle_user_status(user_id):
    """Toggle user account status"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        data = request.get_json() or {}
        admin_notes = data.get('admin_notes', '')
        
        success, message = user.toggle_status(admin_notes, current_user)
        
        if success:
            logger.info(f"Admin {current_user.username} toggled status for user: {user.username}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error toggling user status: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error toggling user status'
        }), 500

@users_bp.route('/<int:user_id>/change_role', methods=['POST'])
@require_admin_only_user_management()
def change_user_role(user_id):
    """Change user role"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        new_role = data.get('role', '')
        admin_notes = data.get('admin_notes', '')
        
        if new_role not in User.get_admin_manageable_roles(current_user):
            return jsonify({
                'success': False,
                'message': 'You cannot assign this role'
            }), 403
        
        success, message = user.change_role(new_role, admin_notes, current_user)
        
        if success:
            logger.info(f"Admin {current_user.username} changed role for user: {user.username} from {user.role} to {new_role}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error changing user role: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error changing user role'
        }), 500

@users_bp.route('/<int:user_id>/unlock', methods=['POST'])
@require_admin_only_user_management()
def unlock_user_account(user_id):
    """Unlock user account"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        if not user.is_account_locked():
            return jsonify({
                'success': False,
                'message': 'Account is not locked'
            }), 400
        
        success, message = user.unlock_account(current_user)
        
        if success:
            logger.info(f"Admin {current_user.username} unlocked account for user: {user.username}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error unlocking user account: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error unlocking user account'
        }), 500

@users_bp.route('/<int:user_id>/force_password_change', methods=['POST'])
@require_admin_only_user_management()
def force_password_change(user_id):
    """Force user to change password"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        success, message = user.force_password_change(current_user)
        
        if success:
            logger.info(f"Admin {current_user.username} forced password change for user: {user.username}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error forcing password change: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error forcing password change'
        }), 500

@users_bp.route('/<int:user_id>/details', methods=['GET'])
@require_admin_only_user_management()
def user_details(user_id):
    """Get detailed user information"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        return jsonify({
            'success': True,
            'user': user.get_admin_summary()
        })
        
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error retrieving user details'
        }), 500

@users_bp.route('/bulk_action', methods=['POST'])
@require_admin_only_user_management()
def bulk_user_action():
    """Bulk user operations"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        user_ids = data.get('user_ids', [])
        action = data.get('action', '')
        admin_notes = data.get('admin_notes', '')
        
        if not user_ids or not action:
            return jsonify({
                'success': False,
                'message': 'User IDs and action are required'
            }), 400
        
        # Rate limiting for bulk operations
        if not check_rate_limit(f'bulk_action_{current_user.id}', 3, 300):  # 3 bulk actions per 5 minutes
            return jsonify({
                'success': False,
                'message': 'Rate limit exceeded. Try again later.'
            }), 429
        
        valid_actions = ['activate', 'deactivate', 'suspend', 'change_role', 'unlock_accounts']
        if action not in valid_actions:
            return jsonify({
                'success': False,
                'message': f'Invalid action. Must be one of: {valid_actions}'
            }), 400
        
        results = []
        success_count = 0
        errors = []
        
        for user_id in user_ids:
            try:
                user = User.query.get(user_id)
                if not user:
                    errors.append(f"User ID {user_id} not found")
                    continue
                
                # Check if admin can manage this user
                can_manage, message = check_user_management_permission(user, current_user)
                if not can_manage:
                    errors.append(f"Cannot manage user {user.username}: {message}")
                    continue
                
                if action == 'activate':
                    success, message = user.activate(admin_notes, current_user)
                elif action == 'deactivate':
                    success, message = user.deactivate(admin_notes, current_user)
                elif action == 'suspend':
                    success, message = user.suspend(admin_notes, current_user)
                elif action == 'unlock_accounts':
                    if user.is_account_locked():
                        success, message = user.unlock_account(current_user)
                    else:
                        success, message = True, "Account already unlocked"
                elif action == 'change_role':
                    new_role = data.get('new_role', '')
                    if new_role not in User.get_admin_manageable_roles(current_user):
                        errors.append(f"Cannot assign role {new_role} to {user.username}")
                        continue
                    success, message = user.change_role(new_role, admin_notes, current_user)
                
                if success:
                    success_count += 1
                    results.append({
                        'user_id': user_id,
                        'username': user.username,
                        'status': 'success',
                        'message': message
                    })
                else:
                    results.append({
                        'user_id': user_id,
                        'username': user.username,
                        'status': 'error',
                        'message': message
                    })
                    
            except Exception as e:
                errors.append(f"User ID {user_id}: {str(e)}")
                results.append({
                    'user_id': user_id,
                    'status': 'error',
                    'message': str(e)
                })
        
        logger.info(f"Admin {current_user.username} performed bulk action '{action}' on {success_count} users")
        
        return jsonify({
            'success': True,
            'message': f'Bulk action completed. {success_count} users processed.',
            'results': results,
            'errors': errors,
            'success_count': success_count
        })
        
    except Exception as e:
        logger.error(f"Error performing bulk action: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error performing bulk action'
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

@users_bp.route('/api/admin/users')
@require_admin_only_user_management()
def get_users_api():
    """Get users via API with filtering and search"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)  # Max 100 per page
        search = request.args.get('search', '').strip()
        role = request.args.get('role', '')
        status = request.args.get('status', '')
        include_inactive = request.args.get('include_inactive', 'true').lower() == 'true'
        
        # Start with users that admin can manage
        users = User.get_users_for_admin(current_user, include_inactive=include_inactive)
        
        # Apply filters
        if search:
            search_users = User.search_users(search, current_user, include_inactive)
            users = [u for u in users if u.id in [su.id for su in search_users]]
        
        if role:
            users = [u for u in users if u.role == role]
        
        if status:
            users = [u for u in users if u.account_status == status]
        
        # Pagination
        total = len(users)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_users = users[start:end]
        
        # Convert to JSON
        user_list = []
        for user in paginated_users:
            user_data = user.get_admin_summary()
            user_data['can_be_managed'] = user.can_be_managed_by(current_user)[0]
            user_list.append(user_data)
        
        return jsonify({
            'success': True,
            'users': user_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting users via API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error retrieving users'
        }), 500

@users_bp.route('/api/admin/users/search')
@require_admin_only_user_management()
def search_users_api():
    """Search users via API"""
    try:
        search_term = request.args.get('q', '').strip()
        include_inactive = request.args.get('include_inactive', 'true').lower() == 'true'
        
        if not search_term:
            return jsonify({
                'success': True,
                'users': []
            })
        
        users = User.search_users(search_term, current_user, include_inactive)
        
        user_list = []
        for user in users:
            user_data = user.get_admin_summary()
            user_data['can_be_managed'] = user.can_be_managed_by(current_user)[0]
            user_list.append(user_data)
        
        return jsonify({
            'success': True,
            'users': user_list
        })
        
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error searching users'
        }), 500

@users_bp.route('/api/admin/users/<int:user_id>')
@require_admin_only_user_management()
def get_user_api(user_id):
    """Get specific user via API"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        user_data = user.get_admin_summary()
        user_data['can_be_managed'] = can_manage
        
        return jsonify({
            'success': True,
            'user': user_data
        })
        
    except Exception as e:
        logger.error(f"Error getting user via API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error retrieving user'
        }), 500

@users_bp.route('/api/admin/roles')
@require_admin_only_user_management()
def get_roles_api():
    """Get available roles via API based on admin level"""
    try:
        roles = []
        manageable_roles = User.get_admin_manageable_roles(current_user)
        
        for role in manageable_roles:
            roles.append({
                'value': role,
                'label': User.get_role_display_name(role),
                'level': User.ROLE_HIERARCHY.index(role),
                'assignable': True
            })
        
        return jsonify({
            'success': True,
            'roles': roles,
            'is_super_admin': current_user.is_super_admin()
        })
        
    except Exception as e:
        logger.error(f"Error getting roles via API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error retrieving roles'
        }), 500

@users_bp.route('/api/admin/users/<int:user_id>/activity')
@require_admin_only_user_management()
def get_user_activity(user_id):
    """Get user activity information"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if admin can manage this user
        can_manage, message = check_user_management_permission(user, current_user)
        if not can_manage:
            return jsonify({
                'success': False,
                'message': message
            }), 403
        
        activity_info = {
            'last_activity': user.last_activity.isoformat() if user.last_activity else None,
            'activity_count': user.activity_count,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'failed_login_attempts': user.failed_login_attempts,
            'is_account_locked': user.is_account_locked(),
            'locked_until': user.locked_until.isoformat() if user.locked_until else None,
            'must_change_password': user.must_change_password,
            'password_expiry_date': user.password_expiry_date.isoformat() if user.password_expiry_date else None
        }
        
        return jsonify({
            'success': True,
            'activity': activity_info
        })
        
    except Exception as e:
        logger.error(f"Error getting user activity: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error retrieving user activity'
        }), 500

@users_bp.route('/api/admin/stats')
@require_admin_only_user_management()
def get_admin_stats():
    """Get admin statistics dashboard"""
    try:
        users = User.get_users_for_admin(current_user, include_inactive=True)
        
        # Basic statistics
        total_users = len(users)
        active_users = len([u for u in users if u.account_status == 'active'])
        inactive_users = len([u for u in users if u.account_status == 'inactive'])
        suspended_users = len([u for u in users if u.account_status == 'suspended'])
        locked_accounts = len([u for u in users if u.is_account_locked()])
        
        # Role distribution
        role_distribution = {}
        for user in users:
            role = user.role
            role_distribution[role] = role_distribution.get(role, 0) + 1
        
        # Recent activity (last 7 days)
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        recent_activity = len([u for u in users if u.last_activity and u.last_activity > cutoff_date])
        
        # Users needing attention
        needing_attention = len([u for u in users if u.is_account_locked() or u.account_status == 'suspended'])
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'suspended_users': suspended_users,
            'locked_accounts': locked_accounts,
            'role_distribution': role_distribution,
            'recent_activity': recent_activity,
            'users_needing_attention': needing_attention,
            'last_updated': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error retrieving admin statistics'
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
