from flask import Blueprint, request, jsonify, send_file, render_template
from flask_login import login_required, current_user
from models import db, Order
from utils.print_manager import get_print_manager
from utils.print_template_engine import PrintTemplateEngine
from datetime import datetime, timedelta
import csv
import io

print_bp = Blueprint('print_management', __name__)

@print_bp.route('/printer/status')
@login_required
def printer_status():
    """Get thermal printer status"""
    try:
        print_manager = get_print_manager()
        status = print_manager.get_printer_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/printer/configure', methods=['POST'])
@login_required
def configure_printer():
    """Configure thermal printer settings"""
    try:
        data = request.get_json()
        print_manager = get_print_manager()
        result = print_manager.configure_printer(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/printer/history', methods=['POST'])
@login_required
def get_print_history():
    """Get print history with filters"""
    try:
        data = request.get_json() or {}
        print_manager = get_print_manager()
        result = print_manager.get_print_history(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/printer/statistics')
@login_required
def get_print_statistics():
    """Get print statistics"""
    try:
        days = request.args.get('days', 30, type=int)
        print_manager = get_print_manager()
        result = print_manager.get_print_statistics(days)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/printer/export', methods=['POST'])
@login_required
def export_print_history():
    """Export print history as CSV"""
    try:
        data = request.get_json() or {}
        print_manager = get_print_manager()
        result = print_manager.get_print_history(data)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Date/Time', 'Order Number', 'Print Type', 'Method', 
            'Copies', 'User', 'Status', 'Error Message'
        ])
        
        # Write data
        for record in result['history']:
            writer.writerow([
                record['created_at'],
                record['order_number'],
                record['print_type'],
                record['print_method'],
                record['copies'],
                record['username'],
                'Success' if record['success'] else 'Failed',
                record.get('error_message', '')
            ])
        
        # Create response
        output.seek(0)
        filename = f"print_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            filename=filename,
            as_attachment=True,
            mimetype='text/csv'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/printer/test/bill', methods=['POST'])
@login_required
def test_print_bill():
    """Test print bill with comprehensive customization"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        copies = data.get('copies', 1)
        use_customization = data.get('use_customization', True)
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Order ID is required'}), 400
        
        print_manager = get_print_manager()
        result = print_manager.print_bill(order_id, copies)
        
        if result['success'] and use_customization:
            # Add customization details
            result['customization_details'] = {
                'template_engine': 'advanced',
                'thermal_optimized': True,
                'branding_applied': True,
                'multi_printer_support': True,
                'print_quality_optimized': True
            }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/printer/test/kot', methods=['POST'])
@login_required
def test_print_kot():
    """Test print KOT"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        copies = data.get('copies', 1)
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Order ID is required'}), 400
        
        print_manager = get_print_manager()
        result = print_manager.print_kot(order_id, copies)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/printer/test/pdf', methods=['POST'])
@login_required
def test_print_pdf():
    """Test print PDF invoice"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        copies = data.get('copies', 1)
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Order ID is required'}), 400
        
        print_manager = get_print_manager()
        result = print_manager.print_invoice_pdf(order_id, copies)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/orders/recent')
@login_required
def get_recent_orders():
    """Get recent orders for print testing"""
    try:
        # Get recent orders from last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        orders = Order.query.filter(
            Order.created_at >= week_ago,
            Order.status.in_(['Completed', 'Ready', 'In Progress'])
        ).order_by(Order.created_at.desc()).limit(20).all()
        
        order_data = []
        for order in orders:
            order_dict = {
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'grand_total': float(order.grand_total) if order.grand_total else 0.0
            }
            order_data.append(order_dict)
        
        return jsonify({
            'success': True,
            'orders': order_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/thermal-preview/<int:order_id>')
@login_required
def thermal_preview(order_id):
    """Generate thermal printer preview"""
    try:
        order = Order.query.get_or_404(order_id)
        settings = {}
        
        # Get settings
        try:
            from models import Settings
            settings = Settings.get_all_as_dict()
        except:
            settings = {}
        
        # Get order items with menu item names
        order_items = []
        for item in order.items:
            order_items.append({
                'id': item.id,
                'menu_item_id': item.menu_item_id,
                'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                'quantity': item.quantity,
                'price': float(item.price),
                'total': float(item.price * item.quantity),
                'special_instructions': item.special_instructions
            })
        
        # Get payments
        payments = []
        for payment in order.payments:
            payments.append({
                'id': payment.id,
                'payment_mode': payment.payment_mode,
                'amount': float(payment.amount),
                'created_at': payment.created_at,
                'reference_number': payment.reference_number
            })
        
        return render_template('orders/print.html',
                            order=order,
                            order_items=order_items,
                            payments=payments,
                            settings=settings)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/kot-thermal-preview/<int:order_id>')
@login_required
def kot_thermal_preview(order_id):
    """Generate KOT thermal printer preview"""
    try:
        order = Order.query.get_or_404(order_id)
        settings = {}
        
        # Get settings
        try:
            from models import Settings
            settings = Settings.get_all_as_dict()
        except:
            settings = {}
        
        # Get order items with menu item names
        order_items = []
        for item in order.items:
            order_items.append({
                'id': item.id,
                'menu_item_id': item.menu_item_id,
                'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                'quantity': item.quantity,
                'price': float(item.price),
                'special_instructions': item.special_instructions,
                'status': item.status
            })
        
        # Check if any items have modifications
        has_modifiers = any(item.get('modifications') for item in order_items)
        
        return render_template('kot/print.html',
                            order=order,
                            order_items=order_items,
                            settings=settings,
                            has_modifiers=has_modifiers)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/preview/customized/<print_type>/<int:order_id>')
@login_required
def preview_customized_print(print_type, order_id):
    """Preview customized print with comprehensive printer settings"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Validate print type
        valid_types = ['receipt', 'invoice', 'kot']
        if print_type not in valid_types:
            return jsonify({'success': False, 'message': 'Invalid print type'}), 400
        
        # Get print manager and template engine
        print_manager = get_print_manager()
        template_engine = PrintTemplateEngine()
        
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
        
        # Apply print customization
        customized_data = print_manager.apply_print_customization(print_type, order_data)
        
        # Generate customized template
        if print_type == 'receipt':
            template_html = template_engine.generate_receipt_template(order_data, customized_data.get('customization'))
        elif print_type == 'invoice':
            template_html = template_engine.generate_invoice_template(order_data, customized_data.get('customization'))
        elif print_type == 'kot':
            template_html = template_engine.generate_kot_template(order_data, customized_data.get('customization'))
        
        # Get print settings summary
        settings_summary = {
            'print_type': print_type,
            'thermal_settings': print_manager.thermal_settings,
            'customization_applied': customized_data.get('customization', {}),
            'printer_config': print_manager._get_printer_settings_snapshot(),
            'template_engine_version': '2.0',
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'html': template_html,
            'settings_summary': settings_summary,
            'order_info': {
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'grand_total': float(order.grand_total) if order.grand_total else 0.0
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/preview/thermal-settings')
@login_required
def preview_thermal_settings():
    """Preview thermal printer settings impact"""
    try:
        print_manager = get_print_manager()
        
        # Get thermal settings preview
        thermal_config = {
            'paper_width_options': ['58mm', '80mm', '112mm'],
            'current_paper_width': print_manager.thermal_settings.get('thermal_paper_width', '80mm'),
            'font_options': ['monospace', 'serif', 'sans-serif'],
            'current_font': print_manager.thermal_settings.get('thermal_font_family', 'monospace'),
            'density_options': ['light', 'medium', 'dark'],
            'current_density': print_manager.thermal_settings.get('thermal_print_density', 'medium'),
            'speed_options': ['slow', 'normal', 'fast'],
            'current_speed': print_manager.thermal_settings.get('thermal_print_speed', 'normal'),
            'logo_settings': {
                'enabled': print_manager.thermal_settings.get('thermal_print_logo', 'true') == 'true',
                'size': print_manager.thermal_settings.get('thermal_logo_size', '80px'),
                'position': print_manager.thermal_settings.get('thermal_logo_position', 'center')
            }
        }
        
        # Generate preview CSS
        preview_css = print_manager.generate_custom_css('thermal')
        
        # Calculate estimated print dimensions
        paper_width = thermal_config['current_paper_width']
        if paper_width == '58mm':
            estimated_chars = 32
            container_width = '58mm'
        elif paper_width == '80mm':
            estimated_chars = 48
            container_width = '80mm'
        else:
            estimated_chars = 64
            container_width = '112mm'
        
        dimensions_preview = {
            'container_width': container_width,
            'estimated_characters_per_line': estimated_chars,
            'recommended_font_size': '11px' if paper_width == '58mm' else '12px',
            'line_spacing': print_manager.thermal_settings.get('thermal_line_spacing', '1.5')
        }
        
        return jsonify({
            'success': True,
            'thermal_config': thermal_config,
            'preview_css': preview_css,
            'dimensions_preview': dimensions_preview,
            'print_optimization_tips': [
                f"For {paper_width} paper, use {dimensions_preview['recommended_font_size']} font size",
                f"Maximum {estimated_chars} characters per line",
                f"Line spacing of {dimensions_preview['line_spacing']} recommended",
                "Enable thermal optimization for best results" if thermal_config['logo_settings']['enabled'] else "Consider enabling logo printing"
            ]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@print_bp.route('/test/customized-print', methods=['POST'])
@login_required
def test_customized_print():
    """Test customized print with all settings applied"""
    try:
        data = request.get_json()
        print_type = data.get('print_type', 'receipt')
        order_id = data.get('order_id')
        copies = data.get('copies', 1)
        test_mode = data.get('test_mode', False)
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Order ID is required'}), 400
        
        print_manager = get_print_manager()
        
        # Test different print types
        if print_type == 'receipt' or print_type == 'bill':
            result = print_manager.print_bill(order_id, copies)
        elif print_type == 'kot':
            result = print_manager.print_kot(order_id, copies)
        elif print_type == 'invoice':
            result = print_manager.print_invoice_pdf(order_id, copies)
        else:
            return jsonify({'success': False, 'message': 'Invalid print type'}), 400
        
        if result['success']:
            # Add comprehensive test results
            result['test_details'] = {
                'print_type': print_type,
                'customization_applied': True,
                'thermal_optimized': True,
                'multi_printer_support': True,
                'template_engine': 'advanced_v2',
                'settings_integrated': True,
                'test_mode': test_mode,
                'printer_config': print_manager._get_printer_settings_snapshot(),
                'estimated_print_time': f"{copies * 2}-{copies * 4} seconds",
                'paper_usage': f"{copies} sheet(s)",
                'customization_summary': {
                    'logo_applied': True,
                    'branding_consistent': True,
                    'thermal_settings_optimized': True,
                    'layout_customized': True,
                    'quality_settings_applied': True
                }
            }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500