"""
Printer Customization Routes
Comprehensive printer customization management integrated with white labeling
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from models import db, Settings
from datetime import datetime
import json
import logging
import uuid
import os
import io
from werkzeug.utils import secure_filename

printer_customization_bp = Blueprint('printer_customization', __name__)

# Configure logging
logger = logging.getLogger(__name__)

@printer_customization_bp.route('/')
@login_required
def index():
    """Printer customization dashboard"""
    try:
        # Check if user has permission to access printer settings
        if not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.index'))
        
        # Get all printer settings categories
        receipt_settings = Settings.get_receipt_settings()
        invoice_settings = Settings.get_invoice_settings()
        kot_settings = Settings.get_kot_settings()
        thermal_settings = Settings.get_thermal_printer_settings()
        multi_printer_settings = Settings.get_multi_printer_settings()
        print_quality_settings = Settings.get_print_quality_settings()
        print_layout_settings = Settings.get_print_layout_settings()
        print_template_settings = Settings.get_print_template_settings()
        print_branding_settings = Settings.get_print_branding_settings()
        
        return render_template('white_label/printer_customization.html',
                             receipt_settings=receipt_settings,
                             invoice_settings=invoice_settings,
                             kot_settings=kot_settings,
                             thermal_settings=thermal_settings,
                             multi_printer_settings=multi_printer_settings,
                             print_quality_settings=print_quality_settings,
                             print_layout_settings=print_layout_settings,
                             print_template_settings=print_template_settings,
                             print_branding_settings=print_branding_settings)
    except Exception as e:
        logger.error(f"Error loading printer customization dashboard: {str(e)}")
        flash('Error loading printer customization settings', 'error')
        return redirect(url_for('dashboard.index'))

@printer_customization_bp.route('/receipt-settings', methods=['GET', 'POST'])
@login_required
def receipt_settings():
    """Manage receipt customization settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save receipt settings
            receipt_fields = [
                'receipt_logo_path', 'receipt_header_color', 'receipt_footer_text', 'receipt_custom_message',
                'receipt_header_enabled', 'receipt_footer_enabled', 'receipt_logo_size', 'receipt_font_size',
                'receipt_layout_style', 'receipt_header_template', 'receipt_footer_template',
                'receipt_show_company_logo', 'receipt_show_company_info', 'receipt_show_gst_number',
                'receipt_show_order_date', 'receipt_show_order_time', 'receipt_show_customer_name',
                'receipt_show_payment_methods', 'receipt_show_discounts', 'receipt_show_tax_breakdown',
                'receipt_cutting_line', 'receipt_barcode_enabled', 'receipt_qr_code_enabled'
            ]
            
            saved_count = 0
            for field in receipt_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} receipt settings")
            
            return jsonify({
                'success': True,
                'message': f'Receipt settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        receipt_settings = Settings.get_receipt_settings()
        return jsonify({
            'success': True,
            'receipt_settings': receipt_settings
        })
        
    except Exception as e:
        logger.error(f"Error managing receipt settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing receipt settings'
        }), 500

@printer_customization_bp.route('/invoice-settings', methods=['GET', 'POST'])
@login_required
def invoice_settings():
    """Manage invoice customization settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save invoice settings
            invoice_fields = [
                'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
                'invoice_header_enabled', 'invoice_footer_enabled', 'invoice_logo_size', 'invoice_font_size',
                'invoice_layout_style', 'invoice_header_template', 'invoice_footer_template',
                'invoice_show_company_logo', 'invoice_show_company_info', 'invoice_show_gst_number',
                'invoice_show_order_date', 'invoice_show_order_time', 'invoice_show_customer_name',
                'invoice_show_payment_methods', 'invoice_show_discounts', 'invoice_show_tax_breakdown',
                'invoice_billing_address', 'invoice_shipping_address', 'invoice_show_bank_details',
                'invoice_terms_enabled', 'invoice_notes_enabled', 'invoice_show_signature'
            ]
            
            saved_count = 0
            for field in invoice_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} invoice settings")
            
            return jsonify({
                'success': True,
                'message': f'Invoice settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        invoice_settings = Settings.get_invoice_settings()
        return jsonify({
            'success': True,
            'invoice_settings': invoice_settings
        })
        
    except Exception as e:
        logger.error(f"Error managing invoice settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing invoice settings'
        }), 500

@printer_customization_bp.route('/kot-settings', methods=['GET', 'POST'])
@login_required
def kot_settings():
    """Manage KOT (Kitchen Order Ticket) customization settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save KOT settings
            kot_fields = [
                'kot_logo_path', 'kot_header_color', 'kot_footer_text', 'kot_custom_message',
                'kot_header_enabled', 'kot_footer_enabled', 'kot_logo_size', 'kot_font_size',
                'kot_layout_style', 'kot_header_template', 'kot_footer_template',
                'kot_show_company_logo', 'kot_show_company_info', 'kot_table_number_style',
                'kot_order_type_display', 'kot_priority_display', 'kot_show_special_instructions',
                'kot_show_cooking_time', 'kot_cutting_line', 'kot_order_separation'
            ]
            
            saved_count = 0
            for field in kot_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} KOT settings")
            
            return jsonify({
                'success': True,
                'message': f'KOT settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        kot_settings = Settings.get_kot_settings()
        return jsonify({
            'success': True,
            'kot_settings': kot_settings
        })
        
    except Exception as e:
        logger.error(f"Error managing KOT settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing KOT settings'
        }), 500

@printer_customization_bp.route('/thermal-settings', methods=['GET', 'POST'])
@login_required
def thermal_settings():
    """Manage thermal printer settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save thermal printer settings
            thermal_fields = [
                'thermal_printer_name', 'thermal_paper_width', 'thermal_print_density', 'thermal_print_speed',
                'thermal_font_family', 'thermal_font_size', 'thermal_font_weight', 'thermal_line_spacing',
                'thermal_margin_top', 'thermal_margin_bottom', 'thermal_margin_left', 'thermal_margin_right',
                'thermal_header_spacing', 'thermal_item_spacing', 'thermal_footer_spacing',
                'thermal_print_logo', 'thermal_logo_size', 'thermal_logo_position',
                'thermal_cut_paper', 'thermal_partial_cut', 'thermal_beep_enabled', 'thermal_feed_lines'
            ]
            
            saved_count = 0
            for field in thermal_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} thermal printer settings")
            
            return jsonify({
                'success': True,
                'message': f'Thermal printer settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        thermal_settings = Settings.get_thermal_printer_settings()
        return jsonify({
            'success': True,
            'thermal_settings': thermal_settings
        })
        
    except Exception as e:
        logger.error(f"Error managing thermal printer settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing thermal printer settings'
        }), 500

@printer_customization_bp.route('/multi-printer-settings', methods=['GET', 'POST'])
@login_required
def multi_printer_settings():
    """Manage multi-printer configuration settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save multi-printer settings
            multi_printer_fields = [
                'default_printer_name', 'printer_profiles_enabled', 'printer_location_mapping',
                'bill_printer_name', 'kot_printer_name', 'invoice_printer_name', 'report_printer_name',
                'kitchen_printer_name', 'bar_printer_name', 'receipt_printer_name',
                'printer_auto_selection', 'printer_fallback_enabled', 'printer_priority_order'
            ]
            
            saved_count = 0
            for field in multi_printer_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} multi-printer settings")
            
            return jsonify({
                'success': True,
                'message': f'Multi-printer settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        multi_printer_settings = Settings.get_multi_printer_settings()
        return jsonify({
            'success': True,
            'multi_printer_settings': multi_printer_settings
        })
        
    except Exception as e:
        logger.error(f"Error managing multi-printer settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing multi-printer settings'
        }), 500

@printer_customization_bp.route('/print-quality-settings', methods=['GET', 'POST'])
@login_required
def print_quality_settings():
    """Manage print quality and formatting settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save print quality settings
            quality_fields = [
                'print_quality_dpi', 'print_contrast', 'print_brightness', 'print_speed_draft',
                'print_speed_normal', 'print_speed_high', 'print_dithering', 'print_color_mode',
                'print_media_type', 'print_finishing', 'print_collation', 'print_copies_default'
            ]
            
            saved_count = 0
            for field in quality_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} print quality settings")
            
            return jsonify({
                'success': True,
                'message': f'Print quality settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        print_quality_settings = Settings.get_print_quality_settings()
        return jsonify({
            'success': True,
            'print_quality_settings': print_quality_settings
        })
        
    except Exception as e:
        logger.error(f"Error managing print quality settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing print quality settings'
        }), 500

@printer_customization_bp.route('/print-layout-settings', methods=['GET', 'POST'])
@login_required
def print_layout_settings():
    """Manage print layout and formatting settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save print layout settings
            layout_fields = [
                'print_page_orientation', 'print_page_size', 'print_margins', 'print_scaling',
                'print_headers_footers', 'print_page_numbers', 'print_date_time', 'print_logo_watermark',
                'print_border_enabled', 'print_shadow_enabled', 'print_alignment', 'print_wrapping'
            ]
            
            saved_count = 0
            for field in layout_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} print layout settings")
            
            return jsonify({
                'success': True,
                'message': f'Print layout settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        print_layout_settings = Settings.get_print_layout_settings()
        return jsonify({
            'success': True,
            'print_layout_settings': print_layout_settings
        })
        
    except Exception as e:
        logger.error(f"Error managing print layout settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing print layout settings'
        }), 500

@printer_customization_bp.route('/print-template-settings', methods=['GET', 'POST'])
@login_required
def print_template_settings():
    """Manage print template and customization settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Save print template settings
            template_fields = [
                'print_template_receipt', 'print_template_invoice', 'print_template_kot',
                'print_template_custom_css', 'print_template_javascript', 'print_template_variables',
                'print_dynamic_content', 'print_conditional_content', 'print_loop_content'
            ]
            
            saved_count = 0
            for field in template_fields:
                if field in data:
                    value = data[field]
                    Settings.set_white_label_setting(field, value)
                    saved_count += 1
            
            logger.info(f"User {current_user.username} updated {saved_count} print template settings")
            
            return jsonify({
                'success': True,
                'message': f'Print template settings saved successfully ({saved_count} fields)',
                'saved_count': saved_count
            })
        
        # GET request - return current settings
        print_template_settings = Settings.get_print_template_settings()
        return jsonify({
            'success': True,
            'print_template_settings': print_template_settings
        })
        
    except Exception as e:
        logger.error(f"Error managing print template settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error managing print template settings'
        }), 500

@printer_customization_bp.route('/generate-print-css', methods=['POST'])
@login_required
def generate_print_css():
    """Generate CSS for print templates based on settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get all print-related settings
        receipt_settings = Settings.get_receipt_settings()
        invoice_settings = Settings.get_invoice_settings()
        kot_settings = Settings.get_kot_settings()
        thermal_settings = Settings.get_thermal_printer_settings()
        print_layout_settings = Settings.get_print_layout_settings()
        print_branding_settings = Settings.get_print_branding_settings()
        
        # Generate CSS
        css_content = generate_comprehensive_print_css(
            receipt_settings, invoice_settings, kot_settings, 
            thermal_settings, print_layout_settings, print_branding_settings
        )
        
        # Save to file
        css_file_path = 'static/css/print-customization.css'
        os.makedirs(os.path.dirname(css_file_path), exist_ok=True)
        
        with open(css_file_path, 'w') as f:
            f.write(css_content)
        
        # Enable custom print CSS
        Settings.set('print_custom_css_enabled', 'true')
        Settings.set('print_custom_css_content', css_content)
        
        logger.info(f"User {current_user.username} generated comprehensive print CSS")
        
        return jsonify({
            'success': True,
            'message': 'Print CSS generated successfully',
            'css_file': '/static/css/print-customization.css',
            'css_size': len(css_content)
        })
        
    except Exception as e:
        logger.error(f"Error generating print CSS: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error generating print CSS: {str(e)}'
        }), 500

@printer_customization_bp.route('/export-settings', methods=['POST'])
@login_required
def export_printer_settings():
    """Export printer customization settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get all printer settings
        all_settings = {
            'receipt_settings': Settings.get_receipt_settings(),
            'invoice_settings': Settings.get_invoice_settings(),
            'kot_settings': Settings.get_kot_settings(),
            'thermal_settings': Settings.get_thermal_printer_settings(),
            'multi_printer_settings': Settings.get_multi_printer_settings(),
            'print_quality_settings': Settings.get_print_quality_settings(),
            'print_layout_settings': Settings.get_print_layout_settings(),
            'print_template_settings': Settings.get_print_template_settings(),
            'print_branding_settings': Settings.get_print_branding_settings()
        }
        
        # Add metadata
        export_data = {
            'export_info': {
                'exported_at': datetime.now().isoformat(),
                'exported_by': current_user.username,
                'version': '1.0',
                'type': 'printer_customization_settings'
            },
            'settings': all_settings
        }
        
        # Convert to JSON
        export_json = json.dumps(export_data, indent=2)
        
        # Create response
        filename = f"printer_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return send_file(
            io.BytesIO(export_json.encode('utf-8')),
            filename=filename,
            as_attachment=True,
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Error exporting printer settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error exporting printer settings: {str(e)}'
        }), 500

@printer_customization_bp.route('/import-settings', methods=['POST'])
@login_required
def import_printer_settings():
    """Import printer customization settings"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        if 'settings_file' not in request.files:
            return jsonify({'success': False, 'message': 'No settings file provided'}), 400
        
        file = request.files['settings_file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Read and parse JSON file
        try:
            import_data = json.loads(file.read().decode('utf-8'))
        except json.JSONDecodeError:
            return jsonify({'success': False, 'message': 'Invalid JSON file'}), 400
        
        # Validate import data structure
        if 'settings' not in import_data:
            return jsonify({'success': False, 'message': 'Invalid settings file format'}), 400
        
        # Import settings
        imported_count = 0
        for category, settings in import_data['settings'].items():
            for key, value in settings.items():
                try:
                    Settings.set_white_label_setting(key, str(value))
                    imported_count += 1
                except ValueError:
                    # Skip invalid keys
                    continue
        
        logger.info(f"User {current_user.username} imported {imported_count} printer settings")
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {imported_count} printer settings',
            'imported_count': imported_count
        })
        
    except Exception as e:
        logger.error(f"Error importing printer settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error importing printer settings: {str(e)}'
        }), 500

@printer_customization_bp.route('/reset-settings', methods=['POST'])
@login_required
def reset_printer_settings():
    """Reset printer customization settings to defaults"""
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Reset printer settings to defaults
        default_settings = {
            # Receipt defaults
            'receipt_header_enabled': 'true',
            'receipt_footer_enabled': 'true',
            'receipt_logo_size': '100px',
            'receipt_font_size': '12px',
            'receipt_show_company_logo': 'true',
            'receipt_show_company_info': 'true',
            'receipt_show_order_date': 'true',
            'receipt_show_order_time': 'true',
            'receipt_cutting_line': 'true',
            
            # Invoice defaults
            'invoice_header_enabled': 'true',
            'invoice_footer_enabled': 'true',
            'invoice_logo_size': '150px',
            'invoice_font_size': '14px',
            'invoice_show_company_logo': 'true',
            'invoice_show_company_info': 'true',
            'invoice_show_gst_number': 'true',
            'invoice_terms_enabled': 'true',
            
            # KOT defaults
            'kot_header_enabled': 'true',
            'kot_footer_enabled': 'true',
            'kot_logo_size': '80px',
            'kot_font_size': '11px',
            'kot_show_company_logo': 'true',
            'kot_table_number_style': 'bold',
            'kot_show_special_instructions': 'true',
            
            # Thermal printer defaults
            'thermal_paper_width': '80mm',
            'thermal_print_density': 'medium',
            'thermal_font_family': 'monospace',
            'thermal_font_size': '12px',
            'thermal_line_spacing': '1.5',
            'thermal_cut_paper': 'true',
            
            # Multi-printer defaults
            'printer_profiles_enabled': 'false',
            'printer_auto_selection': 'true',
            'printer_fallback_enabled': 'true',
            
            # Print quality defaults
            'print_quality_dpi': '203',
            'print_speed_normal': 'true',
            'print_color_mode': 'monochrome',
            'print_copies_default': '1',
            
            # Print layout defaults
            'print_page_orientation': 'portrait',
            'print_headers_footers': 'true',
            'print_alignment': 'center',
            
            # Print branding defaults
            'print_header_enabled': 'true',
            'print_footer_enabled': 'true',
            'print_logo_size': '100px',
            'print_font_size': '12px'
        }
        
        for key, value in default_settings.items():
            Settings.set_white_label_setting(key, value)
        
        logger.warning(f"User {current_user.username} reset printer settings to defaults")
        
        return jsonify({
            'success': True,
            'message': 'Printer settings reset to defaults successfully',
            'reset_count': len(default_settings)
        })
        
    except Exception as e:
        logger.error(f"Error resetting printer settings: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error resetting printer settings: {str(e)}'
        }), 500

def generate_comprehensive_print_css(receipt_settings, invoice_settings, kot_settings, 
                                   thermal_settings, print_layout_settings, print_branding_settings):
    """Generate comprehensive CSS for print templates"""
    
    css_template = """
/* Comprehensive Print Customization CSS */
/* Generated from printer customization settings */

@media print {
    /* Global Print Styles */
    * {
        -webkit-print-color-adjust: exact !important;
        color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    
    /* Receipt Styles */
    .receipt-container {{
        width: {receipt_width};
        font-family: {receipt_font_family};
        font-size: {receipt_font_size};
        line-height: {receipt_line_height};
        color: {receipt_text_color};
    }}
    
    .receipt-header {{
        text-align: {receipt_header_align};
        margin-bottom: {receipt_header_spacing};
        border-bottom: {receipt_header_border};
        padding-bottom: 10px;
    }}
    
    .receipt-logo {{
        max-width: {receipt_logo_size};
        max-height: {receipt_logo_size};
        {receipt_logo_display}
    }}
    
    .receipt-company-info {{
        {receipt_company_info_display}
        margin-top: 5px;
    }}
    
    .receipt-order-info {{
        margin: 10px 0;
        {receipt_order_info_display}
    }}
    
    .receipt-items {{
        margin: 15px 0;
    }}
    
    .receipt-item {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 5px;
        border-bottom: {receipt_item_border};
        padding-bottom: 3px;
    }}
    
    .receipt-footer {{
        margin-top: 20px;
        padding-top: 10px;
        border-top: {receipt_footer_border};
        text-align: {receipt_footer_align};
    }}
    
    .receipt-cutting-line {{
        {receipt_cutting_line_display}
        border-top: 1px dashed #000;
        margin: 20px 0;
    }}
    
    /* Invoice Styles */
    .invoice-container {{
        width: {invoice_width};
        font-family: {invoice_font_family};
        font-size: {invoice_font_size};
        line-height: {invoice_line_height};
        color: {invoice_text_color};
    }}
    
    .invoice-header {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
        border-bottom: {invoice_header_border};
        padding-bottom: 15px;
    }}
    
    .invoice-logo {{
        max-width: {invoice_logo_size};
        max-height: {invoice_logo_size};
        {invoice_logo_display}
    }}
    
    .invoice-company-details {{
        text-align: right;
        {invoice_company_display}
    }}
    
    .invoice-billing-info {{
        display: flex;
        justify-content: space-between;
        margin: 20px 0;
    }}
    
    .invoice-items-table {{
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
    }}
    
    .invoice-items-table th,
    .invoice-items-table td {{
        border: {invoice_table_border};
        padding: 8px;
        text-align: left;
    }}
    
    .invoice-items-table th {{
        background-color: {invoice_header_bg};
        font-weight: bold;
    }}
    
    .invoice-totals {{
        float: right;
        margin: 20px 0;
        width: 250px;
    }}
    
    .invoice-total-row {{
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: {invoice_total_border};
    }}
    
    .invoice-total-row.final {{
        font-weight: bold;
        font-size: {invoice_total_font_size};
        border-top: 2px solid #000;
        padding-top: 10px;
    }}
    
    .invoice-footer {{
        clear: both;
        margin-top: 30px;
        padding-top: 15px;
        border-top: {invoice_footer_border};
    }}
    
    /* KOT Styles */
    .kot-container {{
        width: {kot_width};
        font-family: {kot_font_family};
        font-size: {kot_font_size};
        line-height: {kot_line_height};
        color: {kot_text_color};
    }}
    
    .kot-header {{
        text-align: {kot_header_align};
        margin-bottom: {kot_header_spacing};
        border-bottom: {kot_header_border};
        padding-bottom: 8px;
    }}
    
    .kot-logo {{
        max-width: {kot_logo_size};
        max-height: {kot_logo_size};
        {kot_logo_display}
    }}
    
    .kot-order-details {{
        margin: 15px 0;
        {kot_order_display}
    }}
    
    .kot-table-number {{
        font-size: {kot_table_font_size};
        font-weight: {kot_table_weight};
        color: {kot_table_color};
        {kot_table_display}
    }}
    
    .kot-items {{
        margin: 15px 0;
    }}
    
    .kot-item {{
        margin-bottom: 8px;
        padding: 8px;
        border: {kot_item_border};
        border-radius: 4px;
        background-color: {kot_item_bg};
    }}
    
    .kot-item-priority {{
        {kot_priority_display}
        font-weight: bold;
        color: {kot_priority_color};
    }}
    
    .kot-special-instructions {{
        {kot_instructions_display}
        font-style: italic;
        color: {kot_instructions_color};
        margin-top: 5px;
    }}
    
    .kot-footer {{
        margin-top: 20px;
        text-align: {kot_footer_align};
        border-top: {kot_footer_border};
        padding-top: 10px;
    }}
    
    .kot-cutting-line {{
        {kot_cutting_line_display}
        border-top: 1px dashed #000;
        margin: 15px 0;
    }}
    
    /* Thermal Printer Optimizations */
    @media print and (max-width: 80mm) {{
        .thermal-container {{
            width: 100%;
            margin: 0;
            padding: 0;
        }}
        
        .thermal-header,
        .thermal-footer {{
            margin: 5px 0;
        }}
        
        .thermal-items {{
            margin: 10px 0;
        }}
        
        .thermal-item {{
            margin-bottom: 3px;
            padding: 2px 0;
        }}
    }}
    
    /* General Print Optimizations */
    .no-print {{
        display: none !important;
    }}
    
    .print-only {{
        display: block !important;
    }}
    
    /* Custom Print CSS from Settings */
    {custom_print_css}
}
"""
    
    # Fill in the CSS template with actual values from settings
    css_content = css_template.format(
        # Receipt settings
        receipt_width=receipt_settings.get('receipt_width', '100%'),
        receipt_font_family=receipt_settings.get('receipt_font_family', 'monospace'),
        receipt_font_size=receipt_settings.get('receipt_font_size', '12px'),
        receipt_line_height=receipt_settings.get('receipt_line_height', '1.4'),
        receipt_text_color=receipt_settings.get('receipt_text_color', '#000'),
        receipt_header_align=receipt_settings.get('receipt_header_align', 'center'),
        receipt_header_spacing=receipt_settings.get('receipt_header_spacing', '15px'),
        receipt_header_border=receipt_settings.get('receipt_header_border', '1px solid #000'),
        receipt_logo_size=receipt_settings.get('receipt_logo_size', '100px'),
        receipt_logo_display='display: block;' if receipt_settings.get('receipt_show_company_logo', 'true') == 'true' else 'display: none;',
        receipt_company_info_display='display: block;' if receipt_settings.get('receipt_show_company_info', 'true') == 'true' else 'display: none;',
        receipt_order_info_display='display: block;' if receipt_settings.get('receipt_show_order_date', 'true') == 'true' else 'display: none;',
        receipt_item_border=receipt_settings.get('receipt_item_border', '1px dotted #ccc'),
        receipt_footer_align=receipt_settings.get('receipt_footer_align', 'center'),
        receipt_footer_border=receipt_settings.get('receipt_footer_border', '1px solid #000'),
        receipt_cutting_line_display='display: block;' if receipt_settings.get('receipt_cutting_line', 'true') == 'true' else 'display: none;',
        
        # Invoice settings
        invoice_width=invoice_settings.get('invoice_width', '100%'),
        invoice_font_family=invoice_settings.get('invoice_font_family', 'Arial, sans-serif'),
        invoice_font_size=invoice_settings.get('invoice_font_size', '14px'),
        invoice_line_height=invoice_settings.get('invoice_line_height', '1.4'),
        invoice_text_color=invoice_settings.get('invoice_text_color', '#000'),
        invoice_header_border=invoice_settings.get('invoice_header_border', '2px solid #000'),
        invoice_logo_size=invoice_settings.get('invoice_logo_size', '150px'),
        invoice_logo_display='display: block;' if invoice_settings.get('invoice_show_company_logo', 'true') == 'true' else 'display: none;',
        invoice_company_display='display: block;' if invoice_settings.get('invoice_show_company_info', 'true') == 'true' else 'display: none;',
        invoice_table_border=invoice_settings.get('invoice_table_border', '1px solid #000'),
        invoice_header_bg=invoice_settings.get('invoice_header_bg', '#f0f0f0'),
        invoice_total_border=invoice_settings.get('invoice_total_border', '1px solid #ccc'),
        invoice_total_font_size=invoice_settings.get('invoice_total_font_size', '16px'),
        invoice_footer_border=invoice_settings.get('invoice_footer_border', '1px solid #000'),
        
        # KOT settings
        kot_width=kot_settings.get('kot_width', '100%'),
        kot_font_family=kot_settings.get('kot_font_family', 'monospace'),
        kot_font_size=kot_settings.get('kot_font_size', '11px'),
        kot_line_height=kot_settings.get('kot_line_height', '1.3'),
        kot_text_color=kot_settings.get('kot_text_color', '#000'),
        kot_header_align=kot_settings.get('kot_header_align', 'center'),
        kot_header_spacing=kot_settings.get('kot_header_spacing', '10px'),
        kot_header_border=kot_settings.get('kot_header_border', '1px solid #000'),
        kot_logo_size=kot_settings.get('kot_logo_size', '80px'),
        kot_logo_display='display: block;' if kot_settings.get('kot_show_company_logo', 'true') == 'true' else 'display: none;',
        kot_order_display='display: block;' if kot_settings.get('kot_show_order_date', 'true') == 'true' else 'display: none;',
        kot_table_font_size=kot_settings.get('kot_table_font_size', '14px'),
        kot_table_weight=kot_settings.get('kot_table_weight', 'bold'),
        kot_table_color=kot_settings.get('kot_table_color', '#000'),
        kot_table_display='display: block;' if kot_settings.get('kot_table_number_style', 'bold') != 'hidden' else 'display: none;',
        kot_item_border=kot_settings.get('kot_item_border', '1px solid #ccc'),
        kot_item_bg=kot_settings.get('kot_item_bg', '#f9f9f9'),
        kot_priority_display='display: inline;' if kot_settings.get('kot_priority_display', 'true') == 'true' else 'display: none;',
        kot_priority_color=kot_settings.get('kot_priority_color', '#ff0000'),
        kot_instructions_display='display: block;' if kot_settings.get('kot_show_special_instructions', 'true') == 'true' else 'display: none;',
        kot_instructions_color=kot_settings.get('kot_instructions_color', '#666'),
        kot_footer_align=kot_settings.get('kot_footer_align', 'center'),
        kot_footer_border=kot_settings.get('kot_footer_border', '1px solid #000'),
        kot_cutting_line_display='display: block;' if kot_settings.get('kot_cutting_line', 'true') == 'true' else 'display: none;',
        
        # Custom print CSS from template settings
        custom_print_css=print_template_settings.get('print_template_custom_css', '')
    )
    
    return css_content