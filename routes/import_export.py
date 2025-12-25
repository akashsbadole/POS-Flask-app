"""
Import/Export Routes for Restaurant POS System
Provides API endpoints for bulk import/export functionality
"""

import os
import json
from flask import Blueprint, request, jsonify, render_template, send_file, redirect, url_for, flash, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime
import tempfile
import traceback

from utils.import_export_manager import ImportExportManager, validate_file_upload, get_import_export_permissions, ImportExportError
from models import db, User

import_export_bp = Blueprint('import_export', __name__, url_prefix='/import-export')

@import_export_bp.before_request
@login_required
def require_login():
    """Require login for all import/export routes"""
    pass

@import_export_bp.route('/')
def index():
    """Import/Export dashboard"""
    permissions = get_import_export_permissions(current_user)
    
    if not any(permissions.values()):
        flash('You do not have permission to access import/export functionality.', 'error')
        return redirect(url_for('dashboard.index'))
    
    return render_template('import_export/index.html', 
                         permissions=permissions,
                         user=current_user)

@import_export_bp.route('/api/upload', methods=['POST'])
def upload_import_file():
    """Handle file upload for import"""
    try:
        permissions = get_import_export_permissions(current_user)
        if not permissions['can_import']:
            return jsonify({'error': 'Permission denied'}), 403
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        is_valid, message = validate_file_upload(file, allowed_extensions)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Check file size (max 10MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({'error': 'File too large. Maximum size is 10MB'}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_filename = f"{timestamp}_{filename}"
        
        upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, temp_filename)
        
        file.save(filepath)
        
        # Validate and read file
        manager = ImportExportManager()
        
        try:
            data, format_type = manager.read_import_file(filepath)
            is_valid, validation_errors = manager.validate_import_data(data)
            
            # Store data in session for next step
            session['import_data'] = data
            session['import_filename'] = filename
            session['import_format'] = format_type
            
            return jsonify({
                'success': True,
                'filename': filename,
                'format': format_type,
                'record_count': len(data),
                'validation_errors': validation_errors if not is_valid else [],
                'preview': data[:5] if data else []  # First 5 records for preview
            })
            
        except ImportExportError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to read file: {str(e)}'}), 400
        finally:
            # Clean up temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    except RequestEntityTooLarge:
        return jsonify({'error': 'File too large'}), 413
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@import_export_bp.route('/api/preview', methods=['POST'])
def preview_import():
    """Preview import data before confirming"""
    try:
        permissions = get_import_export_permissions(current_user)
        if not permissions['can_import']:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = session.get('import_data')
        if not data:
            return jsonify({'error': 'No import data found. Please upload a file first.'}), 400
        
        # Limit preview to first 20 records
        preview_data = data[:20]
        
        return jsonify({
            'success': True,
            'total_records': len(data),
            'preview_records': len(preview_data),
            'preview': preview_data
        })
    
    except Exception as e:
        return jsonify({'error': f'Preview failed: {str(e)}'}), 500

@import_export_bp.route('/api/import', methods=['POST'])
def confirm_import():
    """Confirm and execute import"""
    try:
        permissions = get_import_export_permissions(current_user)
        if not permissions['can_import']:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = session.get('import_data')
        if not data:
            return jsonify({'error': 'No import data found. Please upload a file first.'}), 400
        
        # Get import options
        update_existing = request.json.get('update_existing', False) if request.json else False
        
        # Execute import
        manager = ImportExportManager()
        results = manager.import_menu_items(data, current_user.id, update_existing)
        
        # Save operation log
        log_entry = manager.save_import_log(
            operation_type='import',
            results=results,
            user_id=current_user.id,
            filename=session.get('import_filename')
        )
        
        # Clear session data
        session.pop('import_data', None)
        session.pop('import_filename', None)
        session.pop('import_format', None)
        
        return jsonify({
            'success': True,
            'results': results,
            'errors': manager.errors,
            'warnings': manager.warnings,
            'log': manager.import_log,
            'operation_log': log_entry
        })
    
    except Exception as e:
        return jsonify({'error': f'Import failed: {str(e)}'}), 500

@import_export_bp.route('/api/export', methods=['POST'])
def export_menu_items():
    """Export menu items"""
    try:
        permissions = get_import_export_permissions(current_user)
        if not permissions['can_export']:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Get export options
        data = request.get_json() or {}
        format_type = data.get('format', 'csv')
        category_filter = data.get('category_filter')
        
        if format_type not in ['csv', 'excel']:
            return jsonify({'error': 'Invalid export format. Use csv or excel.'}), 400
        
        # Execute export
        manager = ImportExportManager()
        result = manager.export_menu_items(format_type, category_filter)
        
        if result['success']:
            # Save operation log
            log_entry = manager.save_import_log(
                operation_type='export',
                results={'records': result['records'], 'format': result['format']},
                user_id=current_user.id,
                filename=result['filename']
            )
            
            return jsonify({
                'success': True,
                'filename': result['filename'],
                'filepath': result['filepath'],
                'records': result['records'],
                'format': result['format'],
                'operation_log': log_entry
            })
        else:
            return jsonify({'error': 'Export failed'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@import_export_bp.route('/api/download/<filename>')
def download_export(filename):
    """Download exported file"""
    try:
        permissions = get_import_export_permissions(current_user)
        if not permissions['can_export']:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Security check - only allow downloads from export directory
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Get file path
        export_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
        filepath = os.path.join(export_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Check file age (delete files older than 24 hours)
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(filepath))
        if file_age.total_seconds() > 24 * 3600:
            os.remove(filepath)
            return jsonify({'error': 'File has expired'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@import_export_bp.route('/api/template', methods=['POST'])
def generate_template():
    """Generate import template"""
    try:
        permissions = get_import_export_permissions(current_user)
        if not permissions['can_import']:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Get template format
        data = request.get_json() or {}
        format_type = data.get('format', 'csv')
        
        if format_type not in ['csv', 'excel']:
            return jsonify({'error': 'Invalid template format. Use csv or excel.'}), 400
        
        # Generate template
        manager = ImportExportManager()
        result = manager.generate_import_template(format_type)
        
        if result['success']:
            return jsonify({
                'success': True,
                'filename': result['filename'],
                'filepath': result['filepath'],
                'format': result['format']
            })
        else:
            return jsonify({'error': 'Template generation failed'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Template generation failed: {str(e)}'}), 500

@import_export_bp.route('/api/download-template/<filename>')
def download_template(filename):
    """Download import template"""
    try:
        permissions = get_import_export_permissions(current_user)
        if not permissions['can_import']:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Security check
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Get file path
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        filepath = os.path.join(template_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Template not found'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    
    except Exception as e:
        return jsonify({'error': f'Template download failed: {str(e)}'}), 500

@import_export_bp.route('/api/history')
def get_import_history():
    """Get import/export history"""
    try:
        permissions = get_import_export_permissions(current_user)
        if not permissions['can_view_history']:
            return jsonify({'error': 'Permission denied'}), 403
        
        manager = ImportExportManager()
        history = manager.get_import_history(current_user.id)
        
        return jsonify({
            'success': True,
            'history': history
        })
    
    except Exception as e:
        return jsonify({'error': f'Failed to get history: {str(e)}'}), 500

@import_export_bp.route('/api/validate-data', methods=['POST'])
def validate_import_data():
    """Validate import data without importing"""
    try:
        permissions = get_import_export_permissions(current_user)
        if not permissions['can_import']:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = session.get('import_data')
        if not data:
            return jsonify({'error': 'No import data found. Please upload a file first.'}), 400
        
        # Validate data
        manager = ImportExportManager()
        is_valid, validation_errors = manager.validate_import_data(data)
        
        # Get summary statistics
        categories = set()
        spice_levels = set()
        dietary_info = {'vegetarian': 0, 'vegan': 0, 'gluten_free': 0}
        
        for row in data:
            if row.get('category'):
                categories.add(row['category'])
            if row.get('spice_level'):
                spice_levels.add(row['spice_level'])
            
            # Count dietary preferences
            if str(row.get('is_vegetarian', '')).lower() in ['true', '1', 'yes']:
                dietary_info['vegetarian'] += 1
            if str(row.get('is_vegan', '')).lower() in ['true', '1', 'yes']:
                dietary_info['vegan'] += 1
            if str(row.get('is_gluten_free', '')).lower() in ['true', '1', 'yes']:
                dietary_info['gluten_free'] += 1
        
        return jsonify({
            'success': True,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'summary': {
                'total_records': len(data),
                'unique_categories': len(categories),
                'categories': list(categories),
                'spice_levels': list(spice_levels),
                'dietary_info': dietary_info
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'Validation failed: {str(e)}'}), 500

@import_export_bp.route('/api/cleanup', methods=['POST'])
def cleanup_session():
    """Clean up session data"""
    try:
        session.pop('import_data', None)
        session.pop('import_filename', None)
        session.pop('import_format', None)
        
        return jsonify({
            'success': True,
            'message': 'Session data cleaned up'
        })
    
    except Exception as e:
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500

# Error handlers
@import_export_bp.errorhandler(413)
def file_too_large(error):
    """Handle file too large error"""
    return jsonify({'error': 'File too large. Maximum size is 10MB'}), 413

@import_export_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server error"""
    db.session.rollback()
    return jsonify({'error': 'Internal server error occurred'}), 500

@import_export_bp.errorhandler(404)
def not_found_error(error):
    """Handle not found error"""
    return jsonify({'error': 'Resource not found'}), 404