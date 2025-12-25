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
        self.settings = Settings.get_all_as_dict()
        self.default_printer = self.settings.get('thermal_printer_name', 'Default')
        self.paper_width = self.settings.get('paper_width', '80mm')  # Default to 80mm
        self.auto_print = self.settings.get('auto_print_enabled', 'true').lower() == 'true'
        
    def print_bill(self, order_id, copies=1, printer_name=None):
        """Print bill for order"""
        try:
            from models import Order
            
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            # Track print operation
            printer_name = printer_name or self.default_printer
            print_record = PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='bill',
                print_method='thermal',
                copies=copies,
                printer_name=printer_name,
                success=True
            )
            
            # Return print URL for frontend
            return {
                'success': True,
                'print_url': f'/orders/print/{order_id}?auto_print=true',
                'message': f'Bill print job created for order {order.order_number}',
                'print_record_id': print_record.id if print_record else None
            }
            
        except Exception as e:
            # Log failed print
            PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='bill',
                print_method='thermal',
                copies=copies,
                printer_name=printer_name,
                success=False,
                error_message=str(e)
            )
            
            return {'success': False, 'message': f'Print failed: {str(e)}'}
    
    def print_kot(self, order_id, copies=1, printer_name=None):
        """Print KOT for order"""
        try:
            from models import Order
            
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            # Track print operation
            printer_name = printer_name or self.default_printer
            print_record = PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='kot',
                print_method='thermal',
                copies=copies,
                printer_name=printer_name,
                success=True
            )
            
            # Return print URL for frontend
            return {
                'success': True,
                'print_url': f'/kot/print/{order_id}?auto_print=true',
                'message': f'KOT print job created for order {order.order_number}',
                'print_record_id': print_record.id if print_record else None
            }
            
        except Exception as e:
            # Log failed print
            PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='kot',
                print_method='thermal',
                copies=copies,
                printer_name=printer_name,
                success=False,
                error_message=str(e)
            )
            
            return {'success': False, 'message': f'Print failed: {str(e)}'}
    
    def print_invoice_pdf(self, order_id, copies=1):
        """Generate and print invoice PDF"""
        try:
            from models import Order
            from utils.pdf_invoice_generator import generate_invoice_pdf
            
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            # Track print operation
            print_record = PrintHistory.create_print_record(
                order_id=order_id,
                user_id=current_user.id if current_user.is_authenticated else 1,
                print_type='invoice',
                print_method='pdf',
                copies=copies,
                success=True
            )
            
            # Generate PDF
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
        try:
            # This would interface with actual printer drivers
            # For now, return a simulated status
            return {
                'online': True,
                'paper_width': self.paper_width,
                'printer_name': self.default_printer,
                'status': 'Ready',
                'last_check': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'online': False,
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def configure_printer(self, printer_config):
        """Configure thermal printer settings"""
        try:
            # Update settings
            for key, value in printer_config.items():
                if hasattr(Settings, 'set'):
                    Settings.set(key, value)
                else:
                    # Direct database update if Settings.set is not available
                    self._update_setting(key, value)
            
            # Refresh settings
            self.settings = Settings.get_all_as_dict()
            self.default_printer = self.settings.get('thermal_printer_name', 'Default')
            self.paper_width = self.settings.get('paper_width', '80mm')
            self.auto_print = self.settings.get('auto_print_enabled', 'true').lower() == 'true'
            
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

# Global print manager instance
print_manager = PrintManager()

def get_print_manager():
    """Get the global print manager instance"""
    return print_manager

# Helper functions for route handlers
def print_order_bill(order_id, copies=1, printer_name=None):
    """Helper function to print order bill"""
    return print_manager.print_bill(order_id, copies, printer_name)

def print_order_kot(order_id, copies=1, printer_name=None):
    """Helper function to print order KOT"""
    return print_manager.print_kot(order_id, copies, printer_name)

def generate_order_invoice_pdf(order_id, copies=1):
    """Helper function to generate order invoice PDF"""
    return print_manager.print_invoice_pdf(order_id, copies)

def get_printer_status():
    """Helper function to get printer status"""
    return print_manager.get_printer_status()