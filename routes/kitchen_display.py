"""
Kitchen Display Routes
Provides access to real-time kitchen display interfaces
"""

from flask import Blueprint, render_template, request, jsonify, session, current_app
from flask_login import login_required, current_user
from utils.websocket_security import get_websocket_security, create_websocket_auth_token
from utils.websocket_performance import get_websocket_performance
import json

kitchen_display_bp = Blueprint('kitchen_display', __name__)

@kitchen_display_bp.route('/')
@login_required
def index():
    """Main kitchen display dashboard"""
    return render_template('kot/display.html')

@kitchen_display_bp.route('/display')
@login_required
def display():
    """Real-time kitchen display interface"""
    return render_template('kot/display.html')

@kitchen_display_bp.route('/mobile')
@login_required
def mobile_display():
    """Mobile-optimized kitchen display"""
    return render_template('kot/mobile_display.html')

@kitchen_display_bp.route('/api/auth-token', methods=['POST'])
@login_required
def get_auth_token():
    """Get WebSocket authentication token for kitchen display"""
    try:
        data = request.get_json() or {}
        
        # Get display configuration
        display_name = data.get('display_name', f"{current_user.username}'s Display")
        station_type = data.get('station_type', 'general')
        kitchen_role = data.get('kitchen_role', current_user.role)
        
        # Validate user has kitchen access
        security = get_websocket_security()
        if not security.has_kitchen_access(current_user.role):
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions for kitchen access'
            }), 403
        
        # Create authentication token
        token = security.generate_auth_token(
            user_id=current_user.id,
            role=current_user.role,
            display_name=display_name,
            station_type=station_type
        )
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Failed to generate authentication token'
            }), 500
        
        return jsonify({
            'success': True,
            'token': token,
            'config': {
                'display_name': display_name,
                'station_type': station_type,
                'kitchen_role': kitchen_role,
                'user_id': current_user.id,
                'username': current_user.username
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating auth token: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate authentication token'
        }), 500

@kitchen_display_bp.route('/api/display-status')
@login_required
def get_display_status():
    """Get current kitchen display system status"""
    try:
        # Get performance metrics
        performance_manager = get_websocket_performance()
        real_time_metrics = performance_manager.get_real_time_metrics()
        performance_report = performance_manager.get_performance_report()
        
        # Get system health
        health_data = {
            'websocket_status': 'connected' if real_time_metrics.get('active_connections', 0) > 0 else 'disconnected',
            'active_displays': real_time_metrics.get('active_connections', 0),
            'system_load': {
                'memory': real_time_metrics.get('memory_usage_percent', 0),
                'cpu': real_time_metrics.get('cpu_usage_percent', 0)
            },
            'events_per_minute': real_time_metrics.get('events_per_minute', 0),
            'recent_errors': real_time_metrics.get('recent_errors', 0),
            'system_status': real_time_metrics.get('system_status', 'unknown')
        }
        
        return jsonify({
            'success': True,
            'status': health_data,
            'performance': performance_report,
            'timestamp': real_time_metrics.get('timestamp')
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting display status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get display status'
        }), 500

@kitchen_display_bp.route('/api/optimization-recommendations')
@login_required
def get_optimization_recommendations():
    """Get performance optimization recommendations"""
    try:
        # Only allow admin and manager roles
        if current_user.role not in ['admin', 'manager']:
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions'
            }), 403
        
        performance_manager = get_websocket_performance()
        recommendations = performance_manager.get_optimization_recommendations()
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'timestamp': current_app.config.get('SERVER_START_TIME')
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting optimization recommendations: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get recommendations'
        }), 500

@kitchen_display_bp.route('/api/connection-stats/<connection_id>')
@login_required
def get_connection_stats(connection_id):
    """Get statistics for specific WebSocket connection"""
    try:
        # Only allow admin and manager roles
        if current_user.role not in ['admin', 'manager']:
            return jsonify({
                'success': False,
                'error': 'Insufficient permissions'
            }), 403
        
        performance_manager = get_websocket_performance()
        stats = performance_manager.get_connection_stats(connection_id)
        
        if not stats:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting connection stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get connection stats'
        }), 500

@kitchen_display_bp.route('/api/validate-display-config', methods=['POST'])
@login_required
def validate_display_config():
    """Validate kitchen display configuration"""
    try:
        data = request.get_json() or {}
        display_name = data.get('display_name')
        station_type = data.get('station_type', 'general')
        
        if not display_name:
            return jsonify({
                'success': False,
                'error': 'Display name is required'
            }), 400
        
        # Validate using security manager
        security = get_websocket_security()
        is_valid = security.validate_display_config(
            user_role=current_user.role,
            display_name=display_name,
            station_type=station_type
        )
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'message': 'Configuration is valid' if is_valid else 'Configuration validation failed'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error validating display config: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Validation failed'
        }), 500

@kitchen_display_bp.route('/settings')
@login_required
def display_settings():
    """Kitchen display settings page"""
    return render_template('kot/settings.html')

@kitchen_display_bp.route('/api/save-settings', methods=['POST'])
@login_required
def save_display_settings():
    """Save kitchen display settings"""
    try:
        data = request.get_json() or {}
        
        # Save settings to session or database
        display_settings = {
            'auto_refresh': data.get('auto_refresh', True),
            'sound_enabled': data.get('sound_enabled', True),
            'refresh_interval': data.get('refresh_interval', 30),
            'display_name': data.get('display_name', f"{current_user.username}'s Display"),
            'station_type': data.get('station_type', 'general'),
            'urgency_filter': data.get('urgency_filter', 'all'),
            'status_filter': data.get('status_filter', 'all')
        }
        
        # Store in user session
        session['kitchen_display_settings'] = display_settings
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully',
            'settings': display_settings
        })
        
    except Exception as e:
        current_app.logger.error(f"Error saving display settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to save settings'
        }), 500

@kitchen_display_bp.route('/api/load-settings')
@login_required
def load_display_settings():
    """Load kitchen display settings"""
    try:
        # Load from session
        settings = session.get('kitchen_display_settings', {})
        
        # Set defaults if not found
        default_settings = {
            'auto_refresh': True,
            'sound_enabled': True,
            'refresh_interval': 30,
            'display_name': f"{current_user.username}'s Display",
            'station_type': 'general',
            'urgency_filter': 'all',
            'status_filter': 'all'
        }
        
        # Merge with defaults
        final_settings = {**default_settings, **settings}
        
        return jsonify({
            'success': True,
            'settings': final_settings
        })
        
    except Exception as e:
        current_app.logger.error(f"Error loading display settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load settings'
        }), 500

@kitchen_display_bp.route('/api/health-check')
@login_required
def health_check():
    """Health check endpoint for kitchen display system"""
    try:
        # Basic system health check
        health_status = {
            'status': 'healthy',
            'timestamp': current_app.config.get('SERVER_START_TIME'),
            'services': {
                'database': 'healthy',
                'websocket': 'healthy',
                'authentication': 'healthy'
            },
            'checks': {}
        }
        
        # Database check
        try:
            from models import db
            with current_app.app_context():
                db.engine.execute('SELECT 1')
            health_status['checks']['database'] = 'pass'
        except Exception as e:
            health_status['services']['database'] = 'unhealthy'
            health_status['checks']['database'] = f'fail: {str(e)}'
            health_status['status'] = 'degraded'
        
        # WebSocket check
        try:
            performance_manager = get_websocket_performance()
            metrics = performance_manager.get_real_time_metrics()
            health_status['checks']['websocket'] = 'pass'
            health_status['services']['websocket_connections'] = metrics.get('active_connections', 0)
        except Exception as e:
            health_status['services']['websocket'] = 'unhealthy'
            health_status['checks']['websocket'] = f'fail: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Authentication check
        try:
            security = get_websocket_security()
            # Simple token generation test
            test_token = security.generate_auth_token(1, 'test', 'test', 'general')
            health_status['checks']['authentication'] = 'pass' if test_token else 'fail'
        except Exception as e:
            health_status['services']['authentication'] = 'unhealthy'
            health_status['checks']['authentication'] = f'fail: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Determine HTTP status code
        status_code = 200
        if health_status['status'] == 'degraded':
            status_code = 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        current_app.logger.error(f"Error in health check: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': 'Health check failed',
            'timestamp': current_app.config.get('SERVER_START_TIME')
        }), 500

# Station-specific display routes
@kitchen_display_bp.route('/station/<station_type>')
@login_required
def station_display(station_type):
    """Station-specific kitchen display"""
    valid_stations = ['general', 'grill', 'fry', 'salad', 'dessert', 'beverage', 'expo']
    
    if station_type not in valid_stations:
        return render_template('errors/404.html'), 404
    
    # Validate user has access to this station
    security = get_websocket_security()
    if not security.validate_display_config(current_user.role, 'Station Display', station_type):
        return render_template('errors/403.html'), 403
    
    return render_template('kot/station_display.html', station_type=station_type)

@kitchen_display_bp.route('/api/station-orders/<station_type>')
@login_required
def get_station_orders(station_type):
    """Get orders filtered by kitchen station"""
    try:
        valid_stations = ['general', 'grill', 'fry', 'salad', 'dessert', 'beverage', 'expo']
        
        if station_type not in valid_stations:
            return jsonify({
                'success': False,
                'error': 'Invalid station type'
            }), 400
        
        # Get orders for this station
        from models import Order, OrderItem, MenuItem
        from sqlalchemy import and_
        
        with current_app.app_context():
            # This would be enhanced based on menu item categorization
            # For now, return all active orders
            orders = Order.query.filter(
                Order.status.in_(['New', 'In Progress', 'Ready'])
            ).order_by(Order.created_at.asc()).all()
            
            order_data = []
            for order in orders:
                order_dict = order.to_dict()
                
                # Add station-specific filtering logic here
                # For example, filter items based on kitchen station
                items = OrderItem.query.filter_by(order_id=order.id).all()
                order_dict['items'] = [item.to_dict() for item in items]
                
                order_data.append(order_dict)
        
        return jsonify({
            'success': True,
            'orders': order_data,
            'station_type': station_type,
            'total_orders': len(order_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting station orders: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get station orders'
        }), 500