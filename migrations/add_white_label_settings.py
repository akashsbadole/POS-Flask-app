"""
Add white label settings to the database
Migration for comprehensive white label customization system
"""

import sys
import os

# Add the parent directory to the path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Settings
from datetime import datetime

def create_white_label_settings():
    """Create white label settings defaults"""
    
    # Company Information Settings
    company_settings = [
        # Company Details
        ('company_name', 'Restaurant POS', 'Company/business name for white label branding', True),
        ('company_full_name', '', 'Full company name', True),
        ('company_short_name', '', 'Short company name/abbreviation', True),
        ('company_tagline', '', 'Company tagline or slogan', True),
        
        # Contact Information
        ('company_address_line1', '', 'Company address line 1', True),
        ('company_address_line2', '', 'Company address line 2', True),
        ('company_city', '', 'Company city', True),
        ('company_state', '', 'Company state', True),
        ('company_country', '', 'Company country', True),
        ('company_postal_code', '', 'Postal/ZIP code', True),
        ('company_phone_primary', '', 'Primary phone number', True),
        ('company_phone_secondary', '', 'Secondary phone number', True),
        ('company_email_primary', '', 'Primary email address', True),
        ('company_email_secondary', '', 'Secondary email address', True),
        ('company_website', '', 'Company website URL', True),
        
        # Legal Information
        ('company_registration_number', '', 'Company registration number', True),
        ('company_tax_id', '', 'Company tax ID/GST number', True),
        ('company_legal_entity', '', 'Legal entity type (Pvt Ltd, Corp, etc.)', True),
        ('company_year_established', '', 'Year company was established', True),
    ]
    
    # Visual Branding Settings
    branding_settings = [
        # Logo Settings
        ('logo_main_path', '', 'Main company logo path', True),
        ('logo_header_path', '', 'Header logo path', True),
        ('logo_footer_path', '', 'Footer logo path', True),
        ('logo_favicon_path', '', 'Favicon logo path', True),
        ('logo_invoice_path', '', 'Invoice logo path', True),
        ('logo_email_path', '', 'Email template logo path', True),
        ('logo_login_path', '', 'Login page logo path', True),
        
        # Logo Display Options
        ('logo_show_in_header', 'true', 'Show logo in header', True),
        ('logo_show_in_footer', 'true', 'Show logo in footer', True),
        ('logo_show_in_login', 'true', 'Show logo in login page', True),
        ('logo_show_in_emails', 'true', 'Show logo in emails', True),
        ('logo_show_in_invoices', 'true', 'Show logo in invoices', True),
        ('logo_height_header', '40px', 'Logo height in header', False),
        ('logo_height_footer', '30px', 'Logo height in footer', False),
        ('logo_height_login', '60px', 'Logo height in login page', False),
        
        # Color Scheme
        ('brand_primary_color', '#007bff', 'Primary brand color (hex)', True),
        ('brand_secondary_color', '#6c757d', 'Secondary brand color (hex)', True),
        ('brand_accent_color', '#28a745', 'Accent brand color (hex)', True),
        ('brand_success_color', '#28a745', 'Success color (hex)', True),
        ('brand_warning_color', '#ffc107', 'Warning color (hex)', True),
        ('brand_danger_color', '#dc3545', 'Danger color (hex)', True),
        ('brand_info_color', '#17a2b8', 'Info color (hex)', True),
        ('brand_light_color', '#f8f9fa', 'Light color (hex)', True),
        ('brand_dark_color', '#343a40', 'Dark color (hex)', True),
        
        # Background Colors
        ('bg_primary_color', '#ffffff', 'Primary background color (hex)', True),
        ('bg_secondary_color', '#f8f9fa', 'Secondary background color (hex)', True),
        ('bg_header_color', '#ffffff', 'Header background color (hex)', True),
        ('bg_footer_color', '#f8f9fa', 'Footer background color (hex)', True),
        
        # Text Colors
        ('text_primary_color', '#212529', 'Primary text color (hex)', True),
        ('text_secondary_color', '#6c757d', 'Secondary text color (hex)', True),
        ('text_light_color', '#ffffff', 'Light text color (hex)', True),
        ('text_header_color', '#212529', 'Header text color (hex)', True),
        ('text_footer_color', '#6c757d', 'Footer text color (hex)', True),
    ]
    
    # Typography Settings
    typography_settings = [
        # Font Families
        ('font_primary_family', 'Inter, sans-serif', 'Primary font family', True),
        ('font_secondary_family', 'Inter, sans-serif', 'Secondary font family', True),
        ('font_header_family', 'Inter, sans-serif', 'Header font family', True),
        ('font_body_family', 'Inter, sans-serif', 'Body text font family', True),
        
        # Font Sizes
        ('font_size_base', '14px', 'Base font size', False),
        ('font_size_small', '12px', 'Small font size', False),
        ('font_size_large', '16px', 'Large font size', False),
        ('font_size_h1', '32px', 'Heading 1 font size', False),
        ('font_size_h2', '28px', 'Heading 2 font size', False),
        ('font_size_h3', '24px', 'Heading 3 font size', False),
        ('font_size_h4', '20px', 'Heading 4 font size', False),
        ('font_size_h5', '18px', 'Heading 5 font size', False),
        ('font_size_h6', '16px', 'Heading 6 font size', False),
        
        # Font Weights
        ('font_weight_light', '300', 'Light font weight', False),
        ('font_weight_normal', '400', 'Normal font weight', False),
        ('font_weight_medium', '500', 'Medium font weight', False),
        ('font_weight_semibold', '600', 'Semi-bold font weight', False),
        ('font_weight_bold', '700', 'Bold font weight', False),
        
        # Line Heights
        ('line_height_base', '1.5', 'Base line height', False),
        ('line_height_heading', '1.2', 'Heading line height', False),
    ]
    
    # Custom Content Settings
    content_settings = [
        # Welcome Messages
        ('welcome_message_dashboard', 'Welcome to our restaurant management system!', 'Dashboard welcome message', True),
        ('welcome_message_login', 'Welcome back! Please sign in to continue.', 'Login page welcome message', True),
        ('welcome_message_registration', 'Join us today and start managing your restaurant efficiently.', 'Registration welcome message', True),
        
        # Custom Text
        ('custom_header_text', '', 'Custom header text', True),
        ('custom_footer_text', 'Thank you for choosing our restaurant management system.', 'Custom footer text', True),
        ('custom_about_text', '', 'About us custom text', True),
        ('custom_contact_text', '', 'Contact information custom text', True),
        
        # Custom CSS
        ('custom_css_enabled', 'false', 'Enable custom CSS injection', False),
        ('custom_css_content', '', 'Custom CSS content for white labeling', False),
        ('custom_css_priority', '100', 'Custom CSS loading priority', False),
    ]
    
    # Email Template Settings
    email_settings = [
        # Email Branding
        ('email_header_logo', '', 'Email header logo path', True),
        ('email_footer_logo', '', 'Email footer logo path', True),
        ('email_signature_text', 'Best regards,\nThe Restaurant POS Team', 'Email signature text', True),
        ('email_contact_info', '', 'Email contact information', True),
        
        # Email Colors
        ('email_primary_color', '#007bff', 'Email primary color', True),
        ('email_background_color', '#ffffff', 'Email background color', True),
        ('email_text_color', '#333333', 'Email text color', True),
        
        # Email Templates
        ('email_template_style', 'modern', 'Email template style (modern, classic, minimal)', True),
        ('email_show_social_links', 'true', 'Show social media links in emails', True),
        ('email_social_links', '', 'Social media links JSON', True),
    ]
    
    # Print Material Settings
    print_settings = [
        # Invoice Branding
        ('invoice_logo_path', '', 'Invoice logo path', True),
        ('invoice_header_color', '#007bff', 'Invoice header color', True),
        ('invoice_footer_text', 'Thank you for your business!', 'Invoice footer text', True),
        ('invoice_terms_text', '', 'Invoice terms and conditions', True),
        ('invoice_note_text', '', 'Invoice note text', True),
        
        # Receipt Branding
        ('receipt_logo_path', '', 'Receipt logo path', True),
        ('receipt_header_color', '#007bff', 'Receipt header color', True),
        ('receipt_footer_text', 'Thank you for your visit!', 'Receipt footer text', True),
        ('receipt_custom_message', '', 'Receipt custom message', True),
        
        # Print Layout
        ('print_header_enabled', 'true', 'Enable print header', True),
        ('print_footer_enabled', 'true', 'Enable print footer', True),
        ('print_logo_size', '100px', 'Print logo size', False),
        ('print_font_size', '12px', 'Print font size', False),
    ]
    
    # Application UI Settings
    ui_settings = [
        # Login Screen
        ('login_background_image', '', 'Login page background image path', True),
        ('login_background_color', '#f8f9fa', 'Login page background color', True),
        ('login_card_background', '#ffffff', 'Login card background color', True),
        ('login_title', 'Welcome Back', 'Login page title', True),
        ('login_subtitle', 'Sign in to manage your restaurant', 'Login page subtitle', True),
        ('login_features_enabled', 'true', 'Enable login features section', True),
        
        # Dashboard
        ('dashboard_welcome_text', 'Welcome to your restaurant dashboard', 'Dashboard welcome text', True),
        ('dashboard_stats_enabled', 'true', 'Enable dashboard statistics', True),
        ('dashboard_quick_actions_enabled', 'true', 'Enable dashboard quick actions', True),
        
        # Navigation
        ('nav_style', 'modern', 'Navigation style (modern, classic, minimal)', True),
        ('nav_color_scheme', 'light', 'Navigation color scheme (light, dark)', True),
        ('nav_show_branding', 'true', 'Show branding in navigation', True),
        
        # Theme Presets
        ('theme_preset', 'default', 'Theme preset (default, corporate, modern, elegant)', True),
        ('theme_custom_enabled', 'false', 'Enable custom theme creation', False),
    ]
    
    # White Label Features
    white_label_features = [
        # Custom Domain/Subdomain
        ('custom_domain_enabled', 'false', 'Enable custom domain support', False),
        ('custom_domain', '', 'Custom domain name', False),
        ('subdomain_enabled', 'false', 'Enable subdomain branding', False),
        ('subdomain_name', '', 'Subdomain for white labeling', False),
        
        # Branded URLs
        ('branded_urls_enabled', 'false', 'Enable branded URL structure', False),
        ('url_prefix', '', 'URL prefix for white labeling', False),
        
        # API Branding
        ('api_branding_enabled', 'false', 'Enable API response branding', False),
        ('api_brand_name', '', 'API brand name', False),
        ('api_support_email', '', 'API support email', False),
    ]
    
    # Security & Performance
    security_settings = [
        # File Upload Security
        ('logo_upload_max_size', '2048', 'Maximum logo file size in KB', False),
        ('logo_upload_formats', 'png,jpg,jpeg,svg', 'Allowed logo formats', False),
        ('logo_optimization_enabled', 'true', 'Enable automatic logo optimization', False),
        
        # CSS Security
        ('css_injection_enabled', 'false', 'Enable CSS injection (security risk)', False),
        ('css_whitelist_enabled', 'true', 'Enable CSS property whitelist', False),
        
        # Performance
        ('logo_caching_enabled', 'true', 'Enable logo file caching', False),
        ('css_minification_enabled', 'true', 'Enable CSS minification', False),
    ]
    
    # Combine all settings
    all_white_label_settings = (
        company_settings + 
        branding_settings + 
        typography_settings + 
        content_settings + 
        email_settings + 
        print_settings + 
        ui_settings + 
        white_label_features + 
        security_settings
    )
    
    # Create settings in database
    created_count = 0
    for key, value, description, is_public in all_white_label_settings:
        if not Settings.query.filter_by(key=key).first():
            setting = Settings(key, value, description, is_public)
            db.session.add(setting)
            created_count += 1
    
    db.session.commit()
    return created_count

def remove_white_label_settings():
    """Remove white label settings (for rollback)"""
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
        
        # Print
        'invoice_logo_path', 'invoice_header_color', 'invoice_footer_text', 'invoice_terms_text', 'invoice_note_text',
        'receipt_logo_path', 'receipt_header_color', 'receipt_footer_text', 'receipt_custom_message',
        'print_header_enabled', 'print_footer_enabled', 'print_logo_size', 'print_font_size',
        
        # UI
        'login_background_image', 'login_background_color', 'login_card_background',
        'login_title', 'login_subtitle', 'login_features_enabled',
        'dashboard_welcome_text', 'dashboard_stats_enabled', 'dashboard_quick_actions_enabled',
        'nav_style', 'nav_color_scheme', 'nav_show_branding',
        'theme_preset', 'theme_custom_enabled',
        
        # White Label Features
        'custom_domain_enabled', 'custom_domain', 'subdomain_enabled', 'subdomain_name',
        'branded_urls_enabled', 'url_prefix',
        'api_branding_enabled', 'api_brand_name', 'api_support_email',
        
        # Security
        'logo_upload_max_size', 'logo_upload_formats', 'logo_optimization_enabled',
        'css_injection_enabled', 'css_whitelist_enabled',
        'logo_caching_enabled', 'css_minification_enabled',
    ]
    
    deleted_count = 0
    for key in white_label_keys:
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            db.session.delete(setting)
            deleted_count += 1
    
    db.session.commit()
    return deleted_count

if __name__ == '__main__':
    # This can be run directly to add white label settings
    import sys
    import os
    
    # Add the parent directory to the path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Import the app and create app context
    from app import create_app
    from models import db, Settings
    
    app = create_app()
    
    with app.app_context():
        created_count = create_white_label_settings()
        print(f"Created {created_count} white label settings")