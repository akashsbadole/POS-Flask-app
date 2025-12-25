"""
Email Service for Flask Web Version
Provides comprehensive email functionality for backup notifications
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
from datetime import datetime
import logging
import json
import threading
import queue
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import re

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class EmailConfig:
    """Email configuration data class"""
    # SMTP settings
    smtp_server: str = ""
    smtp_port: int = 587
    use_tls: bool = True
    use_ssl: bool = False
    
    # Authentication
    username: str = ""
    password: str = ""
    from_email: str = ""
    from_name: str = "POS Backup System"
    
    # Recipients
    recipients: List[str] = None
    
    # Email settings
    backup_notifications: bool = False
    test_emails: bool = True
    
    # Advanced settings
    max_attachment_size_mb: int = 25
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    def __post_init__(self):
        if self.recipients is None:
            self.recipients = []

@dataclass
class EmailQueueItem:
    """Email queue item data class"""
    id: str
    subject: str
    body: str
    recipients: List[str]
    attachments: List[str] = None
    priority: int = 1  # 1=high, 2=normal, 3=low
    created_at: datetime = None
    attempts: int = 0
    max_attempts: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.attachments is None:
            self.attachments = []

@dataclass
class EmailHistory:
    """Email history data class"""
    id: str
    subject: str
    recipients: List[str]
    sent_at: datetime
    status: str  # sent, failed, pending
    error_message: str = ""
    attachment_count: int = 0

class EmailService:
    """Advanced email service for backup notifications"""
    
    def __init__(self, config_path: str = "email_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        
        # Email queue and threading
        self.email_queue = queue.PriorityQueue()
        self.email_history: List[EmailHistory] = []
        self.queue_thread = None
        self.queue_running = False
        
        # Load email history
        self.load_email_history()
        
        # Start email queue processor
        if self.config.backup_notifications:
            self.start_queue_processor()
    
    def load_config(self) -> EmailConfig:
        """Load email configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                return EmailConfig(**config_data)
            else:
                # Create default config
                config = EmailConfig()
                self.save_config(config)
                return config
        except Exception as e:
            logger.error(f"Error loading email config: {e}")
            return EmailConfig()
    
    def save_config(self, config: EmailConfig = None):
        """Save email configuration to file"""
        try:
            if config is None:
                config = self.config
            
            with open(self.config_path, 'w') as f:
                json.dump(asdict(config), f, indent=2)
            
            self.config = config
            return True
        except Exception as e:
            logger.error(f"Error saving email config: {e}")
            return False
    
    def load_email_history(self):
        """Load email history from file"""
        try:
            history_path = os.path.join(os.path.dirname(self.config_path), "email_history.json")
            if os.path.exists(history_path):
                with open(history_path, 'r') as f:
                    history_data = json.load(f)
                
                for item in history_data:
                    item['sent_at'] = datetime.fromisoformat(item['sent_at'])
                    self.email_history.append(EmailHistory(**item))
        except Exception as e:
            logger.error(f"Error loading email history: {e}")
    
    def save_email_history(self):
        """Save email history to file"""
        try:
            history_path = os.path.join(os.path.dirname(self.config_path), "email_history.json")
            history_data = []
            
            for item in self.email_history:
                item_dict = asdict(item)
                item_dict['sent_at'] = item.sent_at.isoformat()
                history_data.append(item_dict)
            
            with open(history_path, 'w') as f:
                json.dump(history_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving email history: {e}")
    
    def validate_email_address(self, email: str) -> bool:
        """Validate email address format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_config(self) -> Tuple[bool, str]:
        """Validate email configuration"""
        if not self.config.smtp_server:
            return False, "SMTP server is required"
        
        if not self.config.username:
            return False, "Username is required"
        
        if not self.config.password:
            return False, "Password is required"
        
        if not self.config.from_email:
            return False, "From email is required"
        
        if not self.validate_email_address(self.config.from_email):
            return False, "Invalid from email address"
        
        if not self.config.recipients:
            return False, "At least one recipient is required"
        
        for recipient in self.config.recipients:
            if not self.validate_email_address(recipient):
                return False, f"Invalid recipient email: {recipient}"
        
        return True, "Configuration is valid"
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test SMTP connection"""
        try:
            # Validate config first
            is_valid, message = self.validate_config()
            if not is_valid:
                return False, message
            
            # Create SMTP connection
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                if self.config.use_tls:
                    server.starttls()
            
            # Login
            server.login(self.config.username, self.config.password)
            server.quit()
            
            return True, "Connection successful"
        
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def send_test_email(self) -> Tuple[bool, str]:
        """Send a test email"""
        try:
            # Validate config first
            is_valid, message = self.validate_config()
            if not is_valid:
                return False, message
            
            subject = "POS Backup System - Test Email"
            body = self.get_test_email_template()
            
            success, message = self._send_email_sync(
                subject=subject,
                body=body,
                recipients=self.config.recipients
            )
            
            if success:
                # Add to history
                history_item = EmailHistory(
                    id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    subject=subject,
                    recipients=self.config.recipients.copy(),
                    sent_at=datetime.now(),
                    status="sent"
                )
                self.email_history.append(history_item)
                self.save_email_history()
            
            return success, message
        
        except Exception as e:
            return False, f"Test email failed: {str(e)}"
    
    def send_backup_notification(self, backup_path: str, backup_info: Dict) -> Tuple[bool, str]:
        """Send backup notification email"""
        try:
            if not self.config.backup_notifications:
                return True, "Email notifications disabled"
            
            subject = f"POS Backup - {backup_info.get('status', 'Completed').title()}"
            body = self.get_backup_notification_template(backup_info)
            
            # Add backup file as attachment
            attachments = [backup_path] if os.path.exists(backup_path) else []
            
            # Queue email for sending
            email_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            queue_item = EmailQueueItem(
                id=email_id,
                subject=subject,
                body=body,
                recipients=self.config.recipients.copy(),
                attachments=attachments,
                priority=1  # High priority
            )
            
            self.email_queue.put((queue_item.priority, queue_item))
            
            logger.info(f"Backup notification queued: {email_id}")
            return True, "Backup notification queued"
        
        except Exception as e:
            logger.error(f"Error queuing backup notification: {e}")
            return False, f"Failed to queue notification: {str(e)}"
    
    def _send_email_sync(self, subject: str, body: str, recipients: List[str], 
                         attachments: List[str] = None) -> Tuple[bool, str]:
        """Send email synchronously"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.config.from_name, self.config.from_email))
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'html'))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        # Check file size
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        if file_size_mb > self.config.max_attachment_size_mb:
                            logger.warning(f"Attachment too large: {file_path} ({file_size_mb:.2f}MB)")
                            continue
                        
                        # Add attachment
                        with open(file_path, 'rb') as f:
                            part = MIMEApplication(f.read())
                            part.add_header(
                                'Content-Disposition',
                                'attachment',
                                filename=os.path.basename(file_path)
                            )
                            msg.attach(part)
            
            # Send email
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                if self.config.use_tls:
                    server.starttls()
            
            server.login(self.config.username, self.config.password)
            server.send_message(msg)
            server.quit()
            
            return True, "Email sent successfully"
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False, f"Failed to send email: {str(e)}"
    
    def start_queue_processor(self):
        """Start email queue processor thread"""
        if self.queue_running:
            return
        
        self.queue_running = True
        self.queue_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.queue_thread.start()
        logger.info("Email queue processor started")
    
    def stop_queue_processor(self):
        """Stop email queue processor thread"""
        self.queue_running = False
        if self.queue_thread:
            self.queue_thread.join(timeout=5)
        logger.info("Email queue processor stopped")
    
    def _process_queue(self):
        """Process email queue"""
        while self.queue_running:
            try:
                # Get next item from queue (with timeout)
                try:
                    priority, queue_item = self.email_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Send email with retry logic
                success = False
                error_message = ""
                
                for attempt in range(queue_item.max_attempts):
                    try:
                        success, message = self._send_email_sync(
                            subject=queue_item.subject,
                            body=queue_item.body,
                            recipients=queue_item.recipients,
                            attachments=queue_item.attachments
                        )
                        
                        if success:
                            break
                        else:
                            error_message = message
                            if attempt < queue_item.max_attempts - 1:
                                time.sleep(self.config.retry_delay_seconds)
                    
                    except Exception as e:
                        error_message = str(e)
                        if attempt < queue_item.max_attempts - 1:
                            time.sleep(self.config.retry_delay_seconds)
                
                # Add to history
                history_item = EmailHistory(
                    id=queue_item.id,
                    subject=queue_item.subject,
                    recipients=queue_item.recipients.copy(),
                    sent_at=datetime.now(),
                    status="sent" if success else "failed",
                    error_message=error_message,
                    attachment_count=len(queue_item.attachments or [])
                )
                self.email_history.append(history_item)
                self.save_email_history()
                
                # Log result
                if success:
                    logger.info(f"Email sent successfully: {queue_item.id}")
                else:
                    logger.error(f"Email failed after {queue_item.max_attempts} attempts: {queue_item.id}")
                
                # Mark task as done
                self.email_queue.task_done()
            
            except Exception as e:
                logger.error(f"Error in email queue processor: {e}")
    
    def get_test_email_template(self) -> str:
        """Get test email template"""
        return f"""
        <html>
        <body>
            <h2>POS Backup System - Test Email</h2>
            <p>This is a test email from your POS Backup System.</p>
            <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Server:</strong> {self.config.smtp_server}:{self.config.smtp_port}</p>
            <p><strong>From:</strong> {self.config.from_name} <{self.config.from_email}></p>
            <hr>
            <p><em>If you received this email, your email configuration is working correctly.</em></p>
        </body>
        </html>
        """
    
    def get_backup_notification_template(self, backup_info: Dict) -> str:
        """Get backup notification email template"""
        status = backup_info.get('status', 'Unknown')
        backup_type = backup_info.get('backup_type', 'Full')
        file_size = backup_info.get('file_size_mb', 0)
        created_at = backup_info.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Color based on status
        if status.lower() == 'success':
            status_color = '#28a745'
            status_icon = '✅'
        elif status.lower() == 'failed':
            status_color = '#dc3545'
            status_icon = '❌'
        else:
            status_color = '#ffc107'
            status_icon = '⚠️'
        
        # Get footer for emails
        footer_html = self._get_email_footer()
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #333; margin: 0;">POS Backup System</h1>
                    <p style="color: #666; margin: 5px 0 0 0;">Automated Backup Notification</p>
                </div>
                
                <div style="background-color: {status_color}20; border-left: 4px solid {status_color}; padding: 15px; margin: 20px 0; border-radius: 0 5px 5px 0;">
                    <h2 style="margin: 0; color: {status_color};">
                        {status_icon} Backup {status.title()}
                    </h2>
                </div>
                
                <div style="margin: 20px 0;">
                    <h3 style="color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px;">Backup Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold; width: 150px;">Status:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; color: {status_color}; font-weight: bold;">{status.title()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Type:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{backup_type.title()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Created:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{created_at}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">File Size:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{file_size} MB</td>
                        </tr>
                    </table>
                </div>
                
                <div style="margin: 20px 0;">
                    <h3 style="color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px;">Data Included</h3>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        {"".join([f"<li>{item.replace('_', ' ').title()}</li>" for item in backup_info.get('includes', [])])}
                    </ul>
                </div>
                
                <div style="margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 5px; text-align: center;">
                    <p style="margin: 0; color: #666;">
                        <strong>This is an automated message from your POS Backup System.</strong><br>
                        Please do not reply to this email.
                    </p>
                </div>
                
                {footer_html}
            </div>
        </body>
        </html>
        """
    
    def _get_email_footer(self) -> str:
        """Get footer HTML for emails"""
        try:
            from models.settings import Settings
            footer_settings = Settings.get_footer_settings()
            restaurant_info = Settings.get_restaurant_info()
            
            if not footer_settings.get('footer_enabled', 'true').lower() == 'true':
                return ""
            
            # Build footer based on settings
            footer_lines = []
            
            # Custom text
            custom_text = footer_settings.get('footer_custom_text', 'Thank you for your business!')
            if custom_text:
                footer_lines.append(f"<p style='margin: 5px 0; color: #666; font-size: 11px;'>{custom_text}</p>")
            
            # Business info
            if footer_settings.get('footer_show_business_info', 'true').lower() == 'true':
                business_parts = []
                if restaurant_info.get('restaurant_name'):
                    business_parts.append(restaurant_info['restaurant_name'])
                if restaurant_info.get('restaurant_phone'):
                    business_parts.append(restaurant_info['restaurant_phone'])
                if restaurant_info.get('restaurant_email'):
                    business_parts.append(restaurant_info['restaurant_email'])
                
                if business_parts:
                    footer_lines.append(f"<p style='margin: 5px 0; color: #666; font-size: 10px;'>{' | '.join(business_parts)}</p>")
            
            # Timestamp
            footer_lines.append(f"<p style='margin: 10px 0 0; color: #999; font-size: 9px; border-top: 1px solid #eee; padding-top: 10px;'>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | POS Backup System v1.0</p>")
            
            if footer_lines:
                return f"""
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    {''.join(footer_lines)}
                </div>
                """
            
            return ""
            
        except Exception as e:
            # Fallback to basic footer if settings fail
            return f"""
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                <p style="margin: 10px 0 0; color: #999; font-size: 9px;">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | POS Backup System v1.0</p>
            </div>
            """
    
    def get_email_history(self, limit: int = 50) -> List[Dict]:
        """Get email history"""
        try:
            # Sort by sent_at descending
            sorted_history = sorted(self.email_history, key=lambda x: x.sent_at, reverse=True)
            
            # Convert to dict and limit
            history_dicts = []
            for item in sorted_history[:limit]:
                item_dict = asdict(item)
                item_dict['sent_at'] = item.sent_at.strftime('%Y-%m-%d %H:%M:%S')
                history_dicts.append(item_dict)
            
            return history_dicts
        
        except Exception as e:
            logger.error(f"Error getting email history: {e}")
            return []
    
    def get_queue_status(self) -> Dict:
        """Get email queue status"""
        return {
            'queue_size': self.email_queue.qsize(),
            'queue_running': self.queue_running,
            'total_sent': len([h for h in self.email_history if h.status == 'sent']),
            'total_failed': len([h for h in self.email_history if h.status == 'failed']),
            'total_pending': len([h for h in self.email_history if h.status == 'pending'])
        }
    
    def clear_email_history(self, older_than_days: int = 30):
        """Clear email history older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            original_count = len(self.email_history)
            
            self.email_history = [
                h for h in self.email_history 
                if h.sent_at > cutoff_date
            ]
            
            cleared_count = original_count - len(self.email_history)
            if cleared_count > 0:
                self.save_email_history()
                logger.info(f"Cleared {cleared_count} old email history entries")
            
            return cleared_count
        
        except Exception as e:
            logger.error(f"Error clearing email history: {e}")
            return 0
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop_queue_processor()
        except:
            pass