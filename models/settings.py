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
