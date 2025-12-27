from datetime import datetime
from utils.encryption import get_encryption_manager
from . import db

class Settings(db.Model):
    """Settings model for application configuration"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, default=False)  # Whether setting is accessible to non-admin users
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, key, value=None, description=None, is_public=False):
        self.key = key
        self.value = self._encrypt_value_if_needed(key, value) if value else None
        self.description = description
        self.is_public = is_public
    
    def to_dict(self):
        """Convert setting to dictionary"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self._decrypt_value_if_needed(self.key, self.value),
            'description': self.description,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get(key, default=None):
        """Get setting value by key"""
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            return setting._decrypt_value_if_needed(key, setting.value)
        return default
    
    @staticmethod
    def get_all():
        """Get all settings as dictionary"""
        settings = Settings.query.all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_all_as_dict():
        """Get all settings as dictionary"""
        return Settings.get_all()
    
    @staticmethod
    def get_public():
        """Get all public settings as dictionary"""
        settings = Settings.query.filter_by(is_public=True).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def set(key, value, description=None, is_public=None):
        """Set setting value"""
        setting = Settings.query.filter_by(key=key).first()
        
        if setting:
            setting.value = setting._encrypt_value_if_needed(key, value) if value else None
            if description is not None:
                setting.description = description
            if is_public is not None:
                setting.is_public = is_public
            setting.updated_at = datetime.utcnow()
        else:
            setting = Settings(key, value, description, is_public)
            db.session.add(setting)
        
        db.session.commit()
        return setting
    
    @staticmethod
    def create_defaults():
        """Create default settings"""
        default_settings = [
            ('restaurant_name', 'Restaurant POS', 'Restaurant name for receipts and display', True),
            ('restaurant_address', '', 'Restaurant address for receipts', True),
            ('restaurant_phone', '', 'Restaurant phone number', True),
            ('restaurant_email', '', 'Restaurant email address', True),
            ('gst_number', '', 'GST registration number', True),
            ('currency_symbol', '₹', 'Currency symbol', True),
            ('decimal_places', '2', 'Number of decimal places for amounts', True),
            ('tax_rate', '5', 'Default tax rate percentage', False),
            ('cgst_rate', '2.5', 'CGST rate percentage', False),
            ('sgst_rate', '2.5', 'SGST rate percentage', False),
            ('enable_printing', 'true', 'Enable receipt printing', False),
            ('printer_name', '', 'Default printer name', False),
            ('enable_notifications', 'true', 'Enable desktop notifications', False),
            ('auto_backup', 'true', 'Enable automatic backup', False),
            ('backup_interval', '24', 'Backup interval in hours', False),
            ('low_stock_threshold', '10', 'Low stock alert threshold', False),
            ('enable_sms', 'false', 'Enable SMS notifications', False),
            ('sms_api_key', '', 'SMS API key', False),
            ('session_timeout', '8', 'Session timeout in hours', False),
            ('max_order_items', '50', 'Maximum items per order', True),
            ('enable_discount', 'true', 'Enable discount functionality', False),
            ('max_discount_percentage', '50', 'Maximum discount percentage', False),
            ('enable_delivery', 'false', 'Enable delivery orders', False),
            ('delivery_charge', '0', 'Default delivery charge', True),
            ('min_delivery_amount', '100', 'Minimum amount for free delivery', True),
            
            # Footer settings
            ('footer_enabled', 'true', 'Enable footer on receipts and documents', True),
            ('footer_template', 'default', 'Footer template style (default, minimal, detailed)', True),
            ('footer_show_user_name', 'true', 'Show user name in footer', True),
            ('footer_show_receipt_info', 'true', 'Show receipt number and date in footer', True),
            ('footer_show_business_info', 'true', 'Show business info in footer', True),
            ('footer_custom_text', 'Thank you for your business!', 'Custom footer text', True),
            ('footer_font_size', '10', 'Footer font size', False),
            ('footer_alignment', 'center', 'Footer text alignment (left, center, right)', True),
            ('footer_show_logo', 'false', 'Show company logo in footer', False),
            ('footer_logo_path', '', 'Path to company logo image', False),
            ('footer_different_receipts', 'false', 'Use different footer for receipts vs invoices', False),
            ('footer_invoice_template', 'default', 'Footer template for invoices', True),
            ('footer_receipt_template', 'default', 'Footer template for receipts', True),
            ('footer_multiline', 'false', 'Enable multiline footer text', False),
            ('footer_line1', '', 'Footer line 1 text', True),
            ('footer_line2', '', 'Footer line 2 text', True),
            ('footer_line3', '', 'Footer line 3 text', True),
        ]
        
        for key, value, description, is_public in default_settings:
            if not Settings.query.filter_by(key=key).first():
                setting = Settings(key, value, description, is_public)
                db.session.add(setting)
        
        db.session.commit()
    
    @staticmethod
    def get_restaurant_info():
        """Get restaurant information settings"""
        keys = [
            'restaurant_name', 'restaurant_address', 'restaurant_phone',
            'restaurant_email', 'gst_number', 'currency_symbol'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_tax_settings():
        """Get tax-related settings"""
        keys = ['tax_rate', 'cgst_rate', 'sgst_rate']
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_printer_settings():
        """Get printer-related settings"""
        keys = ['enable_printing', 'printer_name']
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_backup_settings():
        """Get backup-related settings"""
        keys = ['auto_backup', 'backup_interval']
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_footer_settings():
        """Get footer-related settings"""
        keys = [
            'footer_enabled', 'footer_template', 'footer_show_user_name', 'footer_show_receipt_info',
            'footer_show_business_info', 'footer_custom_text', 'footer_font_size', 'footer_alignment',
            'footer_show_logo', 'footer_logo_path', 'footer_different_receipts', 'footer_invoice_template',
            'footer_receipt_template', 'footer_multiline', 'footer_line1', 'footer_line2', 'footer_line3'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_white_label_settings():
        """Get all white label related settings"""
        white_label_keys = [
            # Company Information
            'company_name', 'company_full_name', 'company_short_name', 'company_tagline',
            'company_address_line1', 'company_address_line2', 'company_city', 'company_state',
            'company_country', 'company_postal_code', 'company_phone_primary', 'company_phone_secondary',
            'company_email_primary', 'company_email_secondary', 'company_website',
            'company_registration_number', 'company_tax_id', 'company_legal_entity', 'company_year_established',
            
            # Visual Branding
            'logo_main_path', 'logo_header_path', 'logo_footer_path', 'logo_favicon_path',
            'logo_invoice_path', 'logo_email_path', 'logo_login_path',
            'logo_show_in_header', 'logo_show_in_footer', 'logo_show_in_login', 'logo_show_in_emails', 'logo_show_in_invoices',
            'logo_height_header', 'logo_height_footer', 'logo_height_login',
            'brand_primary_color', 'brand_secondary_color', 'brand_accent_color', 'brand_success_color',
            'brand_warning_color', 'brand_danger_color', 'brand_info_color', 'brand_light_color', 'brand_dark_color',
            'bg_primary_color', 'bg_secondary_color', 'bg_header_color', 'bg_footer_color',
            'text_primary_color', 'text_secondary_color', 'text_light_color', 'text_header_color', 'text_footer_color',
            
            # Typography
            'font_primary_family', 'font_secondary_family', 'font_header_family', 'font_body_family',
            'font_size_base', 'font_size_small', 'font_size_large', 'font_size_h1', 'font_size_h2', 'font_size_h3',
            'font_size_h4', 'font_size_h5', 'font_size_h6',
            'font_weight_light', 'font_weight_normal', 'font_weight_medium', 'font_weight_semibold', 'font_weight_bold',
            'line_height_base', 'line_height_heading',
            
            # Content
            'welcome_message_dashboard', 'welcome_message_login', 'welcome_message_registration',
            'custom_header_text', 'custom_footer_text', 'custom_about_text', 'custom_contact_text',
            'custom_css_enabled', 'custom_css_content', 'custom_css_priority',
            
            # Email
            'email_header_logo', 'email_footer_logo', 'email_signature_text', 'email_contact_info',
            'email_primary_color', 'email_background_color', 'email_text_color',
            'email_template_style', 'email_show_social_links', 'email_social_links',
            
            # Enhanced Print Settings (Comprehensive Printer Customization)
            # Receipt Settings
            'receipt_logo_path', 'receipt_header_color', 'receipt_footer_text', 'receipt_custom_message',
            'receipt_header_enabled', 'receipt_footer_enabled', 'receipt_logo_size', 'receipt_font_size',
            'receipt_layout_style', 'receipt_header_template', 'receipt_footer_template',
            'receipt_show_company_logo', 'receipt_show_company_info', 'receipt_show_gst_number',
            'receipt_show_order_date', 'receipt_show_order_time', 'receipt_show_customer_name',
            'receipt_show_payment_methods', 'receipt_show_discounts', 'receipt_show_tax_breakdown',
            'receipt_cutting_line', 'receipt_barcode_enabled', 'receipt_qr_code_enabled',
            
            # Invoice Settings
            'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
            'invoice_header_enabled', 'invoice_footer_enabled', 'invoice_logo_size', 'invoice_font_size',
            'invoice_layout_style', 'invoice_header_template', 'invoice_footer_template',
            'invoice_show_company_logo', 'invoice_show_company_info', 'invoice_show_gst_number',
            'invoice_show_order_date', 'invoice_show_order_time', 'invoice_show_customer_name',
            'invoice_show_payment_methods', 'invoice_show_discounts', 'invoice_show_tax_breakdown',
            'invoice_billing_address', 'invoice_shipping_address', 'invoice_show_bank_details',
            'invoice_terms_enabled', 'invoice_notes_enabled', 'invoice_show_signature',
            
            # KOT Settings
            'kot_logo_path', 'kot_header_color', 'kot_footer_text', 'kot_custom_message',
            'kot_header_enabled', 'kot_footer_enabled', 'kot_logo_size', 'kot_font_size',
            'kot_layout_style', 'kot_header_template', 'kot_footer_template',
            'kot_show_company_logo', 'kot_show_company_info', 'kot_table_number_style',
            'kot_order_type_display', 'kot_priority_display', 'kot_show_special_instructions',
            'kot_show_cooking_time', 'kot_cutting_line', 'kot_order_separation',
            
            # Thermal Printer Settings
            'thermal_printer_name', 'thermal_paper_width', 'thermal_print_density', 'thermal_print_speed',
            'thermal_font_family', 'thermal_font_size', 'thermal_font_weight', 'thermal_line_spacing',
            'thermal_margin_top', 'thermal_margin_bottom', 'thermal_margin_left', 'thermal_margin_right',
            'thermal_header_spacing', 'thermal_item_spacing', 'thermal_footer_spacing',
            'thermal_print_logo', 'thermal_logo_size', 'thermal_logo_position',
            'thermal_cut_paper', 'thermal_partial_cut', 'thermal_beep_enabled', 'thermal_feed_lines',
            
            # Multi-Printer Settings
            'default_printer_name', 'printer_profiles_enabled', 'printer_location_mapping',
            'bill_printer_name', 'kot_printer_name', 'invoice_printer_name', 'report_printer_name',
            'kitchen_printer_name', 'bar_printer_name', 'receipt_printer_name',
            'printer_auto_selection', 'printer_fallback_enabled', 'printer_priority_order',
            
            # Print Quality Settings
            'print_quality_dpi', 'print_contrast', 'print_brightness', 'print_speed_draft',
            'print_speed_normal', 'print_speed_high', 'print_dithering', 'print_color_mode',
            'print_media_type', 'print_finishing', 'print_collation', 'print_copies_default',
            
            # Print Layout Settings
            'print_page_orientation', 'print_page_size', 'print_margins', 'print_scaling',
            'print_headers_footers', 'print_page_numbers', 'print_date_time', 'print_logo_watermark',
            'print_border_enabled', 'print_shadow_enabled', 'print_alignment', 'print_wrapping',
            
            # Print Templates
            'print_template_receipt', 'print_template_invoice', 'print_template_kot',
            'print_template_custom_css', 'print_template_javascript', 'print_template_variables',
            'print_dynamic_content', 'print_conditional_content', 'print_loop_content',
            
            # Print Branding
            'print_header_enabled', 'print_footer_enabled', 'print_logo_size', 'print_font_size',
            'print_brand_colors', 'print_company_tagline', 'print_legal_disclaimer',
            'print_warranty_info', 'print_return_policy', 'print_contact_info',
            
            # Legacy Print Settings (for compatibility)
            'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
            'print_header_enabled', 'print_footer_enabled', 'print_logo_size', 'print_font_size',
            
            # UI
            'login_background_image', 'login_background_color', 'login_card_background',
            'login_title', 'login_subtitle', 'login_features_enabled',
            'dashboard_welcome_text', 'dashboard_stats_enabled', 'dashboard_quick_actions_enabled',
            'nav_style', 'nav_color_scheme', 'nav_show_branding',
            'theme_preset', 'theme_custom_enabled'
        ]
        settings = Settings.query.filter(Settings.key.in_(white_label_keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_company_info():
        """Get company information for white labeling"""
        keys = [
            'company_name', 'company_full_name', 'company_short_name', 'company_tagline',
            'company_address_line1', 'company_address_line2', 'company_city', 'company_state',
            'company_country', 'company_postal_code', 'company_phone_primary', 'company_phone_secondary',
            'company_email_primary', 'company_email_secondary', 'company_website',
            'company_registration_number', 'company_tax_id', 'company_legal_entity', 'company_year_established'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_branding_info():
        """Get branding information for white labeling"""
        keys = [
            'logo_main_path', 'logo_header_path', 'logo_footer_path', 'logo_favicon_path',
            'logo_invoice_path', 'logo_email_path', 'logo_login_path',
            'brand_primary_color', 'brand_secondary_color', 'brand_accent_color',
            'bg_primary_color', 'bg_secondary_color', 'bg_header_color', 'bg_footer_color',
            'text_primary_color', 'text_secondary_color', 'text_light_color', 'text_header_color', 'text_footer_color',
            'font_primary_family', 'font_secondary_family', 'font_header_family', 'font_body_family'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_logo_settings():
        """Get logo-related settings"""
        keys = [
            'logo_main_path', 'logo_header_path', 'logo_footer_path', 'logo_favicon_path',
            'logo_invoice_path', 'logo_email_path', 'logo_login_path',
            'logo_show_in_header', 'logo_show_in_footer', 'logo_show_in_login', 'logo_show_in_emails', 'logo_show_in_invoices',
            'logo_height_header', 'logo_height_footer', 'logo_height_login'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_color_scheme():
        """Get color scheme settings for white labeling"""
        keys = [
            'brand_primary_color', 'brand_secondary_color', 'brand_accent_color', 'brand_success_color',
            'brand_warning_color', 'brand_danger_color', 'brand_info_color', 'brand_light_color', 'brand_dark_color',
            'bg_primary_color', 'bg_secondary_color', 'bg_header_color', 'bg_footer_color',
            'text_primary_color', 'text_secondary_color', 'text_light_color', 'text_header_color', 'text_footer_color',
            'email_primary_color', 'email_background_color', 'email_text_color',
            'invoice_header_color', 'receipt_header_color'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_typography_settings():
        """Get typography settings for white labeling"""
        keys = [
            'font_primary_family', 'font_secondary_family', 'font_header_family', 'font_body_family',
            'font_size_base', 'font_size_small', 'font_size_large', 'font_size_h1', 'font_size_h2', 'font_size_h3',
            'font_size_h4', 'font_size_h5', 'font_size_h6',
            'font_weight_light', 'font_weight_normal', 'font_weight_medium', 'font_weight_semibold', 'font_weight_bold',
            'line_height_base', 'line_height_heading',
            'print_font_size'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_ui_customization_settings():
        """Get UI customization settings"""
        keys = [
            'login_background_image', 'login_background_color', 'login_card_background',
            'login_title', 'login_subtitle', 'login_features_enabled',
            'dashboard_welcome_text', 'dashboard_stats_enabled', 'dashboard_quick_actions_enabled',
            'nav_style', 'nav_color_scheme', 'nav_show_branding',
            'theme_preset', 'theme_custom_enabled'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_email_branding_settings():
        """Get email branding settings"""
        keys = [
            'email_header_logo', 'email_footer_logo', 'email_signature_text', 'email_contact_info',
            'email_primary_color', 'email_background_color', 'email_text_color',
            'email_template_style', 'email_show_social_links', 'email_social_links'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_print_branding_settings():
        """Get print branding settings"""
        keys = [
            'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
            'receipt_logo_path', 'receipt_header_color', 'receipt_footer_text', 'receipt_custom_message',
            'print_header_enabled', 'print_footer_enabled', 'print_logo_size', 'print_font_size'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_custom_content_settings():
        """Get custom content settings"""
        keys = [
            'welcome_message_dashboard', 'welcome_message_login', 'welcome_message_registration',
            'custom_header_text', 'custom_footer_text', 'custom_about_text', 'custom_contact_text',
            'custom_css_enabled', 'custom_css_content', 'custom_css_priority'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_receipt_settings():
        """Get comprehensive receipt settings"""
        keys = [
            'receipt_logo_path', 'receipt_header_color', 'receipt_footer_text', 'receipt_custom_message',
            'receipt_header_enabled', 'receipt_footer_enabled', 'receipt_logo_size', 'receipt_font_size',
            'receipt_layout_style', 'receipt_header_template', 'receipt_footer_template',
            'receipt_show_company_logo', 'receipt_show_company_info', 'receipt_show_gst_number',
            'receipt_show_order_date', 'receipt_show_order_time', 'receipt_show_customer_name',
            'receipt_show_payment_methods', 'receipt_show_discounts', 'receipt_show_tax_breakdown',
            'receipt_cutting_line', 'receipt_barcode_enabled', 'receipt_qr_code_enabled'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_invoice_settings():
        """Get comprehensive invoice settings"""
        keys = [
            'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
            'invoice_header_enabled', 'invoice_footer_enabled', 'invoice_logo_size', 'invoice_font_size',
            'invoice_layout_style', 'invoice_header_template', 'invoice_footer_template',
            'invoice_show_company_logo', 'invoice_show_company_info', 'invoice_show_gst_number',
            'invoice_show_order_date', 'invoice_show_order_time', 'invoice_show_customer_name',
            'invoice_show_payment_methods', 'invoice_show_discounts', 'invoice_show_tax_breakdown',
            'invoice_billing_address', 'invoice_shipping_address', 'invoice_show_bank_details',
            'invoice_terms_enabled', 'invoice_notes_enabled', 'invoice_show_signature'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_kot_settings():
        """Get comprehensive KOT (Kitchen Order Ticket) settings"""
        keys = [
            'kot_logo_path', 'kot_header_color', 'kot_footer_text', 'kot_custom_message',
            'kot_header_enabled', 'kot_footer_enabled', 'kot_logo_size', 'kot_font_size',
            'kot_layout_style', 'kot_header_template', 'kot_footer_template',
            'kot_show_company_logo', 'kot_show_company_info', 'kot_table_number_style',
            'kot_order_type_display', 'kot_priority_display', 'kot_show_special_instructions',
            'kot_show_cooking_time', 'kot_cutting_line', 'kot_order_separation'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_thermal_printer_settings():
        """Get comprehensive thermal printer settings"""
        keys = [
            'thermal_printer_name', 'thermal_paper_width', 'thermal_print_density', 'thermal_print_speed',
            'thermal_font_family', 'thermal_font_size', 'thermal_font_weight', 'thermal_line_spacing',
            'thermal_margin_top', 'thermal_margin_bottom', 'thermal_margin_left', 'thermal_margin_right',
            'thermal_header_spacing', 'thermal_item_spacing', 'thermal_footer_spacing',
            'thermal_print_logo', 'thermal_logo_size', 'thermal_logo_position',
            'thermal_cut_paper', 'thermal_partial_cut', 'thermal_beep_enabled', 'thermal_feed_lines'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_multi_printer_settings():
        """Get multi-printer configuration settings"""
        keys = [
            'default_printer_name', 'printer_profiles_enabled', 'printer_location_mapping',
            'bill_printer_name', 'kot_printer_name', 'invoice_printer_name', 'report_printer_name',
            'kitchen_printer_name', 'bar_printer_name', 'receipt_printer_name',
            'printer_auto_selection', 'printer_fallback_enabled', 'printer_priority_order'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_print_quality_settings():
        """Get print quality and formatting settings"""
        keys = [
            'print_quality_dpi', 'print_contrast', 'print_brightness', 'print_speed_draft',
            'print_speed_normal', 'print_speed_high', 'print_dithering', 'print_color_mode',
            'print_media_type', 'print_finishing', 'print_collation', 'print_copies_default'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_print_layout_settings():
        """Get print layout and formatting settings"""
        keys = [
            'print_page_orientation', 'print_page_size', 'print_margins', 'print_scaling',
            'print_headers_footers', 'print_page_numbers', 'print_date_time', 'print_logo_watermark',
            'print_border_enabled', 'print_shadow_enabled', 'print_alignment', 'print_wrapping'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_print_template_settings():
        """Get print template and customization settings"""
        keys = [
            'print_template_receipt', 'print_template_invoice', 'print_template_kot',
            'print_template_custom_css', 'print_template_javascript', 'print_template_variables',
            'print_dynamic_content', 'print_conditional_content', 'print_loop_content'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def get_print_branding_settings():
        """Get print branding and customization settings"""
        keys = [
            'print_header_enabled', 'print_footer_enabled', 'print_logo_size', 'print_font_size',
            'print_brand_colors', 'print_company_tagline', 'print_legal_disclaimer',
            'print_warranty_info', 'print_return_policy', 'print_contact_info',
            'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
            'receipt_logo_path', 'receipt_header_color', 'receipt_footer_text', 'receipt_custom_message',
            'print_header_enabled', 'print_footer_enabled', 'print_logo_size', 'print_font_size'
        ]
        settings = Settings.query.filter(Settings.key.in_(keys)).all()
        return {setting.key: setting._decrypt_value_if_needed(setting.key, setting.value) for setting in settings}
    
    @staticmethod
    def set_white_label_setting(key, value, description=None, is_public=None):
        """Set a white label setting with proper validation"""
        # Validate key is a white label setting
        white_label_keys = [
            'company_name', 'company_full_name', 'company_short_name', 'company_tagline',
            'company_address_line1', 'company_address_line2', 'company_city', 'company_state',
            'company_country', 'company_postal_code', 'company_phone_primary', 'company_phone_secondary',
            'company_email_primary', 'company_email_secondary', 'company_website',
            'company_registration_number', 'company_tax_id', 'company_legal_entity', 'company_year_established',
            'logo_main_path', 'logo_header_path', 'logo_footer_path', 'logo_favicon_path',
            'logo_invoice_path', 'logo_email_path', 'logo_login_path',
            'logo_show_in_header', 'logo_show_in_footer', 'logo_show_in_login', 'logo_show_in_emails', 'logo_show_in_invoices',
            'logo_height_header', 'logo_height_footer', 'logo_height_login',
            'brand_primary_color', 'brand_secondary_color', 'brand_accent_color', 'brand_success_color',
            'brand_warning_color', 'brand_danger_color', 'brand_info_color', 'brand_light_color', 'brand_dark_color',
            'bg_primary_color', 'bg_secondary_color', 'bg_header_color', 'bg_footer_color',
            'text_primary_color', 'text_secondary_color', 'text_light_color', 'text_header_color', 'text_footer_color',
            'font_primary_family', 'font_secondary_family', 'font_header_family', 'font_body_family',
            'font_size_base', 'font_size_small', 'font_size_large', 'font_size_h1', 'font_size_h2', 'font_size_h3',
            'font_size_h4', 'font_size_h5', 'font_size_h6',
            'font_weight_light', 'font_weight_normal', 'font_weight_medium', 'font_weight_semibold', 'font_weight_bold',
            'line_height_base', 'line_height_heading',
            'welcome_message_dashboard', 'welcome_message_login', 'welcome_message_registration',
            'custom_header_text', 'custom_footer_text', 'custom_about_text', 'custom_contact_text',
            'custom_css_enabled', 'custom_css_content', 'custom_css_priority',
            'email_header_logo', 'email_footer_logo', 'email_signature_text', 'email_contact_info',
            'email_primary_color', 'email_background_color', 'email_text_color',
            'email_template_style', 'email_show_social_links', 'email_social_links',
            # Enhanced Print Settings (Comprehensive Printer Customization)
            # Receipt Settings
            'receipt_logo_path', 'receipt_header_color', 'receipt_footer_text', 'receipt_custom_message',
            'receipt_header_enabled', 'receipt_footer_enabled', 'receipt_logo_size', 'receipt_font_size',
            'receipt_layout_style', 'receipt_header_template', 'receipt_footer_template',
            'receipt_show_company_logo', 'receipt_show_company_info', 'receipt_show_gst_number',
            'receipt_show_order_date', 'receipt_show_order_time', 'receipt_show_customer_name',
            'receipt_show_payment_methods', 'receipt_show_discounts', 'receipt_show_tax_breakdown',
            'receipt_cutting_line', 'receipt_barcode_enabled', 'receipt_qr_code_enabled',
            # Invoice Settings
            'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
            'invoice_header_enabled', 'invoice_footer_enabled', 'invoice_logo_size', 'invoice_font_size',
            'invoice_layout_style', 'invoice_header_template', 'invoice_footer_template',
            'invoice_show_company_logo', 'invoice_show_company_info', 'invoice_show_gst_number',
            'invoice_show_order_date', 'invoice_show_order_time', 'invoice_show_customer_name',
            'invoice_show_payment_methods', 'invoice_show_discounts', 'invoice_show_tax_breakdown',
            'invoice_billing_address', 'invoice_shipping_address', 'invoice_show_bank_details',
            'invoice_terms_enabled', 'invoice_notes_enabled', 'invoice_show_signature',
            # KOT Settings
            'kot_logo_path', 'kot_header_color', 'kot_footer_text', 'kot_custom_message',
            'kot_header_enabled', 'kot_footer_enabled', 'kot_logo_size', 'kot_font_size',
            'kot_layout_style', 'kot_header_template', 'kot_footer_template',
            'kot_show_company_logo', 'kot_show_company_info', 'kot_table_number_style',
            'kot_order_type_display', 'kot_priority_display', 'kot_show_special_instructions',
            'kot_show_cooking_time', 'kot_cutting_line', 'kot_order_separation',
            # Thermal Printer Settings
            'thermal_printer_name', 'thermal_paper_width', 'thermal_print_density', 'thermal_print_speed',
            'thermal_font_family', 'thermal_font_size', 'thermal_font_weight', 'thermal_line_spacing',
            'thermal_margin_top', 'thermal_margin_bottom', 'thermal_margin_left', 'thermal_margin_right',
            'thermal_header_spacing', 'thermal_item_spacing', 'thermal_footer_spacing',
            'thermal_print_logo', 'thermal_logo_size', 'thermal_logo_position',
            'thermal_cut_paper', 'thermal_partial_cut', 'thermal_beep_enabled', 'thermal_feed_lines',
            # Multi-Printer Settings
            'default_printer_name', 'printer_profiles_enabled', 'printer_location_mapping',
            'bill_printer_name', 'kot_printer_name', 'invoice_printer_name', 'report_printer_name',
            'kitchen_printer_name', 'bar_printer_name', 'receipt_printer_name',
            'printer_auto_selection', 'printer_fallback_enabled', 'printer_priority_order',
            # Print Quality Settings
            'print_quality_dpi', 'print_contrast', 'print_brightness', 'print_speed_draft',
            'print_speed_normal', 'print_speed_high', 'print_dithering', 'print_color_mode',
            'print_media_type', 'print_finishing', 'print_collation', 'print_copies_default',
            # Print Layout Settings
            'print_page_orientation', 'print_page_size', 'print_margins', 'print_scaling',
            'print_headers_footers', 'print_page_numbers', 'print_date_time', 'print_logo_watermark',
            'print_border_enabled', 'print_shadow_enabled', 'print_alignment', 'print_wrapping',
            # Print Templates
            'print_template_receipt', 'print_template_invoice', 'print_template_kot',
            'print_template_custom_css', 'print_template_javascript', 'print_template_variables',
            'print_dynamic_content', 'print_conditional_content', 'print_loop_content',
            # Print Branding
            'print_header_enabled', 'print_footer_enabled', 'print_logo_size', 'print_font_size',
            'print_brand_colors', 'print_company_tagline', 'print_legal_disclaimer',
            'print_warranty_info', 'print_return_policy', 'print_contact_info',
            # Legacy Print Settings (for compatibility)
            'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
            'receipt_logo_path', 'receipt_header_color', 'receipt_footer_text', 'receipt_custom_message',
            'print_header_enabled', 'print_footer_enabled', 'print_logo_size', 'print_font_size',
            'login_background_image', 'login_background_color', 'login_card_background',
            'login_title', 'login_subtitle', 'login_features_enabled',
            'dashboard_welcome_text', 'dashboard_stats_enabled', 'dashboard_quick_actions_enabled',
            'nav_style', 'nav_color_scheme', 'nav_show_branding',
            'theme_preset', 'theme_custom_enabled'
        ]
        
        if key not in white_label_keys:
            raise ValueError(f"Invalid white label setting key: {key}")
        
        return Settings.set(key, value, description, is_public)
    
    def delete(self):
        """Delete setting"""
        db.session.delete(self)
        db.session.commit()
    
    def _encrypt_value_if_needed(self, key, value):
        """Encrypt setting value if it contains sensitive information"""
        if not value:
            return value
        
        # List of sensitive setting keys that need encryption
        sensitive_keys = [
            'sms_api_key',
            'restaurant_email',
            'restaurant_phone',
            'restaurant_address'  # Address might contain sensitive location info
        ]
        
        if key in sensitive_keys:
            return get_encryption_manager().encrypt_field(value)
        
        return value
    
    def _decrypt_value_if_needed(self, key, encrypted_value):
        """Decrypt setting value if it contains sensitive information"""
        if not encrypted_value:
            return encrypted_value
        
        # List of sensitive setting keys that need decryption
        sensitive_keys = [
            'sms_api_key',
            'restaurant_email',
            'restaurant_phone',
            'restaurant_address'
        ]
        
        if key in sensitive_keys:
            return get_encryption_manager().decrypt_field(encrypted_value)
        
        return encrypted_value
    
    @property
    def value_decrypted(self):
        """Get decrypted value"""
        return self._decrypt_value_if_needed(self.key, self.value)
    
    def __repr__(self):
        # Don't show sensitive values in repr
        if self.key in ['sms_api_key', 'restaurant_email', 'restaurant_phone']:
            return f'<Settings {self.key}: [ENCRYPTED]>'
        return f'<Settings {self.key}: {self.value}>'
