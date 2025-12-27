"""
Template context processors to provide common variables to all templates
"""
from flask import current_app
from models.settings import Settings

def inject_white_label_settings():
    """Inject white label settings into template context"""
    try:
        white_label_settings = Settings.get_white_label_settings()
        public_settings = Settings.get_public_settings()
        all_settings = Settings.get_all()
        return {
            'white_label_settings': white_label_settings,
            'public_settings': public_settings,
            'settings': all_settings  # Add all settings for template compatibility
        }
    except Exception as e:
        # Return empty settings if there's an error
        current_app.logger.error(f"Error loading white label settings: {str(e)}")
        return {
            'white_label_settings': {},
            'public_settings': {},
            'settings': {}  # Add empty settings dict for template compatibility
        }

def inject_app_config():
    """Inject app configuration into template context"""
    return {
        'app_name': current_app.config.get('APP_NAME', 'Restaurant POS'),
        'app_version': current_app.config.get('APP_VERSION', '1.0.0'),
        'debug': current_app.config.get('DEBUG', False)
    }