"""
Email Notification System for Flask POS Application
Handles various email notifications including orders, low stock alerts, and backup notifications
"""

import smtplib
import json
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app
from typing import List, Dict, Optional, Any

class EmailNotifier:
    """Email notification manager"""
    
    def __init__(self, config_file: str = 'email_config.json'):
        self.config_file = config_file
        self.config = self._load_config()
        self.smtp_server = None
        self.connected = False
    
    def _load_config(self) -> Dict[str, Any]:
        """Load email configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading email config: {e}")
        
        # Default configuration
        return {
            "smtp_server": "",
            "smtp_port": 587,
            "use_tls": True,
            "use_ssl": False,
            "username": "",
            "password": "",
            "from_email": "",
            "from_name": "POS System",
            "recipients": [],
            "backup_notifications": True,
            "test_emails": True,
            "max_attachment_size_mb": 25,
            "retry_attempts": 3,
            "retry_delay_seconds": 5
        }
    
    def _save_config(self) -> bool:
        """Save email configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving email config: {e}")
            return False
    
    def _connect(self) -> bool:
        """Connect to SMTP server"""
        if self.connected:
            return True
        
        if not self.config.get('smtp_server') or not self.config.get('username'):
            return False
        
        try:
            if self.config.get('use_ssl'):
                self.smtp_server = smtplib.SMTP_SSL(
                    self.config['smtp_server'], 
                    self.config['smtp_port']
                )
            else:
                self.smtp_server = smtplib.SMTP(
                    self.config['smtp_server'], 
                    self.config['smtp_port']
                )
                
                if self.config.get('use_tls', True):
                    self.smtp_server.starttls()
            
            self.smtp_server.login(
                self.config['username'], 
                self.config['password']
            )
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"Error connecting to SMTP server: {e}")
            return False
    
    def _disconnect(self):
        """Disconnect from SMTP server"""
        if self.smtp_server and self.connected:
            try:
                self.smtp_server.quit()
            except:
                pass
            finally:
                self.connected = False
                self.smtp_server = None
    
    def _send_email(self, to_emails: List[str], subject: str, body: str, 
                   attachments: List[str] = None) -> bool:
        """Send email with retry logic"""
        if not to_emails:
            return False
        
        for attempt in range(self.config.get('retry_attempts', 3)):
            try:
                if not self._connect():
                    return False
                
                # Create message
                msg = MIMEMultipart()
                msg['From'] = f"{self.config.get('from_name', 'POS System')} <{self.config.get('from_email')}>"
                msg['To'] = ', '.join(to_emails)
                msg['Subject'] = subject
                
                # Add body
                msg.attach(MIMEText(body, 'html'))
                
                # Add attachments
                if attachments:
                    for file_path in attachments:
                        if os.path.exists(file_path):
                            self._add_attachment(msg, file_path)
                
                # Send email
                self.smtp_server.send_message(msg)
                return True
                
            except Exception as e:
                print(f"Email send attempt {attempt + 1} failed: {e}")
                if attempt < self.config.get('retry_attempts', 3) - 1:
                    import time
                    time.sleep(self.config.get('retry_delay_seconds', 5))
        
        return False
    
    def _add_attachment(self, msg: MIMEMultipart, file_path: str):
        """Add attachment to email"""
        try:
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                
            encoders.encode_base64(part)
            
            filename = os.path.basename(file_path)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            msg.attach(part)
            
        except Exception as e:
            print(f"Error attaching file {file_path}: {e}")
    
    def send_test_email(self, to_email: str = None) -> bool:
        """Send test email"""
        if not self.config.get('smtp_server'):
            return False
        
        recipient = to_email or self.config.get('from_email')
        if not recipient:
            return False
        
        subject = "POS System - Test Email"
        body = """
        <html>
        <body>
            <h2>POS System Test Email</h2>
            <p>This is a test email from your Restaurant POS system.</p>
            <p><strong>Timestamp:</strong> {}</p>
            <p><strong>Status:</strong> Email configuration is working correctly!</p>
            <hr>
            <p><small>This is an automated message from the POS System</small></p>
        </body>
        </html>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        return self._send_email([recipient], subject, body)
    
    def send_order_notification(self, order_data: Dict[str, Any]) -> bool:
        """Send order notification email"""
        if not self.config.get('backup_notifications', True):
            return True
        
        subject = f"New Order - {order_data.get('order_number', 'Unknown')}"
        
        # Create HTML body
        body = f"""
        <html>
        <body>
            <h2>New Order Received</h2>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                <tr><td><strong>Order Number:</strong></td><td>{order_data.get('order_number', 'N/A')}</td></tr>
                <tr><td><strong>Order Type:</strong></td><td>{order_data.get('order_type', 'N/A')}</td></tr>
                <tr><td><strong>Customer:</strong></td><td>{order_data.get('customer_name', 'Walk-in')}</td></tr>
                <tr><td><strong>Table:</strong></td><td>{order_data.get('table_name', 'N/A')}</td></tr>
                <tr><td><strong>Total Amount:</strong></td><td>₹{order_data.get('grand_total', 0):.2f}</td></tr>
                <tr><td><strong>Time:</strong></td><td>{order_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</td></tr>
            </table>
            
            <h3>Order Items:</h3>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                <tr>
                    <th>Item</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>Total</th>
                </tr>
        """
        
        # Add order items
        for item in order_data.get('items', []):
            body += f"""
                <tr>
                    <td>{item.get('name', 'N/A')}</td>
                    <td>{item.get('quantity', 0)}</td>
                    <td>₹{item.get('price', 0):.2f}</td>
                    <td>₹{item.get('total', item.get('price', 0) * item.get('quantity', 0)):.2f}</td>
                </tr>
            """
        
        body += """
            </table>
            <hr>
            <p><small>This is an automated message from the POS System</small></p>
        </body>
        </html>
        """
        
        recipients = self.config.get('recipients', [])
        if recipients:
            return self._send_email(recipients, subject, body)
        
        return True
    
    def send_low_stock_alert(self, items: List[Dict[str, Any]]) -> bool:
        """Send low stock alert email"""
        if not items or not self.config.get('backup_notifications', True):
            return True
        
        subject = f"Low Stock Alert - {len(items)} Items Need Restocking"
        
        body = """
        <html>
        <body>
            <h2>⚠️ Low Stock Alert</h2>
            <p>The following items are running low on stock and need to be restocked:</p>
            
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                <tr>
                    <th>Item Name</th>
                    <th>Current Stock</th>
                    <th>Min Stock Level</th>
                    <th>Unit</th>
                    <th>Status</th>
                </tr>
        """
        
        for item in items:
            status = "⚠️ Low Stock" if item.get('stock_quantity', 0) > 0 else "❌ Out of Stock"
            body += f"""
                <tr>
                    <td>{item.get('name', 'N/A')}</td>
                    <td>{item.get('stock_quantity', 0)}</td>
                    <td>{item.get('min_stock_level', 0)}</td>
                    <td>{item.get('unit', 'pcs')}</td>
                    <td><strong>{status}</strong></td>
                </tr>
            """
        
        body += f"""
            </table>
            
            <p><strong>Alert Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Please restock these items as soon as possible to avoid order disruptions.</p>
            <hr>
            <p><small>This is an automated message from the POS System</small></p>
        </body>
        </html>
        """
        
        recipients = self.config.get('recipients', [])
        if recipients:
            return self._send_email(recipients, subject, body)
        
        return True
    
    def send_backup_notification(self, backup_info: Dict[str, Any]) -> bool:
        """Send backup completion notification"""
        if not self.config.get('backup_notifications', True):
            return True
        
        status = "✅ Successful" if backup_info.get('success') else "❌ Failed"
        subject = f"Backup {status} - {backup_info.get('type', 'Database').capitalize()}"
        
        body = f"""
        <html>
        <body>
            <h2>Backup Notification</h2>
            <p><strong>Status:</strong> {status}</p>
            
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                <tr><td><strong>Backup Type:</strong></td><td>{backup_info.get('type', 'Database')}</td></tr>
                <tr><td><strong>File Name:</strong></td><td>{backup_info.get('filename', 'N/A')}</td></tr>
                <tr><td><strong>File Size:</strong></td><td>{backup_info.get('size', 'N/A')}</td></tr>
                <tr><td><strong>Time:</strong></td><td>{backup_info.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</td></tr>
                <tr><td><strong>Duration:</strong></td><td>{backup_info.get('duration', 'N/A')}</td></tr>
            </table>
            
            {"<p><strong>Error:</strong> " + backup_info.get('error', '') + "</p>" if not backup_info.get('success') else ""}
            
            <hr>
            <p><small>This is an automated message from the POS System</small></p>
        </body>
        </html>
        """
        
        recipients = self.config.get('recipients', [])
        if recipients:
            # Attach backup file if successful and file exists
            attachments = []
            if backup_info.get('success') and backup_info.get('file_path'):
                attachments.append(backup_info['file_path'])
            
            return self._send_email(recipients, subject, body, attachments)
        
        return True
    
    def send_daily_report(self, report_data: Dict[str, Any]) -> bool:
        """Send daily sales report email"""
        if not self.config.get('backup_notifications', True):
            return True
        
        subject = f"Daily Sales Report - {report_data.get('date', datetime.now().strftime('%Y-%m-%d'))}"
        
        body = f"""
        <html>
        <body>
            <h2>📊 Daily Sales Report</h2>
            <p><strong>Date:</strong> {report_data.get('date', datetime.now().strftime('%Y-%m-%d'))}</p>
            
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                <tr><td><strong>Total Orders:</strong></td><td>{report_data.get('total_orders', 0)}</td></tr>
                <tr><td><strong>Total Revenue:</strong></td><td>₹{report_data.get('total_revenue', 0):.2f}</td></tr>
                <tr><td><strong>Average Order Value:</strong></td><td>₹{report_data.get('avg_order_value', 0):.2f}</td></tr>
                <tr><td><strong>CGST Collected:</strong></td><td>₹{report_data.get('cgst_total', 0):.2f}</td></tr>
                <tr><td><strong>SGST Collected:</strong></td><td>₹{report_data.get('sgst_total', 0):.2f}</td></tr>
                <tr><td><strong>Total GST:</strong></td><td>₹{report_data.get('total_gst', 0):.2f}</td></tr>
            </table>
            
            {"<h3>Top Selling Items:</h3>" + self._format_top_items(report_data.get('top_items', [])) if report_data.get('top_items') else ""}
            
            <hr>
            <p><small>This is an automated message from the POS System</small></p>
        </body>
        </html>
        """
        
        recipients = self.config.get('recipients', [])
        if recipients:
            # Attach report file if provided
            attachments = []
            if report_data.get('report_file'):
                attachments.append(report_data['report_file'])
            
            return self._send_email(recipients, subject, body, attachments)
        
        return True
    
    def _format_top_items(self, items: List[Dict[str, Any]]) -> str:
        """Format top selling items for email"""
        if not items:
            return ""
        
        html = """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
            <tr>
                <th>Item Name</th>
                <th>Quantity Sold</th>
                <th>Revenue</th>
            </tr>
        """
        
        for item in items[:5]:  # Top 5 items
            html += f"""
                <tr>
                    <td>{item.get('name', 'N/A')}</td>
                    <td>{item.get('quantity', 0)}</td>
                    <td>₹{item.get('revenue', 0):.2f}</td>
                </tr>
            """
        
        html += "</table>"
        return html
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update email configuration"""
        self.config.update(new_config)
        return self._save_config()
    
    def test_connection(self) -> Dict[str, Any]:
        """Test email configuration"""
        result = {
            'success': False,
            'message': '',
            'details': {}
        }
        
        try:
            if not self.config.get('smtp_server'):
                result['message'] = 'SMTP server not configured'
                return result
            
            if not self.config.get('username'):
                result['message'] = 'Username not configured'
                return result
            
            if not self.config.get('password'):
                result['message'] = 'Password not configured'
                return result
            
            # Test connection
            if self._connect():
                result['success'] = True
                result['message'] = 'Connection successful'
                result['details'] = {
                    'server': self.config['smtp_server'],
                    'port': self.config['smtp_port'],
                    'use_tls': self.config.get('use_tls', True),
                    'use_ssl': self.config.get('use_ssl', False)
                }
            else:
                result['message'] = 'Failed to connect to SMTP server'
            
        except Exception as e:
            result['message'] = f'Connection error: {str(e)}'
        
        finally:
            self._disconnect()
        
        return result

# Global email notifier instance
email_notifier = EmailNotifier()
