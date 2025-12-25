"""
Permission-based Access Control System for Restaurant POS
Provides decorators and utilities for role-based access control
"""

from functools import wraps
from flask import abort, current_app, flash, redirect, url_for, request, jsonify
from flask_login import current_user
import logging

# Configure logging
logger = logging.getLogger(__name__)

class PermissionError(Exception):
    """Custom exception for permission-related errors"""
    pass

class InsufficientPermissionsError(PermissionError):
    """Raised when user doesn't have required permissions"""
    pass

# Permission constants for better maintainability
class Permissions:
    """Permission constants"""
    # User management
    MANAGE_USERS = 'manage_users'
    VIEW_USERS = 'view_users'
    CREATE_USERS = 'create_users'
    EDIT_USERS = 'edit_users'
    DELETE_USERS = 'delete_users'
    
    # Settings management
    MANAGE_SETTINGS = 'manage_settings'
    VIEW_SETTINGS = 'view_settings'
    EDIT_SETTINGS = 'edit_settings'
    
    # Order management
    MANAGE_ORDERS = 'manage_orders'
    VIEW_ORDERS = 'view_orders'
    CREATE_ORDERS = 'create_orders'
    EDIT_ORDERS = 'edit_orders'
    DELETE_ORDERS = 'delete_orders'
    PROCESS_PAYMENTS = 'process_payments'
    
    # Menu management
    MANAGE_MENU = 'manage_menu'
    VIEW_MENU = 'view_menu'
    EDIT_MENU = 'edit_menu'
    CREATE_MENU_ITEMS = 'create_menu_items'
    DELETE_MENU_ITEMS = 'delete_menu_items'
    
    # Inventory management
    MANAGE_INVENTORY = 'manage_inventory'
    VIEW_INVENTORY = 'view_inventory'
    EDIT_INVENTORY = 'edit_inventory'
    MANAGE_STOCK = 'manage_stock'
    
    # Reports
    VIEW_REPORTS = 'view_reports'
    EXPORT_REPORTS = 'export_reports'
    MANAGE_REPORTS = 'manage_reports'
    
    # Kitchen operations
    MANAGE_KOT = 'manage_kot'
    VIEW_KOT = 'view_kot'
    UPDATE_KOT = 'update_kot'
    
    # Table management
    MANAGE_TABLES = 'manage_tables'
    VIEW_TABLES = 'view_tables'
    EDIT_TABLE_STATUS = 'edit_table_status'
    
    # System administration
    SYSTEM_ADMIN = 'system_admin'
    VIEW_AUDIT_LOGS = 'view_audit_logs'
    MANAGE_BACKUP = 'manage_backup'
    
    # Email management
    MANAGE_EMAIL = 'manage_email'
    SEND_EMAIL = 'send_email'

# Role-based permission mapping
ROLE_PERMISSIONS = {
    # Super Admin - All permissions
    'super_admin': '*',
    
    # Admin - All administrative functions
    'admin': [
        Permissions.MANAGE_USERS,
        Permissions.VIEW_USERS,
        Permissions.CREATE_USERS,
        Permissions.EDIT_USERS,
        Permissions.DELETE_USERS,
        Permissions.MANAGE_SETTINGS,
        Permissions.VIEW_SETTINGS,
        Permissions.EDIT_SETTINGS,
        Permissions.MANAGE_ORDERS,
        Permissions.VIEW_ORDERS,
        Permissions.CREATE_ORDERS,
        Permissions.EDIT_ORDERS,
        Permissions.DELETE_ORDERS,
        Permissions.PROCESS_PAYMENTS,
        Permissions.MANAGE_MENU,
        Permissions.VIEW_MENU,
        Permissions.EDIT_MENU,
        Permissions.CREATE_MENU_ITEMS,
        Permissions.DELETE_MENU_ITEMS,
        Permissions.MANAGE_INVENTORY,
        Permissions.VIEW_INVENTORY,
        Permissions.EDIT_INVENTORY,
        Permissions.MANAGE_STOCK,
        Permissions.VIEW_REPORTS,
        Permissions.EXPORT_REPORTS,
        Permissions.MANAGE_REPORTS,
        Permissions.MANAGE_KOT,
        Permissions.VIEW_KOT,
        Permissions.UPDATE_KOT,
        Permissions.MANAGE_TABLES,
        Permissions.VIEW_TABLES,
        Permissions.EDIT_TABLE_STATUS,
        Permissions.VIEW_AUDIT_LOGS,
        Permissions.MANAGE_BACKUP,
        Permissions.MANAGE_EMAIL,
        Permissions.SEND_EMAIL,
    ],
    
    # Manager - Business operations and reports
    'manager': [
        Permissions.MANAGE_ORDERS,
        Permissions.VIEW_ORDERS,
        Permissions.CREATE_ORDERS,
        Permissions.EDIT_ORDERS,
        Permissions.PROCESS_PAYMENTS,
        Permissions.MANAGE_MENU,
        Permissions.VIEW_MENU,
        Permissions.EDIT_MENU,
        Permissions.CREATE_MENU_ITEMS,
        Permissions.MANAGE_INVENTORY,
        Permissions.VIEW_INVENTORY,
        Permissions.EDIT_INVENTORY,
        Permissions.MANAGE_STOCK,
        Permissions.VIEW_REPORTS,
        Permissions.EXPORT_REPORTS,
        Permissions.MANAGE_KOT,
        Permissions.VIEW_KOT,
        Permissions.UPDATE_KOT,
        Permissions.MANAGE_TABLES,
        Permissions.VIEW_TABLES,
        Permissions.EDIT_TABLE_STATUS,
        Permissions.SEND_EMAIL,
    ],
    
    # Head Chef - Kitchen and menu management
    'head_chef': [
        Permissions.VIEW_ORDERS,
        Permissions.CREATE_ORDERS,
        Permissions.MANAGE_MENU,
        Permissions.VIEW_MENU,
        Permissions.EDIT_MENU,
        Permissions.CREATE_MENU_ITEMS,
        Permissions.DELETE_MENU_ITEMS,
        Permissions.MANAGE_INVENTORY,
        Permissions.VIEW_INVENTORY,
        Permissions.EDIT_INVENTORY,
        Permissions.MANAGE_STOCK,
        Permissions.MANAGE_KOT,
        Permissions.VIEW_KOT,
        Permissions.UPDATE_KOT,
        Permissions.VIEW_TABLES,
        Permissions.EDIT_TABLE_STATUS,
    ],
    
    # Chef - Kitchen operations
    'chef': [
        Permissions.VIEW_ORDERS,
        Permissions.CREATE_ORDERS,
        Permissions.VIEW_MENU,
        Permissions.EDIT_MENU,
        Permissions.VIEW_INVENTORY,
        Permissions.MANAGE_STOCK,
        Permissions.MANAGE_KOT,
        Permissions.VIEW_KOT,
        Permissions.UPDATE_KOT,
        Permissions.VIEW_TABLES,
    ],
    
    # Cashier - Order and payment processing
    'cashier': [
        Permissions.MANAGE_ORDERS,
        Permissions.VIEW_ORDERS,
        Permissions.CREATE_ORDERS,
        Permissions.EDIT_ORDERS,
        Permissions.PROCESS_PAYMENTS,
        Permissions.VIEW_MENU,
        Permissions.VIEW_TABLES,
        Permissions.EDIT_TABLE_STATUS,
    ],
    
    # Waiter - Order and table operations
    'waiter': [
        Permissions.MANAGE_ORDERS,
        Permissions.VIEW_ORDERS,
        Permissions.CREATE_ORDERS,
        Permissions.EDIT_ORDERS,
        Permissions.VIEW_MENU,
        Permissions.VIEW_TABLES,
        Permissions.EDIT_TABLE_STATUS,
    ],
    
    # Kitchen Staff - Limited kitchen operations
    'kitchen_staff': [
        Permissions.VIEW_ORDERS,
        Permissions.CREATE_ORDERS,
        Permissions.VIEW_MENU,
        Permissions.VIEW_INVENTORY,
        Permissions.MANAGE_STOCK,
        Permissions.MANAGE_KOT,
        Permissions.VIEW_KOT,
        Permissions.UPDATE_KOT,
    ],
    
    # Read-only - View only access
    'readonly': [
        Permissions.VIEW_ORDERS,
        Permissions.VIEW_MENU,
        Permissions.VIEW_INVENTORY,
        Permissions.VIEW_REPORTS,
        Permissions.VIEW_KOT,
        Permissions.VIEW_TABLES,
    ]
}

def has_permission(permission):
    """Check if current user has specific permission"""
    if not current_user or not current_user.is_authenticated:
        return False
    
    # Super admin has all permissions
    if current_user.role == 'super_admin':
        return True
    
    # Get role permissions
    role_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
    
    # Super admin permission (all permissions)
    if '*' in role_permissions:
        return True
    
    # Check specific permission
    return permission in role_permissions

def has_any_permission(permissions):
    """Check if current user has any of the specified permissions"""
    return any(has_permission(permission) for permission in permissions)

def has_all_permissions(permissions):
    """Check if current user has all of the specified permissions"""
    return all(has_permission(permission) for permission in permissions)

def require_permission(permission, message=None):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip permission check if we're outside request context (e.g., during module import)
            try:
                if not current_user or not current_user.is_authenticated:
                    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                        return jsonify({'error': 'Authentication required'}), 401
                    flash('Please log in to access this page.', 'warning')
                    return redirect(url_for('auth.login'))
            except RuntimeError:
                # We're outside request context, skip permission check
                pass
            
            # Check permission if we have a current user
            if not has_permission(permission):
                try:
                    logger.warning(f"User {current_user.username} attempted to access {request.endpoint} without permission: {permission}")
                    
                    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                        return jsonify({
                            'error': 'Insufficient permissions',
                            'message': message or f'Required permission: {permission}'
                        }), 403
                    
                    flash(message or 'You do not have permission to access this page.', 'error')
                    return redirect(url_for('dashboard.index'))
                except RuntimeError:
                    # We're outside request context
                    abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_any_permission(permissions, message=None):
    """Decorator to require any of the specified permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip permission check if we're outside request context
            try:
                if not current_user or not current_user.is_authenticated:
                    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                        return jsonify({'error': 'Authentication required'}), 401
                    flash('Please log in to access this page.', 'warning')
                    return redirect(url_for('auth.login'))
            except RuntimeError:
                # We're outside request context, skip permission check
                pass
            
            # Check permissions if we have a current user
            if not has_any_permission(permissions):
                try:
                    logger.warning(f"User {current_user.username} attempted to access {request.endpoint} without any of permissions: {permissions}")
                    
                    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                        return jsonify({
                            'error': 'Insufficient permissions',
                            'message': message or f'Required permissions: {permissions}'
                        }), 403
                    
                    flash(message or 'You do not have permission to access this page.', 'error')
                    return redirect(url_for('dashboard.index'))
                except RuntimeError:
                    abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_all_permissions(permissions, message=None):
    """Decorator to require all of the specified permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip permission check if we're outside request context
            try:
                if not current_user or not current_user.is_authenticated:
                    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                        return jsonify({'error': 'Authentication required'}), 401
                    flash('Please log in to access this page.', 'warning')
                    return redirect(url_for('auth.login'))
            except RuntimeError:
                # We're outside request context, skip permission check
                pass
            
            # Check permissions if we have a current user
            if not has_all_permissions(permissions):
                try:
                    logger.warning(f"User {current_user.username} attempted to access {request.endpoint} without all permissions: {permissions}")
                    
                    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                        return jsonify({
                            'error': 'Insufficient permissions',
                            'message': message or f'Required permissions: {permissions}'
                        }), 403
                    
                    flash(message or 'You do not have permission to access this page.', 'error')
                    return redirect(url_for('dashboard.index'))
                except RuntimeError:
                    abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role_or_higher(minimum_role):
    """Decorator to require minimum role or higher privilege"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip permission check if we're outside request context
            try:
                if not current_user or not current_user.is_authenticated:
                    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                        return jsonify({'error': 'Authentication required'}), 401
                    flash('Please log in to access this page.', 'warning')
                    return redirect(url_for('auth.login'))
            except RuntimeError:
                # We're outside request context, skip permission check
                pass
            
            # Check role if we have a current user
            if current_user and not current_user.has_role_or_higher(minimum_role):
                try:
                    logger.warning(f"User {current_user.username} attempted to access {request.endpoint} without minimum role: {minimum_role}")
                    
                    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                        return jsonify({
                            'error': 'Insufficient role level',
                            'message': f'Required role: {minimum_role} or higher'
                        }), 403
                    
                    flash(f'You do not have sufficient privileges to access this page.', 'error')
                    return redirect(url_for('dashboard.index'))
                except RuntimeError:
                    abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin(message=None):
    """Decorator to require admin or super admin role"""
    return require_role_or_higher('admin')(lambda f: f)

def require_manager(message=None):
    """Decorator to require manager or higher role"""
    return require_role_or_higher('manager')(lambda f: f)

def require_chef(message=None):
    """Decorator to require chef or higher role"""
    return require_role_or_higher('chef')(lambda f: f)

def get_user_permissions(user=None):
    """Get all permissions for a user"""
    if user is None:
        user = current_user
    
    if not user or not user.is_authenticated:
        return []
    
    # Super admin has all permissions
    if user.role == 'super_admin':
        return ['*']
    
    return ROLE_PERMISSIONS.get(user.role, [])

def get_permission_display_name(permission):
    """Get human-readable permission name"""
    permission_names = {
        Permissions.MANAGE_USERS: 'Manage Users',
        Permissions.VIEW_USERS: 'View Users',
        Permissions.CREATE_USERS: 'Create Users',
        Permissions.EDIT_USERS: 'Edit Users',
        Permissions.DELETE_USERS: 'Delete Users',
        Permissions.MANAGE_SETTINGS: 'Manage Settings',
        Permissions.VIEW_SETTINGS: 'View Settings',
        Permissions.EDIT_SETTINGS: 'Edit Settings',
        Permissions.MANAGE_ORDERS: 'Manage Orders',
        Permissions.VIEW_ORDERS: 'View Orders',
        Permissions.CREATE_ORDERS: 'Create Orders',
        Permissions.EDIT_ORDERS: 'Edit Orders',
        Permissions.DELETE_ORDERS: 'Delete Orders',
        Permissions.PROCESS_PAYMENTS: 'Process Payments',
        Permissions.MANAGE_MENU: 'Manage Menu',
        Permissions.VIEW_MENU: 'View Menu',
        Permissions.EDIT_MENU: 'Edit Menu',
        Permissions.CREATE_MENU_ITEMS: 'Create Menu Items',
        Permissions.DELETE_MENU_ITEMS: 'Delete Menu Items',
        Permissions.MANAGE_INVENTORY: 'Manage Inventory',
        Permissions.VIEW_INVENTORY: 'View Inventory',
        Permissions.EDIT_INVENTORY: 'Edit Inventory',
        Permissions.MANAGE_STOCK: 'Manage Stock',
        Permissions.VIEW_REPORTS: 'View Reports',
        Permissions.EXPORT_REPORTS: 'Export Reports',
        Permissions.MANAGE_REPORTS: 'Manage Reports',
        Permissions.MANAGE_KOT: 'Manage KOT',
        Permissions.VIEW_KOT: 'View KOT',
        Permissions.UPDATE_KOT: 'Update KOT',
        Permissions.MANAGE_TABLES: 'Manage Tables',
        Permissions.VIEW_TABLES: 'View Tables',
        Permissions.EDIT_TABLE_STATUS: 'Edit Table Status',
        Permissions.VIEW_AUDIT_LOGS: 'View Audit Logs',
        Permissions.MANAGE_BACKUP: 'Manage Backup',
        Permissions.MANAGE_EMAIL: 'Manage Email',
        Permissions.SEND_EMAIL: 'Send Email',
    }
    return permission_names.get(permission, permission.replace('_', ' ').title())

# Context processor to make permissions available in templates
def inject_permissions():
    """Inject permissions utilities into template context"""
    return {
        'has_permission': has_permission,
        'has_any_permission': has_any_permission,
        'has_all_permissions': has_all_permissions,
        'current_user_permissions': get_user_permissions(),
        'get_permission_display_name': get_permission_display_name,
        'Permissions': Permissions
    }