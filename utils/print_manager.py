"""
Print Manager for Restaurant POS System
Handles thermal printer operations and print history tracking
"""

import os
import json
from datetime import datetime
from flask import current_app, request
from flask_login import current_user
from models import db, Settings
from models.print_history import PrintHistory

class PrintManager:
    """Manages print operations for thermal printers"""
    
    def __init__(self):
        # Initialize with empty dicts - will be loaded lazily
        self.settings = {}
        self.receipt_settings = {}
        self.invoice_settings = {}
        self.kot_settings = {}
        self.thermal_settings = {}
        self.multi_printer_settings = {}
        self.print_quality_settings = {}
        self.print_layout_settings = {}
        self.print_branding_settings = {}
        
        # Legacy compatibility (will be loaded lazily)
        self.default_printer = 'Default'
        self.paper_width = '80mm'
        self.auto_print = True
        
        # Enhanced printer configuration (will be loaded lazily)
        self.printer_profiles = {}
        self.print_templates = {}
    
    def _load_printer_profiles(self):
        """Load printer profiles from settings"""
        profiles = {}
        
        # Default printer profiles
        profiles['default'] = {
            'name': 'Default Thermal Printer',
            'type': 'thermal',
            'paper_width': self.thermal_settings.get('thermal_paper_width', '80mm'),
            'font_family': self.thermal_settings.get('thermal_font_family', 'monospace'),
            'font_size': self.thermal_settings.get('thermal_font_size', '12px'),
            'print_density': self.thermal_settings.get('thermal_print_density', 'medium'),
            'print_speed': self.thermal_settings.get('thermal_print_speed', 'normal')
        }
        
        # Load custom printer profiles if enabled
        if self.multi_printer_settings.get('printer_profiles_enabled', 'false') == 'true':
            location_mapping = self.multi_printer_settings.get('printer_location_mapping', '')
            if location_mapping:
                try:
                    profiles.update(json.loads(location_mapping))
                except json.JSONDecodeError:
                    pass
        
        return profiles
    
    def _ensure_settings_loaded(self):
        """Ensure all settings are loaded from database"""
        if not self.settings:  # Only load if not already loaded
            try:
                self.settings = Settings.get_all_as_dict()
                self.receipt_settings = Settings.get_receipt_settings()
                self.invoice_settings = Settings.get_invoice_settings()
                self.kot_settings = Settings.get_kot_settings()
                self.thermal_settings = Settings.get_thermal_printer_settings()
                self.multi_printer_settings = Settings.get_multi_printer_settings()
                self.print_quality_settings = Settings.get_print_quality_settings()
                self.print_layout_settings = Settings.get_print_layout_settings()
                self.print_branding_settings = Settings.get_print_branding_settings()
                
                # Load printer profiles and templates
                self.printer_profiles = self._load_printer_profiles()
                self.print_templates = self._load_print_templates()
                
                # Update legacy compatibility variables
                self.default_printer = self.settings.get('thermal_printer_name', 'Default')
                self.paper_width = self.settings.get('paper_width', '80mm')
                self.auto_print = self.settings.get('auto_print_enabled', 'true').lower() == 'true'
            except Exception as e:
                # Fall back to default settings if database access fails
                self.settings = {'thermal_printer_name': 'Default', 'paper_width': '80mm', 'auto_print_enabled': 'true'}
                self.receipt_settings = {}
                self.invoice_settings = {}
                self.kot_settings = {}
                self.thermal_settings = {}
                self.multi_printer_settings = {}
                self.print_quality_settings = {}
                self.print_layout_settings = {}
                self.print_branding_settings = {}
    
    def _load_print_templates(self):
        """Load print templates from settings"""
        templates = {}
        
        # Get template settings
        template_settings = Settings.get_print_template_settings()
        
        # Load custom templates
        templates['receipt'] = {
            'template': template_settings.get('print_template_receipt', 'default_receipt'),
            'css': template_settings.get('print_template_custom_css', ''),
            'variables': template_settings.get('print_template_variables', '{}')
        }
        
        templates['invoice'] = {
            'template': template_settings.get('print_template_invoice', 'default_invoice'),
            'css': template_settings.get('print_template_custom_css', ''),
            'variables': template_settings.get('print_template_variables', '{}')
        }
        
        templates['kot'] = {
            'template': template_settings.get('print_template_kot', 'default_kot'),
            'css': template_settings.get('print_template_custom_css', ''),
            'variables': template_settings.get('print_template_variables', '{}')
        }
        
        return templates
    
    def get_printer_for_task(self, task_type):
        """Get appropriate printer for specific task type"""
        self._ensure_settings_loaded()
        printer_mapping = {
            'receipt': self.multi_printer_settings.get('receipt_printer_name'),
            'bill': self.multi_printer_settings.get('bill_printer_name'),
            'invoice': self.multi_printer_settings.get('invoice_printer_name'),
            'kot': self.multi_printer_settings.get('kot_printer_name'),
            'kitchen': self.multi_printer_settings.get('kitchen_printer_name'),
            'bar': self.multi_printer_settings.get('bar_printer_name'),
            'report': self.multi_printer_settings.get('report_printer_name')
        }
        
        printer_name = printer_mapping.get(task_type)
        if not printer_name and self.multi_printer_settings.get('printer_auto_selection', 'true') == 'true':
            # Auto-select based on task type
            if task_type in ['receipt', 'bill']:
                printer_name = self.multi_printer_settings.get('receipt_printer_name') or self.default_printer
            elif task_type in ['kot', 'kitchen', 'bar']:
                printer_name = self.multi_printer_settings.get('kot_printer_name') or self.default_printer
            elif task_type == 'invoice':
                printer_name = self.multi_printer_settings.get('invoice_printer_name') or self.default_printer
            else:
                printer_name = self.default_printer
        
        return printer_name or self.default_printer
    
    def apply_print_customization(self, print_type, content_data):
        """Apply comprehensive print customization to content"""
        self._ensure_settings_loaded()
        customized_content = content_data.copy()
        
        # Get appropriate settings for print type
        if print_type == 'receipt':
            settings = self.receipt_settings
            template = self.print_templates.get('receipt', {})
        elif print_type == 'invoice':
            settings = self.invoice_settings
            template = self.print_templates.get('invoice', {})
        elif print_type == 'kot':
            settings = self.kot_settings
            template = self.print_templates.get('kot', {})
        else:
            settings = self.print_branding_settings
            template = {}
        
        # Apply branding customizations
        customized_content['customization'] = {
            'show_logo': settings.get(f'{print_type}_show_company_logo', 'true') == 'true',
            'show_company_info': settings.get(f'{print_type}_show_company_info', 'true') == 'true',
            'show_gst_number': settings.get(f'{print_type}_show_gst_number', 'true') == 'true',
            'show_order_date': settings.get(f'{print_type}_show_order_date', 'true') == 'true',
            'show_order_time': settings.get(f'{print_type}_show_order_time', 'true') == 'true',
            'show_customer_name': settings.get(f'{print_type}_show_customer_name', 'true') == 'true',
            'show_payment_methods': settings.get(f'{print_type}_show_payment_methods', 'true') == 'true',
            'show_discounts': settings.get(f'{print_type}_show_discounts', 'true') == 'true',
            'show_tax_breakdown': settings.get(f'{print_type}_show_tax_breakdown', 'true') == 'true',
            'font_size': settings.get(f'{print_type}_font_size', '12px'),
            'header_color': settings.get(f'{print_type}_header_color', '#000000'),
            'logo_size': settings.get(f'{print_type}_logo_size', '100px'),
            'layout_style': settings.get(f'{print_type}_layout_style', 'default'),
            'cutting_line': settings.get(f'{print_type}_cutting_line', 'true') == 'true',
            'barcode_enabled': settings.get(f'{print_type}_barcode_enabled', 'false') == 'true',
            'qr_code_enabled': settings.get(f'{print_type}_qr_code_enabled', 'false') == 'true'
        }
        
        # Apply thermal printer optimizations
        if self.thermal_settings.get('thermal_print_logo', 'true') == 'true':
            customized_content['customization']['thermal_logo'] = {
                'size': self.thermal_settings.get('thermal_logo_size', '80px'),
                'position': self.thermal_settings.get('thermal_logo_position', 'center')
            }
        
        # Apply print quality settings
        customized_content['customization']['print_quality'] = {
            'dpi': self.print_quality_settings.get('print_quality_dpi', '203'),
            'contrast': self.print_quality_settings.get('print_contrast', 'medium'),
            'speed': self.print_quality_settings.get('print_speed_normal', 'normal'),
            'color_mode': self.print_quality_settings.get('print_color_mode', 'monochrome')
        }
        
        # Apply layout settings
        customized_content['customization']['layout'] = {
            'orientation': self.print_layout_settings.get('print_page_orientation', 'portrait'),
            'margins': self.print_layout_settings.get('print_margins', '10mm'),
            'alignment': self.print_layout_settings.get('print_alignment', 'center'),
            'border': self.print_layout_settings.get('print_border_enabled', 'false') == 'true'
        }
        
        return customized_content
    
    def generate_custom_css(self, print_type):
        """Generate custom CSS for specific print type"""
        self._ensure_settings_loaded()
        css_rules = []
        
        # Base CSS for print type
        if print_type == 'receipt':
            settings = self.receipt_settings
        elif print_type == 'invoice':
            settings = self.invoice_settings
        elif print_type == 'kot':
            settings = self.kot_settings
        else:
            settings = self.print_branding_settings
        
        # Generate font settings
        font_size = settings.get(f'{print_type}_font_size', '12px')
        font_family = self.thermal_settings.get('thermal_font_family', 'monospace')
        css_rules.append(f'.{print_type}-container {{ font-size: {font_size}; font-family: {font_family}; }}')
        
        # Generate color settings
        header_color = settings.get(f'{print_type}_header_color', '#000000')
        css_rules.append(f'.{print_type}-header {{ color: {header_color}; }}')
        
        # Generate logo settings
        if settings.get(f'{print_type}_show_company_logo', 'true') == 'true':
            logo_size = settings.get(f'{print_type}_logo_size', '100px')
            css_rules.append(f'.{print_type}-logo {{ max-width: {logo_size}; max-height: {logo_size}; }}')
        
        # Generate layout settings
        layout_style = settings.get(f'{print_type}_layout_style', 'default')
        if layout_style == 'compact':
            css_rules.append(f'.{print_type}-container {{ line-height: 1.2; }}')
            css_rules.append(f'.{print_type}-item {{ margin-bottom: 3px; }}')
        elif layout_style == 'spacious':
            css_rules.append(f'.{print_type}-container {{ line-height: 1.6; }}')
            css_rules.append(f'.{print_type}-item {{ margin-bottom: 8px; }}')
        
        # Generate thermal printer specific CSS
        paper_width = self.thermal_settings.get('thermal_paper_width', '80mm')
        if paper_width == '58mm':
            css_rules.append('@media print { .thermal-container { width: 58mm; } }')
        elif paper_width == '80mm':
            css_rules.append('@media print { .thermal-container { width: 80mm; } }')
        
        # Apply print quality settings
        dpi = self.print_quality_settings.get('print_quality_dpi', '203')
        if dpi == '300':
            css_rules.append('@media print { * { print-color-adjust: exact; } }')
        
        return '\n'.join(css_rules)
    
    def _get_printer_settings_snapshot(self):
        """Get snapshot of current printer settings for logging"""
        return {
            'thermal_settings': self.thermal_settings,
            'multi_printer_settings': self.multi_printer_settings,
            'receipt_settings': self.receipt_settings,
            'invoice_settings': self.invoice_settings,
            'kot_settings': self.kot_settings,
            'print_quality_settings': self.print_quality_settings,
            'print_layout_settings': self.print_layout_settings,
            'print_branding_settings': self.print_branding_settings
        }
        
    def print_bill(self, order_id, copies=1, printer_name=None):
        """Print bill for order with comprehensive customization"""
        self._ensure_settings_loaded()
        try:
            from models import Order
            
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            # Get appropriate printer for bill
            printer_name = printer_name or self.get_printer_for_task('bill')
            
            # Prepare order data
            order_data = order.to_dict()
            order_data['items'] = []
            order_data['payments'] = []
            
            for item in order.items:
                order_data['items'].append({
                    'id': item.id,
                    'menu_item_id': item.menu_item_id,
                    'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'total': float(item.price * item.quantity),
                    'special_instructions': item.special_instructions,
                    'modifications': getattr(item, 'modifications', [])
                })
            
            for payment in order.payments:
                order_data['payments'].append({
                    'id': payment.id,
                    'payment_mode': payment.payment_mode,
                    'amount': float(payment.amount),
                    'created_at': payment.created_at.isoformat(),
                    'reference_number': payment.reference_number
                })
            
            # Apply comprehensive print customization
            customized_order_data = self.apply_print_customization('receipt', order_data)
            
            # Track print operation
            print_record = PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='bill',
                print_method='thermal',
                copies=copies,
                printer_name=printer_name,
                success=True,
                printer_settings=self._get_printer_settings_snapshot()
            )
            
            # Return print URL with customization data
            return {
                'success': True,
                'print_url': f'/orders/print/{order_id}?auto_print=true&customized=true',
                'message': f'Customized bill print job created for order {order.order_number}',
                'print_record_id': print_record.id if print_record else None,
                'customization_applied': True,
                'printer_used': printer_name,
                'customization_summary': {
                    'template_used': 'custom_receipt',
                    'logo_applied': customized_order_data['customization']['show_logo'],
                    'branding_applied': customized_order_data['customization']['show_company_info'],
                    'thermal_optimized': self.thermal_settings.get('thermal_print_logo', 'true') == 'true'
                }
            }
            
        except Exception as e:
            # Log failed print
            PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='bill',
                print_method='thermal',
                copies=copies,
                printer_name=printer_name or self.default_printer,
                success=False,
                error_message=str(e),
                printer_settings=self._get_printer_settings_snapshot()
            )
            
            return {'success': False, 'message': f'Print failed: {str(e)}'}
    
    def print_kot(self, order_id, copies=1, printer_name=None):
        """Print KOT for order with comprehensive customization"""
        self._ensure_settings_loaded()
        try:
            from models import Order
            
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            # Get appropriate printer for KOT
            printer_name = printer_name or self.get_printer_for_task('kot')
            
            # Prepare order data
            order_data = order.to_dict()
            order_data['items'] = []
            
            for item in order.items:
                order_data['items'].append({
                    'id': item.id,
                    'menu_item_id': item.menu_item_id,
                    'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'special_instructions': item.special_instructions,
                    'status': getattr(item, 'status', 'Pending'),
                    'modifications': getattr(item, 'modifications', [])
                })
            
            # Check if any items have modifications
            has_modifiers = any(item.get('modifications') for item in order_data['items'])
            order_data['has_modifiers'] = has_modifiers
            
            # Apply comprehensive print customization for KOT
            customized_order_data = self.apply_print_customization('kot', order_data)
            
            # Track print operation
            print_record = PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='kot',
                print_method='thermal',
                copies=copies,
                printer_name=printer_name,
                success=True,
                printer_settings=self._get_printer_settings_snapshot()
            )
            
            # Return print URL with customization data
            return {
                'success': True,
                'print_url': f'/kot/print/{order_id}?auto_print=true&customized=true',
                'message': f'Customized KOT print job created for order {order.order_number}',
                'print_record_id': print_record.id if print_record else None,
                'customization_applied': True,
                'printer_used': printer_name,
                'customization_summary': {
                    'template_used': 'custom_kot',
                    'logo_applied': customized_order_data['customization']['show_logo'],
                    'branding_applied': customized_order_data['customization']['show_company_info'],
                    'thermal_optimized': self.thermal_settings.get('thermal_print_logo', 'true') == 'true',
                    'special_instructions': customized_order_data['customization'].get('show_special_instructions', True),
                    'priority_display': customized_order_data['customization'].get('kot_priority_display', True)
                }
            }
            
        except Exception as e:
            # Log failed print
            PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='kot',
                print_method='thermal',
                copies=copies,
                printer_name=printer_name or self.default_printer,
                success=False,
                error_message=str(e),
                printer_settings=self._get_printer_settings_snapshot()
            )
            
            return {'success': False, 'message': f'Print failed: {str(e)}'}
    
    def print_invoice_pdf(self, order_id, copies=1):
        """Generate and print invoice PDF"""
        self._ensure_settings_loaded()
        try:
            from models import Order
            from utils.pdf_invoice_generator import generate_invoice_pdf
            
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            # Prepare order data
            order_data = order.to_dict()
            order_data['items'] = []
            order_data['payments'] = []
            
            for item in order.items:
                order_data['items'].append({
                    'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'total': float(item.price * item.quantity),
                    'special_instructions': item.special_instructions
                })
            
            for payment in order.payments:
                order_data['payments'].append({
                    'payment_mode': payment.payment_mode,
                    'amount': float(payment.amount),
                    'created_at': payment.created_at.isoformat(),
                    'reference_number': payment.reference_number
                })
            
            # Apply comprehensive print customization for invoice
            customized_order_data = self.apply_print_customization('invoice', order_data)
            
            # Track print operation
            print_record = PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='invoice',
                print_method='pdf',
                copies=copies,
                success=True,
                printer_settings=self._get_printer_settings_snapshot()
            )
            
            # Generate PDF
            pdf_path = generate_invoice_pdf(order_data, self.settings)
            
            return {
                'success': True,
                'pdf_url': f'/reports/invoice/{order_id}',
                'pdf_path': pdf_path,
                'message': f'Invoice PDF generated for order {order.order_number}',
                'print_record_id': print_record.id if print_record else None
            }
            
        except Exception as e:
            # Log failed print
            PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='invoice',
                print_method='pdf',
                copies=copies,
                success=False,
                error_message=str(e)
            )
            
            return {'success': False, 'message': f'PDF generation failed: {str(e)}'}
    
    def get_printer_status(self):
        """Check thermal printer status"""
        self._ensure_settings_loaded()
        try:
            # This would interface with actual printer drivers
            # For now, return a simulated status
            return {
                'online': True,
                'paper_width': self.paper_width,
                'printer_name': self.default_printer,
                'status': 'Ready',
                'last_check': datetime.now().isoformat(),
                'thermal_settings': {
                    'density': self.thermal_settings.get('thermal_print_density', 'medium'),
                    'speed': self.thermal_settings.get('thermal_print_speed', 'normal'),
                    'font_family': self.thermal_settings.get('thermal_font_family', 'monospace'),
                    'font_size': self.thermal_settings.get('thermal_font_size', '12px'),
                    'paper_width': self.thermal_settings.get('thermal_paper_width', '80mm')
                }
            }
        except Exception as e:
            return {
                'online': False,
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def configure_printer(self, printer_config):
        """Configure thermal printer settings"""
        self._ensure_settings_loaded()
        try:
            # Update settings
            for key, value in printer_config.items():
                if hasattr(Settings, 'set'):
                    Settings.set(key, value)
                else:
                    # Direct database update if Settings.set is not available
                    self._update_setting(key, value)
            
            # Reset the loaded flag to force reload of all settings
            self.settings = {}
            
            return {'success': True, 'message': 'Printer configuration updated'}
            
        except Exception as e:
            return {'success': False, 'message': f'Configuration failed: {str(e)}'}
    
    def _update_setting(self, key, value):
        """Helper method to update settings directly"""
        from models import SettingsModel
        setting = SettingsModel.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = SettingsModel(key=key, value=str(value))
            db.session.add(setting)
        db.session.commit()
    
    def get_print_history(self, filters=None):
        """Get print history with optional filters"""
        try:
            order_id = filters.get('order_id') if filters else None
            user_id = filters.get('user_id') if filters else None
            print_type = filters.get('print_type') if filters else None
            limit = filters.get('limit', 50) if filters else 50
            
            history = PrintHistory.get_print_history(
                order_id=order_id,
                user_id=user_id,
                print_type=print_type,
                limit=limit
            )
            
            return {
                'success': True,
                'history': [record.to_dict() for record in history]
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to get history: {str(e)}'}
    
    def get_print_statistics(self, days=30):
        """Get print statistics"""
        try:
            stats = PrintHistory.get_print_statistics(days=days)
            return {'success': True, 'statistics': stats}
        except Exception as e:
            return {'success': False, 'message': f'Failed to get statistics: {str(e)}'}

# Global print manager instance (created lazily)
_print_manager_instance = None

def get_print_manager():
    """Get the global print manager instance"""
    global _print_manager_instance
    if _print_manager_instance is None:
        _print_manager_instance = PrintManager()
    return _print_manager_instance

# Helper functions for route handlers
def print_order_bill(order_id, copies=1, printer_name=None):
    """Helper function to print order bill"""
    return get_print_manager().print_bill(order_id, copies, printer_name)

def print_order_kot(order_id, copies=1, printer_name=None):
    """Helper function to print order KOT"""
    return get_print_manager().print_kot(order_id, copies, printer_name)

def generate_order_invoice_pdf(order_id, copies=1):
    """Helper function to generate order invoice PDF"""
    return get_print_manager().print_invoice_pdf(order_id, copies)

def get_printer_status():
    """Helper function to get printer status"""
    return get_print_manager().get_printer_status()