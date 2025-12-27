"""
Print Template Engine
Dynamic print template generation with comprehensive customization support
"""

import os
import json
import re
from datetime import datetime
from flask import current_app
from models import Settings

class PrintTemplateEngine:
    """Advanced print template engine with dynamic customization"""
    
    def __init__(self):
        self.template_cache = {}
        self.custom_css_cache = {}
        self.variables_cache = {}
        
        # Load all print settings
        self.receipt_settings = Settings.get_receipt_settings()
        self.invoice_settings = Settings.get_invoice_settings()
        self.kot_settings = Settings.get_kot_settings()
        self.thermal_settings = Settings.get_thermal_printer_settings()
        self.print_layout_settings = Settings.get_print_layout_settings()
        self.print_branding_settings = Settings.get_print_branding_settings()
        self.template_settings = Settings.get_print_template_settings()
        
        # Company information
        self.company_info = Settings.get_company_info()
    
    def generate_receipt_template(self, order_data, customization=None):
        """Generate customized receipt template"""
        template_data = {
            'order': order_data,
            'company': self.company_info,
            'customization': customization or self.receipt_settings,
            'thermal_config': self._get_thermal_config(),
            'generated_at': datetime.now().isoformat()
        }
        
        # Apply template logic
        if self.receipt_settings.get('receipt_layout_style', 'default') == 'compact':
            template_data['layout'] = 'compact'
            template_html = self._render_compact_receipt(template_data)
        elif self.receipt_settings.get('receipt_layout_style', 'default') == 'detailed':
            template_data['layout'] = 'detailed'
            template_html = self._render_detailed_receipt(template_data)
        else:
            template_html = self._render_standard_receipt(template_data)
        
        # Apply custom CSS
        custom_css = self._get_custom_css('receipt')
        if custom_css:
            template_html = self._inject_custom_css(template_html, custom_css)
        
        return template_html
    
    def generate_invoice_template(self, order_data, customization=None):
        """Generate customized invoice template"""
        template_data = {
            'order': order_data,
            'company': self.company_info,
            'customization': customization or self.invoice_settings,
            'billing_info': self._get_billing_info(order_data),
            'generated_at': datetime.now().isoformat()
        }
        
        # Apply template logic
        if self.invoice_settings.get('invoice_layout_style', 'default') == 'modern':
            template_html = self._render_modern_invoice(template_data)
        elif self.invoice_settings.get('invoice_layout_style', 'default') == 'traditional':
            template_html = self._render_traditional_invoice(template_data)
        else:
            template_html = self._render_standard_invoice(template_data)
        
        # Apply custom CSS
        custom_css = self._get_custom_css('invoice')
        if custom_css:
            template_html = self._inject_custom_css(template_html, custom_css)
        
        return template_html
    
    def generate_kot_template(self, order_data, customization=None):
        """Generate customized KOT template"""
        template_data = {
            'order': order_data,
            'company': self.company_info,
            'customization': customization or self.kot_settings,
            'kot_config': self._get_kot_config(),
            'generated_at': datetime.now().isoformat()
        }
        
        # Apply template logic
        if self.kot_settings.get('kot_layout_style', 'default') == 'kitchen_friendly':
            template_html = self._render_kitchen_kot(template_data)
        elif self.kot_settings.get('kot_layout_style', 'default') == 'compact':
            template_html = self._render_compact_kot(template_data)
        else:
            template_html = self._render_standard_kot(template_data)
        
        # Apply custom CSS
        custom_css = self._get_custom_css('kot')
        if custom_css:
            template_html = self._inject_custom_css(template_html, custom_css)
        
        return template_html
    
    def _render_standard_receipt(self, data):
        """Render standard receipt template"""
        order = data['order']
        company = data['company']
        customization = data['customization']
        
        html = f"""
        <div class="receipt-container thermal-container">
            <!-- Header -->
            <div class="receipt-header">
                {self._render_receipt_header(company, customization)}
            </div>
            
            <!-- Order Information -->
            <div class="receipt-order-info">
                {self._render_order_info(order, customization)}
            </div>
            
            <!-- Items -->
            <div class="receipt-items">
                {self._render_receipt_items(order, customization)}
            </div>
            
            <!-- Totals -->
            <div class="receipt-totals">
                {self._render_receipt_totals(order, customization)}
            </div>
            
            <!-- Payments -->
            {self._render_payments_section(order, customization) if customization.get('show_payment_methods', True) else ''}
            
            <!-- Footer -->
            <div class="receipt-footer">
                {self._render_receipt_footer(company, customization)}
            </div>
            
            <!-- Cutting Line -->
            {self._render_cutting_line() if customization.get('cutting_line', True) else ''}
            
            <!-- Barcode/QR Code -->
            {self._render_codes(order, customization)}
        </div>
        """
        
        return self._apply_thermal_optimizations(html, 'receipt')
    
    def _render_receipt_header(self, company, customization):
        """Render receipt header with logo and company info"""
        header_html = []
        
        # Logo
        if customization.get('show_company_logo', True):
            logo_path = customization.get('receipt_logo_path', '')
            if logo_path:
                logo_size = customization.get('receipt_logo_size', '100px')
                header_html.append(f'''
                    <div class="receipt-logo">
                        <img src="/static/{logo_path}" alt="Company Logo" style="max-width: {logo_size}; max-height: {logo_size};">
                    </div>
                ''')
        
        # Company Info
        if customization.get('show_company_info', True):
            header_html.append(f'''
                <div class="receipt-company-info">
                    <h2 style="color: {customization.get('receipt_header_color', '#000')}; margin: 5px 0;">{company.get('company_name', 'Restaurant')}</h2>
                    {self._render_company_details(company)}
                </div>
            ''')
        
        return '\\n'.join(header_html)
    
    def _render_company_details(self, company):
        """Render company contact details"""
        details = []
        
        if company.get('company_address_line1'):
            details.append(f"<div>{company['company_address_line1']}</div>")
        
        if company.get('company_city') or company.get('company_state'):
            city_state = []
            if company.get('company_city'):
                city_state.append(company['company_city'])
            if company.get('company_state'):
                city_state.append(company['company_state'])
            if city_state:
                details.append(f"<div>{', '.join(city_state)}</div>")
        
        if company.get('company_phone_primary'):
            details.append(f"<div>Phone: {company['company_phone_primary']}</div>")
        
        if company.get('company_tax_id') and self.receipt_settings.get('receipt_show_gst_number', True):
            details.append(f"<div>GST: {company['company_tax_id']}</div>")
        
        return '\\n'.join(details)
    
    def _render_order_info(self, order, customization):
        """Render order information section"""
        info_html = []
        
        # Order number and date
        order_date = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M')
        info_html.append(f'''
            <div class="receipt-order-number">
                <strong>Order #{order['order_number']}</strong>
            </div>
            <div class="receipt-order-date">{order_date}</div>
        ''')
        
        # Customer info
        if customization.get('show_customer_name', True) and order.get('customer_name'):
            info_html.append(f'''
                <div class="receipt-customer">
                    Customer: {order['customer_name']}
                </div>
            ''')
        
        return '\\n'.join(info_html)
    
    def _render_receipt_items(self, order, customization):
        """Render receipt items table"""
        items_html = ['<div class="receipt-items-list">']
        
        for item in order.get('items', []):
            item_total = float(item['price']) * item['quantity']
            items_html.append(f'''
                <div class="receipt-item">
                    <div class="item-details">
                        <div class="item-name">{item['item_name']}</div>
                        {f"<div class='item-instructions' style='font-size: 10px; color: #666;'>{item['special_instructions']}</div>" if item.get('special_instructions') else ""}
                    </div>
                    <div class="item-quantity">x{item['quantity']}</div>
                    <div class="item-price">₹{item_total:.2f}</div>
                </div>
            ''')
        
        items_html.append('</div>')
        return '\\n'.join(items_html)
    
    def _render_receipt_totals(self, order, customization):
        """Render receipt totals section"""
        subtotal = sum(float(item['price']) * item['quantity'] for item in order.get('items', []))
        tax_amount = float(order.get('tax_amount', 0))
        discount_amount = float(order.get('discount_amount', 0))
        grand_total = subtotal + tax_amount - discount_amount
        
        totals_html = ['<div class="receipt-totals-list">']
        
        # Subtotal
        totals_html.append(f'''
            <div class="total-row">
                <span>Subtotal:</span>
                <span>₹{subtotal:.2f}</span>
            </div>
        ''')
        
        # Discount
        if discount_amount > 0 and customization.get('show_discounts', True):
            totals_html.append(f'''
                <div class="total-row discount">
                    <span>Discount:</span>
                    <span>-₹{discount_amount:.2f}</span>
                </div>
            ''')
        
        # Tax
        if tax_amount > 0 and customization.get('show_tax_breakdown', True):
            totals_html.append(f'''
                <div class="total-row tax">
                    <span>Tax:</span>
                    <span>₹{tax_amount:.2f}</span>
                </div>
            ''')
        
        # Grand Total
        totals_html.append(f'''
            <div class="total-row grand-total" style="border-top: 1px solid #000; padding-top: 5px; font-weight: bold;">
                <span>Total:</span>
                <span>₹{grand_total:.2f}</span>
            </div>
        ''')
        
        totals_html.append('</div>')
        return '\\n'.join(totals_html)
    
    def _render_payments_section(self, order, customization):
        """Render payments section"""
        if not order.get('payments'):
            return ""
        
        payments_html = ['<div class="receipt-payments">']
        payments_html.append('<div class="payments-title">Payments:</div>')
        
        for payment in order['payments']:
            payments_html.append(f'''
                <div class="payment-row">
                    <span>{payment['payment_mode']}:</span>
                    <span>₹{float(payment['amount']):.2f}</span>
                </div>
            ''')
        
        payments_html.append('</div>')
        return '\\n'.join(payments_html)
    
    def _render_receipt_footer(self, company, customization):
        """Render receipt footer"""
        footer_html = []
        
        # Custom footer message
        if customization.get('receipt_custom_message'):
            footer_html.append(f'''
                <div class="receipt-message">
                    {customization['receipt_custom_message']}
                </div>
            ''')
        
        # Footer text
        if customization.get('receipt_footer_text'):
            footer_html.append(f'''
                <div class="receipt-footer-text">
                    {customization['receipt_footer_text']}
                </div>
            ''')
        
        # Thank you message
        footer_html.append('<div class="receipt-thank-you">Thank you for your business!</div>')
        
        return '\\n'.join(footer_html)
    
    def _render_cutting_line(self):
        """Render cutting line"""
        return '<div class="receipt-cutting-line"></div>'
    
    def _render_codes(self, order, customization):
        """Render barcode and QR code"""
        codes_html = []
        
        if customization.get('receipt_barcode_enabled', False):
            codes_html.append(f'''
                <div class="receipt-barcode">
                    <div class="barcode-placeholder">[{order['order_number']}]</div>
                </div>
            ''')
        
        if customization.get('receipt_qr_code_enabled', False):
            codes_html.append(f'''
                <div class="receipt-qr-code">
                    <div class="qr-code-placeholder">QR Code</div>
                </div>
            ''')
        
        return '\\n'.join(codes_html) if codes_html else ""
    
    def _render_standard_invoice(self, data):
        """Render standard invoice template"""
        order = data['order']
        company = data['company']
        customization = data['customization']
        
        html = f"""
        <div class="invoice-container">
            <!-- Header -->
            <div class="invoice-header">
                <div class="invoice-company">
                    {self._render_invoice_company_section(company, customization)}
                </div>
                <div class="invoice-details">
                    <h1 style="color: {customization.get('invoice_header_color', '#000')};">INVOICE</h1>
                    {self._render_invoice_header_details(order, customization)}
                </div>
            </div>
            
            <!-- Billing Information -->
            <div class="invoice-billing">
                {self._render_billing_section(order, customization)}
            </div>
            
            <!-- Items Table -->
            <div class="invoice-items">
                {self._render_invoice_items_table(order, customization)}
            </div>
            
            <!-- Totals -->
            <div class="invoice-totals">
                {self._render_invoice_totals(order, customization)}
            </div>
            
            <!-- Terms and Conditions -->
            {self._render_terms_section(customization) if customization.get('invoice_terms_enabled', True) else ''}
            
            <!-- Notes -->
            {self._render_notes_section(order, customization) if customization.get('invoice_notes_enabled', True) else ''}
            
            <!-- Footer -->
            <div class="invoice-footer">
                {self._render_invoice_footer(company, customization)}
            </div>
            
            <!-- Signature -->
            {self._render_signature_section() if customization.get('invoice_show_signature', False) else ''}
        </div>
        """
        
        return html
    
    def _render_standard_kot(self, data):
        """Render standard KOT template"""
        order = data['order']
        company = data['company']
        customization = data['customization']
        
        html = f"""
        <div class="kot-container thermal-container">
            <!-- Header -->
            <div class="kot-header">
                {self._render_kot_header(company, customization)}
            </div>
            
            <!-- Order Details -->
            <div class="kot-order-details">
                {self._render_kot_order_details(order, customization)}
            </div>
            
            <!-- Items -->
            <div class="kot-items">
                {self._render_kot_items(order, customization)}
            </div>
            
            <!-- Special Instructions -->
            {self._render_kot_special_instructions(order, customization) if customization.get('kot_show_special_instructions', True) else ''}
            
            <!-- Footer -->
            <div class="kot-footer">
                {self._render_kot_footer(company, customization)}
            </div>
            
            <!-- Cutting Line -->
            {self._render_cutting_line() if customization.get('kot_cutting_line', True) else ''}
        </div>
        """
        
        return self._apply_thermal_optimizations(html, 'kot')
    
    def _get_thermal_config(self):
        """Get thermal printer configuration"""
        return {
            'paper_width': self.thermal_settings.get('thermal_paper_width', '80mm'),
            'font_family': self.thermal_settings.get('thermal_font_family', 'monospace'),
            'font_size': self.thermal_settings.get('thermal_font_size', '12px'),
            'line_spacing': self.thermal_settings.get('thermal_line_spacing', '1.5'),
            'margins': {
                'top': self.thermal_settings.get('thermal_margin_top', '5mm'),
                'bottom': self.thermal_settings.get('thermal_margin_bottom', '5mm'),
                'left': self.thermal_settings.get('thermal_margin_left', '3mm'),
                'right': self.thermal_settings.get('thermal_margin_right', '3mm')
            },
            'cut_paper': self.thermal_settings.get('thermal_cut_paper', 'true') == 'true'
        }
    
    def _get_kot_config(self):
        """Get KOT specific configuration"""
        return {
            'table_style': self.kot_settings.get('kot_table_number_style', 'bold'),
            'order_type_display': self.kot_settings.get('kot_order_type_display', 'true') == 'true',
            'priority_display': self.kot_settings.get('kot_priority_display', 'true') == 'true',
            'show_cooking_time': self.kot_settings.get('kot_show_cooking_time', 'false') == 'true',
            'order_separation': self.kot_settings.get('kot_order_separation', 'true') == 'true'
        }
    
    def _get_billing_info(self, order_data):
        """Extract billing information from order"""
        return {
            'billing_address': self.invoice_settings.get('invoice_billing_address', ''),
            'shipping_address': self.invoice_settings.get('invoice_shipping_address', ''),
            'bank_details': self.invoice_settings.get('invoice_show_bank_details', 'false') == 'true'
        }
    
    def _get_custom_css(self, print_type):
        """Get custom CSS for print type"""
        cache_key = f"{print_type}_css"
        if cache_key in self.custom_css_cache:
            return self.custom_css_cache[cache_key]
        
        # Get custom CSS from template settings
        custom_css = self.template_settings.get('print_template_custom_css', '')
        if custom_css:
            # Filter CSS for specific print type
            type_specific_css = self._extract_type_specific_css(custom_css, print_type)
            self.custom_css_cache[cache_key] = type_specific_css
            return type_specific_css
        
        return ""
    
    def _extract_type_specific_css(self, css_content, print_type):
        """Extract CSS rules specific to print type"""
        # Simple CSS parsing - in production, use proper CSS parser
        lines = css_content.split('\\n')
        type_specific_lines = []
        
        for line in lines:
            # Include global styles and type-specific styles
            if (not line.strip().startswith('.') or 
                f'.{print_type}' in line or 
                line.strip().startswith('@') or
                line.strip().startswith('*') or
                'thermal' in line.lower()):
                type_specific_lines.append(line)
        
        return '\\n'.join(type_specific_lines)
    
    def _inject_custom_css(self, html, custom_css):
        """Inject custom CSS into HTML"""
        if not custom_css:
            return html
        
        css_injection = f"""
        <style type="text/css">
        {custom_css}
        </style>
        """
        
        # Insert CSS before closing head tag or at the beginning of body
        if '<head>' in html:
            html = html.replace('<head>', f'<head>{css_injection}')
        else:
            html = html.replace('<body>', f'<body>{css_injection}')
        
        return html
    
    def _apply_thermal_optimizations(self, html, print_type):
        """Apply thermal printer specific optimizations"""
        thermal_config = self._get_thermal_config()
        
        # Add thermal-specific classes and attributes
        optimizations = []
        
        # Paper width optimization
        if thermal_config['paper_width'] == '58mm':
            optimizations.append('thermal-58mm')
        elif thermal_config['paper_width'] == '80mm':
            optimizations.append('thermal-80mm')
        
        # Font optimization
        optimizations.append(f'thermal-font-{thermal_config["font_family"].replace(" ", "-")}')
        
        # Add thermal class to container
        html = html.replace(
            f'<div class="{print_type}-container',
            f'<div class="{print_type}-container thermal-print {" ".join(optimizations)}'
        )
        
        # Add thermal-specific meta tags
        thermal_meta = f"""
        <!-- Thermal Printer Configuration -->
        <meta name="thermal-paper-width" content="{thermal_config['paper_width']}">
        <meta name="thermal-font-family" content="{thermal_config['font_family']}">
        <meta name="thermal-font-size" content="{thermal_config['font_size']}">
        <meta name="thermal-line-spacing" content="{thermal_config['line_spacing']}">
        """
        
        if '<head>' in html:
            html = html.replace('<head>', f'<head>{thermal_meta}')
        
        return html
    
    def clear_cache(self):
        """Clear template cache"""
        self.template_cache.clear()
        self.custom_css_cache.clear()
        self.variables_cache.clear()
    
    def refresh_settings(self):
        """Refresh all settings from database"""
        self.clear_cache()
        
        # Reload all settings
        self.receipt_settings = Settings.get_receipt_settings()
        self.invoice_settings = Settings.get_invoice_settings()
        self.kot_settings = Settings.get_kot_settings()
        self.thermal_settings = Settings.get_thermal_printer_settings()
        self.print_layout_settings = Settings.get_print_layout_settings()
        self.print_branding_settings = Settings.get_print_branding_settings()
        self.template_settings = Settings.get_print_template_settings()
        self.company_info = Settings.get_company_info()

# Helper functions for template rendering
def render_print_template(template_type, order_data, customization=None):
    """Helper function to render print template"""
    engine = PrintTemplateEngine()
    
    if template_type == 'receipt':
        return engine.generate_receipt_template(order_data, customization)
    elif template_type == 'invoice':
        return engine.generate_invoice_template(order_data, customization)
    elif template_type == 'kot':
        return engine.generate_kot_template(order_data, customization)
    else:
        raise ValueError(f"Unknown template type: {template_type}")

def get_template_variables(template_type):
    """Get available variables for template"""
    engine = PrintTemplateEngine()
    cache_key = f"{template_type}_variables"
    
    if cache_key in engine.variables_cache:
        return engine.variables_cache[cache_key]
    
    # Define available variables for each template type
    variables = {
        'receipt': [
            'order.order_number', 'order.created_at', 'order.customer_name',
            'company.company_name', 'company.company_address', 'company.company_phone',
            'customization.show_logo', 'customization.show_company_info',
            'thermal_config.paper_width', 'thermal_config.font_family'
        ],
        'invoice': [
            'order.order_number', 'order.created_at', 'order.customer_name',
            'company.company_name', 'company.company_address', 'company.company_tax_id',
            'billing_info.billing_address', 'customization.invoice_terms_enabled'
        ],
        'kot': [
            'order.order_number', 'order.table_number', 'order.customer_name',
            'company.company_name', 'customization.kot_show_special_instructions',
            'kot_config.priority_display', 'kot_config.table_style'
        ]
    }
    
    engine.variables_cache[cache_key] = variables.get(template_type, [])
    return engine.variables_cache[cache_key]