"""
Footer Settings Routes for Flask Web Version
Handles footer configuration and management
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField
from wtforms.validators import DataRequired, Optional, Email
from models import Settings

footer_settings_bp = Blueprint('footer_settings', __name__)

class FooterSettingsForm(FlaskForm):
    """Footer settings form"""
    footer_enabled = BooleanField('Enable Footer')
    footer_fixed_position = BooleanField('Fixed Position')
    footer_business_name = StringField('Business Name', validators=[Optional()])
    footer_address = TextAreaField('Address', validators=[Optional()])
    footer_phone = StringField('Phone', validators=[Optional()])
    footer_email = StringField('Email', validators=[Optional(), Email()])
    footer_company_logo = StringField('Company Logo URL', validators=[Optional()])
    footer_logo_height = StringField('Logo Height', validators=[Optional()], default='30px')
    
    # Display options
    footer_show_business_info = BooleanField('Show Business Info')
    footer_show_receipt_info = BooleanField('Show Receipt Info')
    footer_show_user_name = BooleanField('Show User Name')
    footer_show_user_id = BooleanField('Show User ID')
    footer_show_timestamp = BooleanField('Show Timestamp')
    footer_show_page_info = BooleanField('Show Page Info')
    footer_show_version = BooleanField('Show Version')
    
    # Custom text
    footer_custom_text = TextAreaField('Custom Text', validators=[Optional()])
    
    # Styling options
    footer_background_color = StringField('Background Color', validators=[Optional()], default='#2c3e50')
    footer_text_color = StringField('Text Color', validators=[Optional()], default='#ecf0f1')
    footer_border_color = StringField('Border Color', validators=[Optional()], default='#34495e')
    footer_border_width = StringField('Border Width', validators=[Optional()], default='2px')
    footer_font_family = SelectField('Font Family', choices=[
        ('Arial, sans-serif', 'Arial'),
        ('Georgia, serif', 'Georgia'),
        ('Courier New, monospace', 'Courier New'),
        ('Times New Roman, serif', 'Times New Roman'),
        ('Verdana, sans-serif', 'Verdana')
    ], validators=[Optional()])
    footer_font_size = StringField('Font Size', validators=[Optional()], default='12px')
    footer_header_font_size = StringField('Header Font Size', validators=[Optional()], default='14px')
    footer_header_color = StringField('Header Color', validators=[Optional()], default='#3498db')
    footer_header_font_weight = SelectField('Header Font Weight', choices=[
        ('normal', 'Normal'),
        ('bold', 'Bold'),
        ('lighter', 'Lighter'),
        ('bolder', 'Bolder')
    ], validators=[Optional()])
    footer_small_font_size = StringField('Small Font Size', validators=[Optional()], default='10px')
    footer_padding = StringField('Padding', validators=[Optional()], default='15px 20px')
    
    # Additional settings
    footer_version = StringField('Version', validators=[Optional()], default='1.0.0')
    footer_default_user = StringField('Default User', validators=[Optional()], default='Staff')

@footer_settings_bp.route('/')
@login_required
def index():
    """Footer settings page"""
    form = FooterSettingsForm()
    
    # Load current settings into form
    settings = Settings.get_all_as_dict()
    for field_name, field in form._fields.items():
        if field_name in settings:
            if isinstance(field, BooleanField):
                field.data = settings[field_name].lower() == 'true'
            else:
                field.data = settings[field_name]
    
    return render_template('footer_settings/index.html', form=form)

@footer_settings_bp.route('/', methods=['POST'])
@login_required
def save_settings():
    """Save footer settings"""
    form = FooterSettingsForm()
    
    if form.validate_on_submit():
        try:
            # Save all form fields to settings
            for field_name, field in form._fields.items():
                if hasattr(field, 'data'):
                    value = str(field.data) if not isinstance(field.data, bool) else str(field.data).lower()
                    Settings.set(field_name, value)
            
            flash('Footer settings saved successfully!', 'success')
            return redirect(url_for('footer_settings.index'))
        except Exception as e:
            current_app.logger.error(f"Error saving footer settings: {str(e)}")
            flash('Error saving footer settings', 'error')
    
    # If form validation fails, show errors
    for field_name, errors in form.errors.items():
        for error in errors:
            flash(f'{getattr(form, field_name).label.text}: {error}', 'error')
    
    return render_template('footer_settings/index.html', form=form)

@footer_settings_bp.route('/reset', methods=['POST'])
@login_required
def reset_settings():
    """Reset footer settings to defaults"""
    try:
        default_settings = {
            'footer_enabled': 'true',
            'footer_fixed_position': 'false',
            'footer_business_name': '',
            'footer_address': '',
            'footer_phone': '',
            'footer_email': '',
            'footer_company_logo': '',
            'footer_logo_height': '30px',
            'footer_show_business_info': 'true',
            'footer_show_receipt_info': 'true',
            'footer_show_user_name': 'true',
            'footer_show_user_id': 'false',
            'footer_show_timestamp': 'true',
            'footer_show_page_info': 'true',
            'footer_show_version': 'false',
            'footer_custom_text': 'Thank you for your business!',
            'footer_background_color': '#2c3e50',
            'footer_text_color': '#ecf0f1',
            'footer_border_color': '#34495e',
            'footer_border_width': '2px',
            'footer_font_family': 'Arial, sans-serif',
            'footer_font_size': '12px',
            'footer_header_font_size': '14px',
            'footer_header_color': '#3498db',
            'footer_header_font_weight': 'bold',
            'footer_small_font_size': '10px',
            'footer_padding': '15px 20px',
            'footer_version': '1.0.0',
            'footer_default_user': 'Staff'
        }
        
        for key, value in default_settings.items():
            Settings.set(key, value)
        
        return jsonify({'success': True, 'message': 'Settings reset to defaults'})
    except Exception as e:
        current_app.logger.error(f"Error resetting footer settings: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@footer_settings_bp.route('/preview', methods=['POST'])
@login_required
def preview_footer():
    """Preview footer with current settings"""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        # Create footer config from preview data
        footer_config = {
            'enabled': data.get('footer_enabled', 'true') == 'true',
            'business_name': data.get('footer_business_name', 'Restaurant POS'),
            'address': data.get('footer_address', ''),
            'phone': data.get('footer_phone', ''),
            'email': data.get('footer_email', ''),
            'company_logo': data.get('footer_company_logo', ''),
            'logo_height': data.get('footer_logo_height', '30px'),
            'show_business_info': data.get('footer_show_business_info', 'true') == 'true',
            'show_receipt_info': data.get('footer_show_receipt_info', 'true') == 'true',
            'show_user_info': data.get('footer_show_user_name', 'true') == 'true',
            'show_user_id': data.get('footer_show_user_id', 'false') == 'true',
            'show_timestamp': data.get('footer_show_timestamp', 'true') == 'true',
            'show_page_info': data.get('footer_show_page_info', 'true') == 'true',
            'show_version': data.get('footer_show_version', 'false') == 'true',
            'custom_text': data.get('footer_custom_text', 'Thank you for your business!'),
            'background_color': data.get('footer_background_color', '#2c3e50'),
            'text_color': data.get('footer_text_color', '#ecf0f1'),
            'border_color': data.get('footer_border_color', '#34495e'),
            'border_width': data.get('footer_border_width', '2px'),
            'font_family': data.get('footer_font_family', 'Arial, sans-serif'),
            'font_size': data.get('footer_font_size', '12px'),
            'header_font_size': data.get('footer_header_font_size', '14px'),
            'header_color': data.get('footer_header_color', '#3498db'),
            'header_font_weight': data.get('footer_header_font_weight', 'bold'),
            'small_font_size': data.get('footer_small_font_size', '10px'),
            'padding': data.get('footer_padding', '15px 20px'),
            'fixed_position': data.get('footer_fixed_position', 'false') == 'true',
            'version': data.get('footer_version', '1.0.0'),
            'default_user': data.get('footer_default_user', 'Staff')
        }
        
        # Mock current receipt and user for preview
        mock_receipt = {
            'order_id': 'PREVIEW001',
            'order_date': '2024-12-10',
            'order_time': '19:13:00',
            'table_name': 'Table 1'
        }
        
        # Render footer component with preview data
        from flask import render_template_string
        footer_template = '''
        <div id="app-footer" class="app-footer {% if footer_config.get('fixed_position', False) %}fixed-footer{% endif %}">
            <div class="footer-container">
                <div class="footer-sections">
                    {% if footer_config.get('show_business_info', True) %}
                    <div class="footer-section business-info">
                        {% if footer_config.get('company_logo', '') %}
                        <div class="footer-logo">
                            <img src="{{ footer_config.company_logo }}" alt="Company Logo" 
                                 style="max-height: {{ footer_config.get('logo_height', '30px') }};">
                        </div>
                        {% endif %}
                        <div class="business-details">
                            <h4>{{ footer_config.get('business_name', 'Restaurant POS') }}</h4>
                            {% if footer_config.get('address', '') %}
                            <p class="footer-address">{{ footer_config.address }}</p>
                            {% endif %}
                            {% if footer_config.get('phone', '') %}
                            <p class="footer-phone">📞 {{ footer_config.phone }}</p>
                            {% endif %}
                            {% if footer_config.get('email', '') %}
                            <p class="footer-email">✉️ {{ footer_config.email }}</p>
                            {% endif %}
                        </div>
                    </div>
                    {% endif %}

                    {% if footer_config.get('show_receipt_info', True) %}
                    <div class="footer-section receipt-info">
                        <h4>Receipt Details</h4>
                        <p class="receipt-number">Receipt #: {{ current_receipt.order_id }}</p>
                        <p class="receipt-date">Date: {{ current_receipt.order_date }}</p>
                        <p class="receipt-time">Time: {{ current_receipt.order_time }}</p>
                        <p class="receipt-table">Table: {{ current_receipt.table_name }}</p>
                    </div>
                    {% endif %}

                    {% if footer_config.get('show_user_info', True) %}
                    <div class="footer-section user-info">
                        <h4>Staff Information</h4>
                        <p class="user-name">Served by: {{ footer_config.get('default_user', 'Staff') }}</p>
                        {% if footer_config.get('show_user_id', False) %}
                        <p class="user-id">ID: STAFF001</p>
                        {% endif %}
                    </div>
                    {% endif %}

                    {% if footer_config.get('custom_text', '') %}
                    <div class="footer-section custom-text">
                        <p class="custom-message">{{ footer_config.custom_text | safe }}</p>
                    </div>
                    {% endif %}
                </div>

                <div class="footer-bottom">
                    <div class="footer-left">
                        {% if footer_config.get('show_timestamp', True) %}
                        <span class="timestamp">{{ moment().format('YYYY-MM-DD HH:mm:ss') }}</span>
                        {% endif %}
                    </div>
                    <div class="footer-center">
                        {% if footer_config.get('show_page_info', True) %}
                        <span class="page-info">Footer Preview</span>
                        {% endif %}
                    </div>
                    <div class="footer-right">
                        {% if footer_config.get('show_version', False) %}
                        <span class="version">v{{ footer_config.get('version', '1.0.0') }}</span>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        
        <style>
        .app-footer {
            background-color: {{ footer_config.get('background_color', '#2c3e50') }};
            color: {{ footer_config.get('text_color', '#ecf0f1') }};
            padding: {{ footer_config.get('padding', '15px 20px') }};
            border-top: {{ footer_config.get('border_width', '2px') }} solid {{ footer_config.get('border_color', '#34495e') }};
            font-family: {{ footer_config.get('font_family', 'Arial, sans-serif') }};
            font-size: {{ footer_config.get('font_size', '12px') }};
            margin-top: 20px;
            width: 100%;
        }

        .footer-sections {
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 10px;
        }

        .footer-section {
            flex: 1;
            min-width: 200px;
        }

        .footer-section h4 {
            margin: 0 0 5px 0;
            font-size: {{ footer_config.get('header_font_size', '14px') }};
            color: {{ footer_config.get('header_color', '#3498db') }};
            font-weight: {{ footer_config.get('header_font_weight', 'bold') }};
        }

        .footer-section p {
            margin: 2px 0;
            line-height: 1.4;
        }

        .footer-bottom {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid {{ footer_config.get('border_color', '#34495e') }};
            padding-top: 8px;
            margin-top: 8px;
            font-size: {{ footer_config.get('small_font_size', '10px') }};
            opacity: 0.8;
        }

        .footer-left, .footer-center, .footer-right {
            flex: 1;
        }

        .footer-center {
            text-align: center;
        }

        .footer-right {
            text-align: right;
        }
        </style>
        '''
        
        return render_template_string(footer_template, 
                                     footer_config=footer_config, 
                                     current_receipt=mock_receipt)
    except Exception as e:
        current_app.logger.error(f"Error generating footer preview: {str(e)}")
        return f'<div class="alert alert-danger">Error generating preview: {str(e)}</div>'

@footer_settings_bp.route('/api/settings')
def get_settings():
    """Get footer settings as JSON"""
    settings = {
        'footer_enabled': Settings.get('footer_enabled', 'true'),
        'footer_business_name': Settings.get('footer_business_name', ''),
        'footer_address': Settings.get('footer_address', ''),
        'footer_phone': Settings.get('footer_phone', ''),
        'footer_email': Settings.get('footer_email', ''),
        'footer_company_logo': Settings.get('footer_company_logo', ''),
        'footer_show_business_info': Settings.get('footer_show_business_info', 'true'),
        'footer_show_receipt_info': Settings.get('footer_show_receipt_info', 'true'),
        'footer_show_user_name': Settings.get('footer_show_user_name', 'true'),
        'footer_show_user_id': Settings.get('footer_show_user_id', 'false'),
        'footer_show_timestamp': Settings.get('footer_show_timestamp', 'true'),
        'footer_show_page_info': Settings.get('footer_show_page_info', 'true'),
        'footer_custom_text': Settings.get('footer_custom_text', 'Thank you for your business!'),
        'footer_background_color': Settings.get('footer_background_color', '#2c3e50'),
        'footer_text_color': Settings.get('footer_text_color', '#ecf0f1'),
        'footer_border_color': Settings.get('footer_border_color', '#34495e'),
        'footer_border_width': Settings.get('footer_border_width', '2px'),
        'footer_font_family': Settings.get('footer_font_family', 'Arial, sans-serif'),
        'footer_font_size': Settings.get('footer_font_size', '12px'),
        'footer_header_font_size': Settings.get('footer_header_font_size', '14px'),
        'footer_header_color': Settings.get('footer_header_color', '#3498db'),
        'footer_header_font_weight': Settings.get('footer_header_font_weight', 'bold'),
        'footer_small_font_size': Settings.get('footer_small_font_size', '10px'),
        'footer_padding': Settings.get('footer_padding', '15px 20px'),
        'footer_logo_height': Settings.get('footer_logo_height', '30px'),
        'footer_fixed_position': Settings.get('footer_fixed_position', 'false'),
        'footer_version': Settings.get('footer_version', '1.0.0'),
        'footer_default_user': Settings.get('footer_default_user', 'Staff')
    }
    return jsonify(settings)