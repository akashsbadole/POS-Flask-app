"""
White Label Management Routes
Handles logo uploads, branding customizations, and white label settings
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from models import db, Settings
from utils.image_handler import WhiteLabelImageHandler
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import json
import logging
from datetime import datetime
import uuid

white_label_bp = Blueprint('white_label', __name__)

# Configure logging
logger = logging.getLogger(__name__)

@white_label_bp.route('/')
@login_required
def index():
    """White label management dashboard"""
    try:
        # Check if user has permission to access white label settings
        if not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.index'))
        
        # Get all white label settings
        white_label_settings = Settings.get_white_label_settings()
        
        # Get settings by category
        company_info = Settings.get_company_info()
        branding_info = Settings.get_branding_info()
        logo_settings = Settings.get_logo_settings()
        color_scheme = Settings.get_color_scheme()
        typography = Settings.get_typography_settings()
        ui_customization = Settings.get_ui_customization_settings()
        email_branding = Settings.get_email_branding_settings()
        print_branding = Settings.get_print_branding_settings()
        custom_content = Settings.get_custom_content_settings()
        
        return render_template('white_label/index.html',
                             white_label_settings=white_label_settings,
                             company_info=company_info,
                             branding_info=branding_info,
                             logo_settings=logo_settings,
                             color_scheme=color_scheme,
                             typography=typography,
                             ui_customization=ui_customization,
                             email_branding=email_branding,
                             print_branding=print_branding,
                             custom_content=custom_content)
    except Exception as e:
        logger.error(f"Error loading white label dashboard: {str(e)}")
        flash('Error loading white label settings', 'error')
        return redirect(url_for('dashboard.index'))

@white_label_bp.route('/company-info', methods=['GET', 'POST'])
@login_required
def company_info():
    """Manage company information settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Validate and save company info
            company_fields = [
                'company_name', 'company_full_name', 'company_short_name', 'company_tagline',
                'company_address_line1', 'company_address_line2', 'company_city', 'company_state',
                'company_country', 'company_postal_code', 'company_phone_primary', 'company_phone_secondary',
                'company_email_primary', 'company_email_secondary', 'company_website',
                'company_registration_number', 'company_tax_id', 'company_legal_entity', 'company_year_established'
            ]
            
            saved_count = 0
            for field in company_fields:
                if field in data:
                    value = data[field].strip() if data[field] else ''
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            # Also update legacy restaurant settings for compatibility
            if 'company_name' in data:
                Settings.set('restaurant_name', data['company_name'], 'Restaurant name for receipts and display', True)
            if 'company_phone_primary' in data:
                Settings.set('restaurant_phone', data['company_phone_primary'], 'Restaurant phone number', True)
            if 'company_email_primary' in data:
                Settings.set('restaurant_email', data['company_email_primary'], 'Restaurant email address', True)
            if 'company_tax_id' in data:
                Settings.set('gst_number', data['company_tax_id'], 'GST registration number', True)
            
            logger.info(f"User {current_user.username} updated {saved_count} company info settings")
            
            return jsonify({
                'success': True,
                'message': f'Company information saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        company_info = Settings.get_company_info()
        return jsonify({
            'success': True,
            'company_info': company_info
        })
        
    except Exception as e:
        logger.error(f"Error managing company info: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing company information'
        }), 500

@white_label_bp.route('/upload-logo', methods=['POST'])
@login_required
def upload_logo():
    """Upload logo for white label branding"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Check if file is present
        if 'logo_file' not in request.files:
            return jsonify({'success': False, 'message': 'No logo file provided'}), 400
        
        file = request.files['logo_file']
        logo_type = request.form.get('logo_type', 'main')
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Validate logo type
        valid_types = ['main', 'header', 'footer', 'favicon', 'invoice', 'email', 'login']
        if logo_type not in valid_types:
            return jsonify({'success': False, 'message': f'Invalid logo type: {logo_type}'}), 400
        
        # Process logo upload
        upload_folder = 'static/images/branding'
        success, result = WhiteLabelImageHandler.process_white_label_logo_upload(
            file, logo_type, upload_folder
        )
        
        if not success:
            return jsonify({'success': False, 'message': result}), 400
        
        # Save logo path to settings
        relative_path = os.path.relpath(result['original_path'], 'static')
        logo_setting_key = f'logo_{logo_type}_path'
        Settings.set_white_label_setting(logo_setting_key, relative_path)
        
        # Get logo info
        logo_info_success, logo_info = WhiteLabelImageHandler.get_white_label_logo_info(
            result['original_path']
        )
        
        logger.info(f"User {current_user.username} uploaded {logo_type} logo: {result['filename']}")
        
        return jsonify({
            'success': True,
            'message': f'{logo_type.title()} logo uploaded successfully',
            'logo_info': {
                'filename': result['filename'],
                'file_size': result['file_size'],
                'format': result['format'],
                'path': relative_path,
                'url': f'/static/{relative_path}',
                'recommended_contexts': logo_info.get('recommended_contexts', []) if logo_info_success else []
            },
            'logo_type': logo_type
        })
        
    except Exception as e:
        logger.error(f"Error uploading logo: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error uploading logo: {str(e)}'
        }), 500

@white_label_bp.route('/delete-logo/<logo_type>', methods=['DELETE'])
@login_required
def delete_logo(logo_type):
    """Delete uploaded logo"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Validate logo type
        valid_types = ['main', 'header', 'footer', 'favicon', 'invoice', 'email', 'login']
        if logo_type not in valid_types:
            return jsonify({'success': False, 'message': f'Invalid logo type: {logo_type}'}), 400
        
        # Get current logo path
        logo_setting_key = f'logo_{logo_type}_path'
        logo_path = Settings.get(logo_setting_key)
        
        if not logo_path:
            return jsonify({'success': False, 'message': 'No logo found to delete'}), 404
        
        # Build full path
        full_path = os.path.join('static', logo_path.lstrip('/'))
        
        # Delete logo file
        success, error_msg = WhiteLabelImageHandler.delete_white_label_logo(full_path)
        if not success:
            logger.warning(f"Could not delete logo file: {error_msg}")
        
        # Clear setting
        Settings.set_white_label_setting(logo_setting_key, '')
        
        logger.info(f"User {current_user.username} deleted {logo_type} logo")
        
        return jsonify({
            'success': True,
            'message': f'{logo_type.title()} logo deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting logo: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting logo: {str(e)}'
        }), 500

@white_label_bp.route('/branding-settings', methods=['GET', 'POST'])
@login_required
def branding_settings():
    """Manage branding settings (colors, fonts, etc.)"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save branding settings
            branding_fields = [
                # Colors
                'brand_primary_color', 'brand_secondary_color', 'brand_accent_color',
                'bg_primary_color', 'bg_secondary_color', 'bg_header_color', 'bg_footer_color',
                'text_primary_color', 'text_secondary_color', 'text_light_color',
                'text_header_color', 'text_footer_color',
                'brand_success_color', 'brand_warning_color', 'brand_danger_color', 'brand_info_color',
                'brand_light_color', 'brand_dark_color',
                
                # Typography
                'font_primary_family', 'font_secondary_family', 'font_header_family', 'font_body_family',
                'font_size_base', 'font_size_small', 'font_size_large',
                'font_size_h1', 'font_size_h2', 'font_size_h3', 'font_size_h4', 'font_size_h5', 'font_size_h6',
                'font_weight_light', 'font_weight_normal', 'font_weight_medium', 'font_weight_semibold', 'font_weight_bold',
                'line_height_base', 'line_height_heading',
                
                # Logo display options
                'logo_show_in_header', 'logo_show_in_footer', 'logo_show_in_login', 'logo_show_in_emails', 'logo_show_in_invoices',
                'logo_height_header', 'logo_height_footer', 'logo_height_login'
            ]
            
            saved_count = 0
            for field in branding_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} branding settings")
            
            return jsonify({
                'success': True,
                'message': f'Branding settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        branding_info = Settings.get_branding_info()
        logo_settings = Settings.get_logo_settings()
        color_scheme = Settings.get_color_scheme()
        typography = Settings.get_typography_settings()
        
        return jsonify({
            'success': True,
            'branding_info': branding_info,
            'logo_settings': logo_settings,
            'color_scheme': color_scheme,
            'typography': typography
        })
        
    except Exception as e:
        logger.error(f"Error managing branding settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing branding settings'
        }), 500

@white_label_bp.route('/ui-customization', methods=['GET', 'POST'])
@login_required
def ui_customization():
    """Manage UI customization settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save UI customization settings
            ui_fields = [
                'login_background_image', 'login_background_color', 'login_card_background',
                'login_title', 'login_subtitle', 'login_features_enabled',
                'dashboard_welcome_text', 'dashboard_stats_enabled', 'dashboard_quick_actions_enabled',
                'nav_style', 'nav_color_scheme', 'nav_show_branding',
                'theme_preset', 'theme_custom_enabled'
            ]
            
            saved_count = 0
            for field in ui_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} UI customization settings")
            
            return jsonify({
                'success': True,
                'message': f'UI customization saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        ui_customization = Settings.get_ui_customization_settings()
        
        return jsonify({
            'success': True,
            'ui_customization': ui_customization
        })
        
    except Exception as e:
        logger.error(f"Error managing UI customization: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing UI customization'
        }), 500

@white_label_bp.route('/custom-content', methods=['GET', 'POST'])
@login_required
def custom_content():
    """Manage custom content settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save custom content settings
            content_fields = [
                'welcome_message_dashboard', 'welcome_message_login', 'welcome_message_registration',
                'custom_header_text', 'custom_footer_text', 'custom_about_text', 'custom_contact_text',
                'custom_css_enabled', 'custom_css_content', 'custom_css_priority'
            ]
            
            saved_count = 0
            for field in content_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} custom content settings")
            
            return jsonify({
                'success': True,
                'message': f'Custom content saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        custom_content = Settings.get_custom_content_settings()
        
        return jsonify({
            'success': True,
            'custom_content': custom_content
        })
        
    except Exception as e:
        logger.error(f"Error managing custom content: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing custom content'
        }), 500

@white_label_bp.route('/generate-css', methods=['POST'])
@login_required
def generate_css():
    """Generate CSS based on white label settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get all relevant settings
        color_scheme = Settings.get_color_scheme()
        typography = Settings.get_typography_settings()
        ui_customization = Settings.get_ui_customization_settings()
        
        # Generate CSS
        css_content = generate_white_label_css(color_scheme, typography, ui_customization)
        
        # Save to file
        css_file_path = 'static/css/white-label-custom.css'
        os.makedirs(os.path.dirname(css_file_path), exist_ok=True)
        
        with open(css_file_path, 'w') as f:
            f.write(css_content)
        
        # Enable custom CSS
        Settings.set('custom_css_enabled', 'true')
        Settings.set('custom_css_content', css_content)
        
        logger.info(f"User {current_user.username} generated white label CSS")
        
        return jsonify({
            'success': True,
            'message': 'White label CSS generated successfully',
            'css_file': '/static/css/white-label-custom.css',
            'css_size': len(css_content)
        })
        
    except Exception as e:
        logger.error(f"Error generating CSS: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error generating CSS: {str(e)}'
        }), 500

@white_label_bp.route('/preview', methods=['POST'])
@login_required
def preview_branding():
    """Preview white label changes"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No preview data provided'}), 400
        
        preview_type = data.get('preview_type', 'dashboard')
        
        if preview_type == 'dashboard':
            # Generate dashboard preview
            preview_html = generate_dashboard_preview(data)
        elif preview_type == 'login':
            # Generate login page preview
            preview_html = generate_login_preview(data)
        elif preview_type == 'email':
            # Generate email template preview
            preview_html = generate_email_preview(data)
        else:
            return jsonify({'success': False, 'message': 'Invalid preview type'}), 400
        
        return jsonify({
            'success': True,
            'preview_html': preview_html,
            'preview_type': preview_type
        })
        
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error generating preview: {str(e)}'
        }), 500

@white_label_bp.route('/reset', methods=['POST'])
@login_required
def reset_white_label():
    """Reset white label settings to defaults"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Reset white label settings to defaults
        reset_settings = {
            'company_name': 'Restaurant POS',
            'brand_primary_color': '#007bff',
            'brand_secondary_color': '#6c757d',
            'brand_accent_color': '#28a745',
            'bg_primary_color': '#ffffff',
            'bg_secondary_color': '#f8f9fa',
            'text_primary_color': '#212529',
            'font_primary_family': 'Inter, sans-serif',
            'login_background_color': '#f8f9fa',
            'login_card_background': '#ffffff',
            'login_title': 'Welcome Back',
            'login_subtitle': 'Sign in to manage your restaurant',
            'theme_preset': 'default',
            'custom_css_enabled': 'false'
        }
        
        for key, value in reset_settings.items():
            Settings.set_white_label_setting(key, value)
        
        logger.warning(f"User {current_user.username} reset white label settings to defaults")
        
        return jsonify({
            'success': True,
            'message': 'White label settings reset to defaults successfully'
        })
        
    except Exception as e:
        logger.error(f"Error resetting white label settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error resetting white label settings: {str(e)}'
        }), 500

def generate_white_label_css(color_scheme, typography, ui_customization):
    """Generate CSS content based on white label settings"""
    css_template = """
/* White Label Custom CSS */
/* Generated automatically from white label settings */

:root {
    /* Brand Colors */
    --brand-primary: {brand_primary_color};
    --brand-secondary: {brand_secondary_color};
    --brand-accent: {brand_accent_color};
    --brand-success: {brand_success_color};
    --brand-warning: {brand_warning_color};
    --brand-danger: {brand_danger_color};
    --brand-info: {brand_info_color};
    --brand-light: {brand_light_color};
    --brand-dark: {brand_dark_color};
    
    /* Background Colors */
    --bg-primary: {bg_primary_color};
    --bg-secondary: {bg_secondary_color};
    --bg-header: {bg_header_color};
    --bg-footer: {bg_footer_color};
    
    /* Text Colors */
    --text-primary: {text_primary_color};
    --text-secondary: {text_secondary_color};
    --text-light: {text_light_color};
    --text-header: {text_header_color};
    --text-footer: {text_footer_color};
    
    /* Typography */
    --font-primary: {font_primary_family};
    --font-secondary: {font_secondary_family};
    --font-header: {font_header_family};
    --font-body: {font_body_family};
    
    --font-size-base: {font_size_base};
    --font-size-small: {font_size_small};
    --font-size-large: {font_size_large};
    
    --font-weight-light: {font_weight_light};
    --font-weight-normal: {font_weight_normal};
    --font-weight-medium: {font_weight_medium};
    --font-weight-semibold: {font_weight_semibold};
    --font-weight-bold: {font_weight_bold};
    
    --line-height-base: {line_height_base};
    --line-height-heading: {line_height_heading};
}

/* Custom CSS overrides */
body {{
    font-family: var(--font-primary);
    color: var(--text-primary);
    background-color: var(--bg-primary);
}}

.modern-header {{
    background-color: var(--bg-header);
    color: var(--text-header);
}}

.modern-sidebar {{
    background-color: var(--bg-secondary);
}}

.modern-btn-primary {{
    background-color: var(--brand-primary);
    border-color: var(--brand-primary);
}}

.modern-badge-primary {{
    background-color: var(--brand-primary);
}}

.text-primary {{ color: var(--brand-primary) !important; }}
.text-secondary {{ color: var(--brand-secondary) !important; }}
.text-accent {{ color: var(--brand-accent) !important; }}

.bg-primary {{ background-color: var(--brand-primary) !important; }}
.bg-secondary {{ background-color: var(--brand-secondary) !important; }}
.bg-light {{ background-color: var(--brand-light) !important; }}
.bg-dark {{ background-color: var(--brand-dark) !important; }}

.modern-login-container {{
    background-color: {login_background_color};
}}

.login-card {{
    background-color: {login_card_background};
}}

/* Print Styles */
@media print {{
    .print-header {{
        color: {invoice_header_color};
    }}
    
    .receipt-header {{
        color: {receipt_header_color};
    }}
}}
"""
    
    # Fill in the CSS template with actual values
    css_content = css_template.format(
        brand_primary_color=color_scheme.get('brand_primary_color', '#007bff'),
        brand_secondary_color=color_scheme.get('brand_secondary_color', '#6c757d'),
        brand_accent_color=color_scheme.get('brand_accent_color', '#28a745'),
        brand_success_color=color_scheme.get('brand_success_color', '#28a745'),
        brand_warning_color=color_scheme.get('brand_warning_color', '#ffc107'),
        brand_danger_color=color_scheme.get('brand_danger_color', '#dc3545'),
        brand_info_color=color_scheme.get('brand_info_color', '#17a2b8'),
        brand_light_color=color_scheme.get('brand_light_color', '#f8f9fa'),
        brand_dark_color=color_scheme.get('brand_dark_color', '#343a40'),
        bg_primary_color=color_scheme.get('bg_primary_color', '#ffffff'),
        bg_secondary_color=color_scheme.get('bg_secondary_color', '#f8f9fa'),
        bg_header_color=color_scheme.get('bg_header_color', '#ffffff'),
        bg_footer_color=color_scheme.get('bg_footer_color', '#f8f9fa'),
        text_primary_color=color_scheme.get('text_primary_color', '#212529'),
        text_secondary_color=color_scheme.get('text_secondary_color', '#6c757d'),
        text_light_color=color_scheme.get('text_light_color', '#ffffff'),
        text_header_color=color_scheme.get('text_header_color', '#212529'),
        text_footer_color=color_scheme.get('text_footer_color', '#6c757d'),
        font_primary_family=typography.get('font_primary_family', 'Inter, sans-serif'),
        font_secondary_family=typography.get('font_secondary_family', 'Inter, sans-serif'),
        font_header_family=typography.get('font_header_family', 'Inter, sans-serif'),
        font_body_family=typography.get('font_body_family', 'Inter, sans-serif'),
        font_size_base=typography.get('font_size_base', '14px'),
        font_size_small=typography.get('font_size_small', '12px'),
        font_size_large=typography.get('font_size_large', '16px'),
        font_weight_light=typography.get('font_weight_light', '300'),
        font_weight_normal=typography.get('font_weight_normal', '400'),
        font_weight_medium=typography.get('font_weight_medium', '500'),
        font_weight_semibold=typography.get('font_weight_semibold', '600'),
        font_weight_bold=typography.get('font_weight_bold', '700'),
        line_height_base=typography.get('line_height_base', '1.5'),
        line_height_heading=typography.get('line_height_heading', '1.2'),
        login_background_color=ui_customization.get('login_background_color', '#f8f9fa'),
        login_card_background=ui_customization.get('login_card_background', '#ffffff'),
        invoice_header_color=color_scheme.get('invoice_header_color', '#007bff'),
        receipt_header_color=color_scheme.get('receipt_header_color', '#007bff')
    )
    
    return css_content

def generate_dashboard_preview(data):
    """Generate dashboard preview HTML"""
    company_name = data.get('company_name', 'Restaurant POS')
    primary_color = data.get('brand_primary_color', '#007bff')
    
    preview_html = f"""
    <div class="dashboard-preview" style="border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
        <div class="modern-header" style="background-color: #fff; padding: 15px; border-radius: 8px 8px 0 0; border-bottom: 1px solid #ddd;">
            <div class="d-flex align-items-center">
                <div class="modern-logo">
                    <i class="bi bi-shop" style="color: {primary_color};"></i>
                    <span style="font-weight: 600; margin-left: 10px;">{company_name}</span>
                </div>
            </div>
        </div>
        <div style="padding: 20px; background-color: #f8f9fa;">
            <h4 style="color: {primary_color}; margin-bottom: 15px;">Dashboard Preview</h4>
            <div class="row">
                <div class="col-md-3">
                    <div class="card" style="border-left: 4px solid {primary_color};">
                        <div class="card-body">
                            <h6 class="card-title">Today's Sales</h6>
                            <h4 style="color: {primary_color};">₹15,420</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card" style="border-left: 4px solid #28a745;">
                        <div class="card-body">
                            <h6 class="card-title">Orders</h6>
                            <h4 style="color: #28a745;">24</h4>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return preview_html

def generate_login_preview(data):
    """Generate login page preview HTML"""
    company_name = data.get('company_name', 'Restaurant POS')
    primary_color = data.get('brand_primary_color', '#007bff')
    login_title = data.get('login_title', 'Welcome Back')
    login_subtitle = data.get('login_subtitle', 'Sign in to manage your restaurant')
    
    preview_html = f"""
    <div class="login-preview" style="border: 1px solid #ddd; border-radius: 8px; overflow: hidden; max-width: 400px;">
        <div style="background-color: #f8f9fa; padding: 40px 30px; text-align: center;">
            <div style="margin-bottom: 30px;">
                <i class="bi bi-shop" style="font-size: 48px; color: {primary_color};"></i>
                <h3 style="margin-top: 15px; color: #333;">{company_name}</h3>
            </div>
            <h4 style="color: #333; margin-bottom: 10px;">{login_title}</h4>
            <p style="color: #666; margin-bottom: 30px;">{login_subtitle}</p>
            <div style="background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="margin-bottom: 20px;">
                    <div style="border: 1px solid #ddd; padding: 12px; border-radius: 4px; background-color: #f8f9fa;">
                        Username
                    </div>
                </div>
                <div style="margin-bottom: 20px;">
                    <div style="border: 1px solid #ddd; padding: 12px; border-radius: 4px; background-color: #f8f9fa;">
                        Password
                    </div>
                </div>
                <button style="background-color: {primary_color}; color: white; border: none; padding: 12px 30px; border-radius: 4px; width: 100%;">
                    Sign In
                </button>
            </div>
        </div>
    </div>
    """
    return preview_html

def generate_email_preview(data):
    """Generate email template preview HTML"""
    company_name = data.get('company_name', 'Restaurant POS')
    primary_color = data.get('brand_primary_color', '#007bff')
    
    preview_html = f"""
    <div class="email-preview" style="border: 1px solid #ddd; border-radius: 8px; overflow: hidden; max-width: 600px; font-family: Arial, sans-serif;">
        <div style="background-color: {primary_color}; color: white; padding: 20px; text-align: center;">
            <h3 style="margin: 0;">{company_name}</h3>
        </div>
        <div style="padding: 30px; background-color: #ffffff;">
            <h4 style="color: #333;">Order Confirmation</h4>
            <p>Dear Customer,</p>
            <p>Your order has been confirmed and is being prepared.</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0;">
                <strong>Order #12345</strong><br>
                Total: ₹450.00
            </div>
            <p>Thank you for choosing {company_name}!</p>
        </div>
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px;">
            <p>&copy; 2025 {company_name}. All rights reserved.</p>
        </div>
    </div>
    """
    return preview_html

@white_label_bp.route('/email-branding', methods=['GET', 'POST'])
@login_required
def email_branding():
    """Manage email branding settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save email branding settings
            email_fields = [
                'email_header_logo', 'email_footer_logo', 'email_signature_text', 'email_contact_info',
                'email_primary_color', 'email_background_color', 'email_text_color',
                'email_template_style', 'email_show_social_links', 'email_social_links'
            ]
            
            saved_count = 0
            for field in email_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} email branding settings")
            
            return jsonify({
                'success': True,
                'message': f'Email branding settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        email_branding = Settings.get_email_branding_settings()
        
        return jsonify({
            'success': True,
            'email_branding': email_branding
        })
        
    except Exception as e:
        logger.error(f"Error managing email branding: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing email branding'
        }), 500

@white_label_bp.route('/print-branding', methods=['GET', 'POST'])
@login_required
def print_branding():
    """Manage print branding settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save print branding settings
            print_fields = [
                'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
                'receipt_logo_path', 'receipt_header_color', 'receipt_footer_text', 'receipt_custom_message',
                'print_header_enabled', 'print_footer_enabled', 'print_logo_size', 'print_font_size'
            ]
            
            saved_count = 0
            for field in print_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} print branding settings")
            
            return jsonify({
                'success': True,
                'message': f'Print branding settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        print_branding = Settings.get_print_branding_settings()
        
        return jsonify({
            'success': True,
            'print_branding': print_branding
        })
        
    except Exception as e:
        logger.error(f"Error managing print branding: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing print branding'
        }), 500
