"""
Footer Generator for Web Version
Handles dynamic footer generation for different document types
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from models import Settings


class FooterGenerator:
    """
    Footer Generator for creating dynamic footers
    """
    
    def __init__(self):
        """Initialize footer generator"""
        self.settings = Settings.get_all_as_dict()
    
    def generate_footer(self, document_type: str = 'receipt', 
                      order_data: Dict = None, 
                      user_data: Dict = None) -> str:
        """
        Generate footer HTML for specified document type
        
        Args:
            document_type: Type of document (receipt, invoice, report, etc.)
            order_data: Order information for dynamic content
            user_data: User information for dynamic content
            
        Returns:
            HTML string for footer
        """
        if not self.settings.get('footer_enabled', 'true').lower() == 'true':
            return ''
        
        footer_config = self._get_footer_config()
        
        # Prepare template data
        template_data = {
            'footer_config': footer_config,
            'document_type': document_type,
            'order_data': order_data or {},
            'user_data': user_data or {},
            'current_receipt': order_data or {},
            'current_user': user_data or {},
            'page_title': self._get_page_title(document_type),
            'moment': self._get_moment_object()
        }
        
        # Generate footer HTML
        footer_html = self._render_footer_template(template_data)
        
        return footer_html
    
    def get_footer_css(self) -> str:
        """
        Get CSS styles for footer
        
        Returns:
            CSS string for footer styling
        """
        footer_config = self._get_footer_config()
        
        css = f"""
        .app-footer {{
            background-color: {footer_config.get('background_color', '#2c3e50')};
            color: {footer_config.get('text_color', '#ecf0f1')};
            padding: {footer_config.get('padding', '15px 20px')};
            border-top: {footer_config.get('border_width', '2px')} solid {footer_config.get('border_color', '#34495e')};
            font-family: {footer_config.get('font_family', 'Arial, sans-serif')};
            font-size: {footer_config.get('font_size', '12px')};
            margin-top: auto;
            width: 100%;
        }}

        .app-footer.fixed-footer {{
            position: fixed;
            bottom: 0;
            left: 0;
            z-index: 1000;
        }}

        .footer-container {{
            max-width: 100%;
            margin: 0 auto;
        }}

        .footer-sections {{
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 10px;
        }}

        .footer-section {{
            flex: 1;
            min-width: 200px;
        }}

        .footer-section h4 {{
            margin: 0 0 5px 0;
            font-size: {footer_config.get('header_font_size', '14px')};
            color: {footer_config.get('header_color', '#3498db')};
            font-weight: {footer_config.get('header_font_weight', 'bold')};
        }}

        .footer-section p {{
            margin: 2px 0;
            line-height: 1.4;
        }}

        .footer-bottom {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid {footer_config.get('border_color', '#34495e')};
            padding-top: 8px;
            margin-top: 8px;
            font-size: {footer_config.get('small_font_size', '10px')};
            opacity: 0.8;
        }}

        .footer-left, .footer-center, .footer-right {{
            flex: 1;
        }}

        .footer-center {{
            text-align: center;
        }}

        .footer-right {{
            text-align: right;
        }}

        .footer-logo img {{
            margin-bottom: 5px;
            max-height: {footer_config.get('logo_height', '30px')};
        }}

        /* Responsive Design */
        @media (max-width: 768px) {{
            .footer-sections {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .footer-section {{
                min-width: 100%;
            }}
            
            .footer-bottom {{
                flex-direction: column;
                gap: 5px;
                text-align: center;
            }}
            
            .footer-left, .footer-center, .footer-right {{
                text-align: center;
                flex: none;
            }}
        }}

        @media print {{
            .app-footer {{
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                page-break-inside: avoid;
            }}
        }}
        """
        
        return css
    
    def _get_footer_config(self) -> Dict:
        """Get footer configuration from settings"""
        return {
            'enabled': self.settings.get('footer_enabled', 'true').lower() == 'true',
            'business_name': self.settings.get('footer_business_name', ''),
            'address': self.settings.get('footer_address', ''),
            'phone': self.settings.get('footer_phone', ''),
            'email': self.settings.get('footer_email', ''),
            'company_logo': self.settings.get('footer_company_logo', ''),
            'logo_height': self.settings.get('footer_logo_height', '30px'),
            'show_business_info': self.settings.get('footer_show_business_info', 'true').lower() == 'true',
            'show_receipt_info': self.settings.get('footer_show_receipt_info', 'true').lower() == 'true',
            'show_user_info': self.settings.get('footer_show_user_name', 'true').lower() == 'true',
            'show_user_id': self.settings.get('footer_show_user_id', 'false').lower() == 'true',
            'show_timestamp': self.settings.get('footer_show_timestamp', 'true').lower() == 'true',
            'show_page_info': self.settings.get('footer_show_page_info', 'true').lower() == 'true',
            'show_version': self.settings.get('footer_show_version', 'false').lower() == 'true',
            'custom_text': self.settings.get('footer_custom_text', 'Thank you for your business!'),
            'background_color': self.settings.get('footer_background_color', '#2c3e50'),
            'text_color': self.settings.get('footer_text_color', '#ecf0f1'),
            'border_color': self.settings.get('footer_border_color', '#34495e'),
            'border_width': self.settings.get('footer_border_width', '2px'),
            'font_family': self.settings.get('footer_font_family', 'Arial, sans-serif'),
            'font_size': self.settings.get('footer_font_size', '12px'),
            'header_font_size': self.settings.get('footer_header_font_size', '14px'),
            'header_color': self.settings.get('footer_header_color', '#3498db'),
            'header_font_weight': self.settings.get('footer_header_font_weight', 'bold'),
            'small_font_size': self.settings.get('footer_small_font_size', '10px'),
            'padding': self.settings.get('footer_padding', '15px 20px'),
            'fixed_position': self.settings.get('footer_fixed_position', 'false').lower() == 'true',
            'version': self.settings.get('footer_version', '1.0.0'),
            'default_user': self.settings.get('footer_default_user', 'Staff')
        }
    
    def _get_page_title(self, document_type: str) -> str:
        """Get page title based on document type"""
        titles = {
            'receipt': 'Receipt',
            'invoice': 'Invoice',
            'order': 'Order',
            'report': 'Report',
            'kot': 'Kitchen Order Ticket',
            'payment': 'Payment Receipt'
        }
        return titles.get(document_type, 'Document')
    
    def _get_moment_object(self):
        """Get moment-like object for date formatting"""
        class Moment:
            @staticmethod
            def format(fmt):
                return datetime.now().strftime(fmt.replace('YYYY', '%Y').replace('MM', '%m').replace('DD', '%d')
                                               .replace('HH', '%H').replace('mm', '%M').replace('ss', '%S'))
        return Moment()
    
    def _render_footer_template(self, data: Dict) -> str:
        """Render footer template with data"""
        footer_config = data['footer_config']
        order_data = data['order_data']
        user_data = data['user_data']
        
        # Process custom text with placeholders
        custom_text = self._process_placeholders(footer_config.get('custom_text', ''), data)
        
        html = f"""
        <div id="app-footer" class="app-footer {'fixed-footer' if footer_config.get('fixed_position', False) else ''}">
            <div class="footer-container">
                <div class="footer-sections">
        """
        
        # Business Information Section
        if footer_config.get('show_business_info', True):
            html += self._render_business_section(footer_config)
        
        # Receipt Information Section
        if footer_config.get('show_receipt_info', True) and order_data:
            html += self._render_receipt_section(footer_config, order_data)
        
        # User Information Section
        if footer_config.get('show_user_info', True):
            html += self._render_user_section(footer_config, user_data)
        
        # Custom Text Section
        if custom_text:
            html += f"""
                    <div class="footer-section custom-text">
                        <p class="custom-message">{custom_text}</p>
                    </div>
            """
        
        html += """
                </div>
                
                <div class="footer-bottom">
                    <div class="footer-left">
            """
        
        # Timestamp
        if footer_config.get('show_timestamp', True):
            html += f'<span class="timestamp" id="footer-timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>'
        
        html += """
                    </div>
                    <div class="footer-center">
            """
        
        # Page Info
        if footer_config.get('show_page_info', True):
            html += f'<span class="page-info">{data.get("page_title", "Document")}</span>'
        
        html += """
                    </div>
                    <div class="footer-right">
            """
        
        # Version
        if footer_config.get('show_version', False):
            html += f'<span class="version">v{footer_config.get("version", "1.0.0")}</span>'
        
        html += """
                    </div>
                </div>
            </div>
        </div>
        """
        
        return html
    
    def _render_business_section(self, footer_config: Dict) -> str:
        """Render business information section"""
        html = """
                    <div class="footer-section business-info">
        """
        
        if footer_config.get('company_logo', ''):
            html += f"""
                        <div class="footer-logo">
                            <img src="{footer_config['company_logo']}" alt="Company Logo" 
                                 style="max-height: {footer_config.get('logo_height', '30px')};">
                        </div>
            """
        
        business_name = footer_config.get('business_name', 'Restaurant POS')
        html += f'<div class="business-details"><h4>{business_name}</h4>'
        
        if footer_config.get('address', ''):
            html += f'<p class="footer-address">{footer_config["address"]}</p>'
        
        if footer_config.get('phone', ''):
            html += f'<p class="footer-phone">📞 {footer_config["phone"]}</p>'
        
        if footer_config.get('email', ''):
            html += f'<p class="footer-email">✉️ {footer_config["email"]}</p>'
        
        html += '</div></div>'
        return html
    
    def _render_receipt_section(self, footer_config: Dict, order_data: Dict) -> str:
        """Render receipt information section"""
        order_id = order_data.get('order_id', order_data.get('order_number', 'N/A'))
        order_date = order_data.get('order_date', order_data.get('created_at', ''))
        order_time = order_data.get('order_time', '')
        table_name = order_data.get('table_name', order_data.get('table_number', ''))
        
        html = """
                    <div class="footer-section receipt-info">
                        <h4>Receipt Details</h4>
                        <p class="receipt-number">Receipt #: {order_id}</p>
        """.format(order_id=order_id)
        
        if order_date:
            formatted_date = self._format_date(order_date)
            html += f'<p class="receipt-date">Date: {formatted_date}</p>'
        
        if order_time:
            html += f'<p class="receipt-time">Time: {order_time}</p>'
        
        if table_name:
            html += f'<p class="receipt-table">Table: {table_name}</p>'
        
        html += '</div>'
        return html
    
    def _render_user_section(self, footer_config: Dict, user_data: Dict) -> str:
        """Render user information section"""
        user_name = user_data.get('name', user_data.get('username', footer_config.get('default_user', 'Staff')))
        user_id = user_data.get('id', '')
        
        html = f"""
                    <div class="footer-section user-info">
                        <h4>Staff Information</h4>
                        <p class="user-name">Served by: {user_name}</p>
        """
        
        if footer_config.get('show_user_id', False) and user_id:
            html += f'<p class="user-id">ID: {user_id}</p>'
        
        html += '</div>'
        return html
    
    def _process_placeholders(self, text: str, data: Dict) -> str:
        """Process placeholders in custom text"""
        placeholders = {
            '{{user_name}}': data.get('user_data', {}).get('name', data.get('user_data', {}).get('username', 'Staff')),
            '{{date}}': datetime.now().strftime('%Y-%m-%d'),
            '{{time}}': datetime.now().strftime('%H:%M:%S'),
            '{{restaurant_name}}': data.get('footer_config', {}).get('business_name', 'Restaurant POS'),
            '{{order_id}}': str(data.get('order_data', {}).get('order_id', '')),
            '{{table_name}}': str(data.get('order_data', {}).get('table_name', ''))
        }
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def _format_date(self, date_str: str) -> str:
        """Format date string"""
        try:
            if isinstance(date_str, str):
                # Try different date formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.strftime('%d-%m-%Y')
                    except ValueError:
                        continue
                return date_str
            else:
                return date_str.strftime('%d-%m-%Y') if hasattr(date_str, 'strftime') else str(date_str)
        except Exception:
            return str(date_str)