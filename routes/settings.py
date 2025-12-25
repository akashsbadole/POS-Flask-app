from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Settings, User
from datetime import datetime
import json
import os
import shutil
from werkzeug.exceptions import BadRequest
import logging

settings_bp = Blueprint('settings', __name__)

# Configure logging
logger = logging.getLogger(__name__)

@settings_bp.route('/')
@login_required
def index():
    """Settings dashboard page"""
    try:
        # Check if user has permission to access settings
        if not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.index'))
        
        # Get all settings for the template
        all_settings = Settings.get_all()
        
        # Get email settings separately (they might be encrypted)
        email_settings = {
            'smtp_server': Settings.get('smtp_server', ''),
            'smtp_port': Settings.get('smtp_port', '587'),
            'username': Settings.get('email_username', ''),
            'password': '',  # Don't expose password
            'from_email': Settings.get('from_email', '')
        }
        
        return render_template('settings/index.html', 
                             settings=all_settings,
                             email_settings=email_settings)
    except Exception as e:
        logger.error(f"Error loading settings page: {str(e)}")
        flash('Error loading settings page', 'error')
        return redirect(url_for('dashboard.index'))

@settings_bp.route('/save', methods=['POST'])
@login_required
def save_settings():
    """Save settings via AJAX"""
    try:
        # Check if user has permission to modify settings
        if not current_user.is_admin():
            return jsonify({
                'success': False, 
                'message': 'Access denied. Admin privileges required.'
            }), 403
        
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        settings_data = data.get('settings', {})
        email_data = data.get('email_settings', {})
        
        # Validate and save regular settings
        saved_count = 0
        for key, value in settings_data.items():
            try:
                # Skip empty or None values for sensitive settings
                if value is None or value == '':
                    continue
                    
                # Get setting description if exists
                existing_setting = Settings.query.filter_by(key=key).first()
                description = existing_setting.description if existing_setting else None
                is_public = existing_setting.is_public if existing_setting else False
                
                Settings.set(key, value, description, is_public)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Failed to save setting {key}: {str(e)}")
                continue
        
        # Save email settings
        email_saved_count = 0
        for key, value in email_data.items():
            try:
                if value is None or value == '':
                    continue
                    
                # Don't save empty passwords
                if key == 'password' and not value:
                    continue
                    
                # Map frontend keys to database keys
                db_key = key
                if key == 'username':
                    db_key = 'email_username'
                
                Settings.set(db_key, value)
                email_saved_count += 1
            except Exception as e:
                logger.warning(f"Failed to save email setting {key}: {str(e)}")
                continue
        
        # Log the settings change
        logger.info(f"User {current_user.username} updated {saved_count} settings and {email_saved_count} email settings")
        
        return jsonify({
            'success': True,
            'message': f'Settings saved successfully ({saved_count + email_saved_count} items)',
            'saved_count': saved_count + email_saved_count
        })
        
    except BadRequest as e:
        logger.error(f"Bad request in save_settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Invalid request data'
        }), 400
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error saving settings. Please try again.'
        }), 500

@settings_bp.route('/reset', methods=['POST'])
@login_required
def reset_settings():
    """Reset settings to defaults"""
    try:
        # Check if user has permission
        if not current_user.is_admin():
            return jsonify({
                'success': False, 
                'message': 'Access denied. Admin privileges required.'
            }), 403
        
        # Recreate default settings
        Settings.create_defaults()
        
        # Log the reset
        logger.warning(f"User {current_user.username} reset all settings to defaults")
        
        return jsonify({
            'success': True,
            'message': 'Settings reset to defaults successfully'
        })
        
    except Exception as e:
        logger.error(f"Error resetting settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error resetting settings. Please try again.'
        }), 500

@settings_bp.route('/backup', methods=['POST'])
@login_required
def create_backup():
    """Create manual backup of settings"""
    try:
        # Check if user has permission
        if not current_user.is_admin():
            return jsonify({
                'success': False, 
                'message': 'Access denied. Admin privileges required.'
            }), 403
        
        # Get all settings
        all_settings = Settings.get_all()
        
        # Create backup data
        backup_data = {
            'settings': all_settings,
            'backup_timestamp': datetime.utcnow().isoformat(),
            'created_by': current_user.username,
            'version': '1.0'
        }
        
        # Create backup directory if it doesn't exist
        backup_dir = 'backups/settings'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'settings_backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Save backup file
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        # Update last backup timestamp
        Settings.set('last_backup', datetime.utcnow().isoformat())
        
        # Log the backup
        logger.info(f"User {current_user.username} created settings backup: {backup_filename}")
        
        return jsonify({
            'success': True,
            'message': 'Settings backup created successfully',
            'backup_filename': backup_filename,
            'backup_time': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error creating backup. Please try again.'
        }), 500

@settings_bp.route('/test_email', methods=['POST'])
@login_required
def test_email():
    """Test email configuration"""
    try:
        # Check if user has permission
        if not current_user.is_admin():
            return jsonify({
                'success': False, 
                'message': 'Access denied. Admin privileges required.'
            }), 403
        
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        # Get email settings from request
        smtp_server = data.get('smtp_server', '').strip()
        smtp_port = data.get('smtp_port', '587').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        from_email = data.get('from_email', '').strip()
        
        # Validate required fields
        if not all([smtp_server, username, password, from_email]):
            return jsonify({
                'success': False,
                'message': 'All email fields are required for testing'
            }), 400
        
        # Test email configuration
        try:
            import smtplib
            from email.mime.text import MimeText
            from email.mime.multipart import MimeMultipart
            
            # Create test message
            msg = MimeMultipart()
            msg['From'] = from_email
            msg['To'] = username
            msg['Subject'] = 'Test Email - Restaurant POS System'
            
            # Email body
            body = f"""
            Test Email Configuration
            ========================
            
            This is a test email from your Restaurant POS system.
            
            Configuration Details:
            - SMTP Server: {smtp_server}:{smtp_port}
            - From: {from_email}
            - Test Time: {datetime.utcnow().isoformat()}
            
            If you received this email, your email configuration is working correctly.
            
            Best regards,
            Restaurant POS System
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send test email
            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            # Log successful test
            logger.info(f"User {current_user.username} successfully tested email configuration")
            
            return jsonify({
                'success': True,
                'message': 'Test email sent successfully. Please check your inbox.'
            })
            
        except smtplib.SMTPAuthenticationError:
            return jsonify({
                'success': False,
                'message': 'Authentication failed. Please check your username and password.'
            }), 400
        except smtplib.SMTPConnectError:
            return jsonify({
                'success': False,
                'message': 'Could not connect to SMTP server. Please check server address and port.'
            }), 400
        except Exception as e:
            logger.error(f"SMTP error during email test: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Email test failed: {str(e)}'
            }), 400
        
    except BadRequest as e:
        logger.error(f"Bad request in test_email: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Invalid request data'
        }), 400
    except Exception as e:
        logger.error(f"Error testing email: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error testing email configuration. Please try again.'
        }), 500

@settings_bp.route('/export')
@login_required
def export_settings():
    """Export all settings as JSON"""
    try:
        # Check if user has permission
        if not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.index'))
        
        # Get all settings
        all_settings = Settings.get_all()
        
        # Create export data
        export_data = {
            'settings': all_settings,
            'export_timestamp': datetime.utcnow().isoformat(),
            'exported_by': current_user.username,
            'version': '1.0'
        }
        
        # Return JSON response
        response = jsonify(export_data)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'settings_export_{timestamp}.json'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        # Log the export
        logger.info(f"User {current_user.username} exported settings")
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting settings: {str(e)}")
        flash('Error exporting settings. Please try again.', 'error')
        return redirect(url_for('settings.index'))

@settings_bp.route('/import', methods=['POST'])
@login_required
def import_settings():
    """Import settings from JSON file"""
    try:
        # Check if user has permission
        if not current_user.is_admin():
            return jsonify({
                'success': False,
                'message': 'Access denied. Admin privileges required.'
            }), 403
        
        # Check if file is present
        if 'settings_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No file uploaded'
            }), 400
        
        file = request.files['settings_file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            }), 400
        
        # Read and parse JSON file
        try:
            import_data = json.load(file)
        except json.JSONDecodeError:
            return jsonify({
                'success': False,
                'message': 'Invalid JSON file'
            }), 400
        
        # Validate import data structure
        if 'settings' not in import_data:
            return jsonify({
                'success': False,
                'message': 'Invalid settings file format'
            }), 400
        
        # Import settings
        settings_data = import_data['settings']
        imported_count = 0
        
        for key, value in settings_data.items():
            try:
                Settings.set(key, value)
                imported_count += 1
            except Exception as e:
                logger.warning(f"Failed to import setting {key}: {str(e)}")
                continue
        
        # Log the import
        logger.info(f"User {current_user.username} imported {imported_count} settings")
        
        return jsonify({
            'success': True,
            'message': f'Settings imported successfully ({imported_count} items)',
            'imported_count': imported_count
        })
        
    except Exception as e:
        logger.error(f"Error importing settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error importing settings. Please try again.'
        }), 500

@settings_bp.route('/api/settings')
@login_required
def get_settings_api():
    """Get settings via API (for AJAX requests)"""
    try:
        # Check if user has permission to view settings
        if not current_user.is_admin():
            return jsonify({
                'error': 'Access denied'
            }), 403
        
        # Get all settings
        all_settings = Settings.get_all()
        
        return jsonify({
            'success': True,
            'settings': all_settings,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting settings via API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error retrieving settings'
        }), 500

@settings_bp.route('/api/validate', methods=['POST'])
@login_required
def validate_settings():
    """Validate settings values"""
    try:
        # Check if user has permission
        if not current_user.is_admin():
            return jsonify({
                'success': False,
                'message': 'Access denied'
            }), 403
        
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        settings_data = data.get('settings', {})
        validation_errors = []
        
        # Validate specific settings
        for key, value in settings_data.items():
            try:
                if key == 'tax_rate':
                    # Validate tax rate
                    tax_rate = float(value)
                    if not 0 <= tax_rate <= 100:
                        validation_errors.append(f"Tax rate must be between 0 and 100, got {tax_rate}")
                
                elif key == 'decimal_places':
                    # Validate decimal places
                    decimal_places = int(value)
                    if not 0 <= decimal_places <= 4:
                        validation_errors.append(f"Decimal places must be between 0 and 4, got {decimal_places}")
                
                elif key in ['smtp_port', 'backup_retention_days', 'items_per_page']:
                    # Validate numeric fields
                    try:
                        num_value = int(value)
                        if key == 'smtp_port' and not (1 <= num_value <= 65535):
                            validation_errors.append(f"SMTP port must be between 1 and 65535, got {num_value}")
                        elif key == 'backup_retention_days' and not (1 <= num_value <= 365):
                            validation_errors.append(f"Backup retention days must be between 1 and 365, got {num_value}")
                        elif key == 'items_per_page' and not (10 <= num_value <= 1000):
                            validation_errors.append(f"Items per page must be between 10 and 1000, got {num_value}")
                    except ValueError:
                        validation_errors.append(f"{key} must be a valid number, got '{value}'")
                
                elif key == 'restaurant_email':
                    # Basic email validation
                    if value and '@' not in value:
                        validation_errors.append(f"Invalid email address: {value}")
                
            except Exception as e:
                validation_errors.append(f"Error validating {key}: {str(e)}")
        
        if validation_errors:
            return jsonify({
                'success': False,
                'errors': validation_errors
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'All settings are valid'
        })
        
    except BadRequest as e:
        logger.error(f"Bad request in validate_settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Invalid request data'
        }), 400
    except Exception as e:
        logger.error(f"Error validating settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error validating settings'
        }), 500