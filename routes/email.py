"""
Email Configuration Routes for Flask Web Version
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import json
import os
from datetime import datetime

from utils.email_service import EmailService

email_bp = Blueprint('email', __name__, url_prefix='/email')

@email_bp.route('/')
@login_required
def index():
    """Email configuration page"""
    try:
        # Initialize email service
        email_service = EmailService()
        
        # Get current configuration
        config = email_service.config
        
        # Get email history
        email_history = email_service.get_email_history(limit=20)
        
        # Get queue status
        queue_status = email_service.get_queue_status()
        
        return render_template('email/index.html', 
                           config=config, 
                           email_history=email_history,
                           queue_status=queue_status)
    
    except Exception as e:
        flash(f'Error loading email configuration: {str(e)}', 'error')
        return render_template('email/index.html', 
                           config=None, 
                           email_history=[],
                           queue_status={})

@email_bp.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    """Email configuration form"""
    try:
        email_service = EmailService()
        
        if request.method == 'POST':
            # Get form data
            smtp_server = request.form.get('smtp_server', '').strip()
            smtp_port = int(request.form.get('smtp_port', 587))
            use_tls = request.form.get('use_tls') == 'on'
            use_ssl = request.form.get('use_ssl') == 'on'
            
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            from_email = request.form.get('from_email', '').strip()
            from_name = request.form.get('from_name', 'POS Backup System').strip()
            
            recipients_str = request.form.get('recipients', '').strip()
            recipients = [email.strip() for email in recipients_str.split(',') if email.strip()]
            
            backup_notifications = request.form.get('backup_notifications') == 'on'
            test_emails = request.form.get('test_emails') == 'on'
            
            max_attachment_size_mb = int(request.form.get('max_attachment_size_mb', 25))
            retry_attempts = int(request.form.get('retry_attempts', 3))
            retry_delay_seconds = int(request.form.get('retry_delay_seconds', 5))
            
            # Update configuration
            from utils.email_service import EmailConfig
            new_config = EmailConfig(
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                use_tls=use_tls,
                use_ssl=use_ssl,
                username=username,
                password=password,
                from_email=from_email,
                from_name=from_name,
                recipients=recipients,
                backup_notifications=backup_notifications,
                test_emails=test_emails,
                max_attachment_size_mb=max_attachment_size_mb,
                retry_attempts=retry_attempts,
                retry_delay_seconds=retry_delay_seconds
            )
            
            # Save configuration
            if email_service.save_config(new_config):
                flash('Email configuration saved successfully', 'success')
                
                # Restart queue processor if settings changed
                if backup_notifications:
                    email_service.start_queue_processor()
                else:
                    email_service.stop_queue_processor()
                
                return redirect(url_for('email.index'))
            else:
                flash('Failed to save email configuration', 'error')
        
        # GET request - show current config
        config = email_service.config
        
        return render_template('email/config.html', config=config)
    
    except Exception as e:
        flash(f'Error saving email configuration: {str(e)}', 'error')
        return redirect(url_for('email.index'))

@email_bp.route('/test', methods=['POST'])
@login_required
def test():
    """Test email configuration"""
    try:
        email_service = EmailService()
        
        # Test connection
        success, message = email_service.test_connection()
        
        if success:
            # Send test email
            success, message = email_service.send_test_email()
            
            if success:
                flash('Test email sent successfully', 'success')
            else:
                flash(f'Test email failed: {message}', 'error')
        else:
            flash(f'Connection test failed: {message}', 'error')
        
        return redirect(url_for('email.config'))
    
    except Exception as e:
        flash(f'Error testing email: {str(e)}', 'error')
        return redirect(url_for('email.config'))

@email_bp.route('/history')
@login_required
def history():
    """Email history page"""
    try:
        email_service = EmailService()
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Get email history
        email_history = email_service.get_email_history(limit=per_page * page)
        
        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        paginated_history = email_history[start:end]
        
        return render_template('email/history.html', 
                           email_history=paginated_history,
                           page=page,
                           per_page=per_page,
                           total=len(email_history))
    
    except Exception as e:
        flash(f'Error loading email history: {str(e)}', 'error')
        return redirect(url_for('email.index'))

@email_bp.route('/queue/status')
@login_required
def queue_status():
    """Get email queue status (AJAX)"""
    try:
        email_service = EmailService()
        status = email_service.get_queue_status()
        return jsonify(status)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@email_bp.route('/history/clear', methods=['POST'])
@login_required
def clear_history():
    """Clear email history"""
    try:
        email_service = EmailService()
        older_than_days = int(request.form.get('older_than_days', 30))
        
        cleared_count = email_service.clear_email_history(older_than_days)
        
        flash(f'Cleared {cleared_count} old email history entries', 'success')
        return redirect(url_for('email.history'))
    
    except Exception as e:
        flash(f'Error clearing email history: {str(e)}', 'error')
        return redirect(url_for('email.history'))

@email_bp.route('/providers')
@login_required
def providers():
    """Email provider presets"""
    return render_template('email/providers.html')

@email_bp.route('/providers/preset/<provider>')
@login_required
def provider_preset(provider):
    """Get email provider preset configuration"""
    try:
        presets = {
            'gmail': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'use_tls': True,
                'use_ssl': False,
                'from_name': 'POS Backup System'
            },
            'outlook': {
                'smtp_server': 'smtp-mail.outlook.com',
                'smtp_port': 587,
                'use_tls': True,
                'use_ssl': False,
                'from_name': 'POS Backup System'
            },
            'yahoo': {
                'smtp_server': 'smtp.mail.yahoo.com',
                'smtp_port': 587,
                'use_tls': True,
                'use_ssl': False,
                'from_name': 'POS Backup System'
            },
            'office365': {
                'smtp_server': 'smtp.office365.com',
                'smtp_port': 587,
                'use_tls': True,
                'use_ssl': False,
                'from_name': 'POS Backup System'
            }
        }
        
        if provider in presets:
            return jsonify(presets[provider])
        else:
            return jsonify({'error': 'Unknown provider'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500