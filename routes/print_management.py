from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Order
from utils.print_manager import get_print_manager
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
    """Test print bill"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        copies = data.get('copies', 1)
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Order ID is required'}), 400
        
        print_manager = get_print_manager()
        result = print_manager.print_bill(order_id, copies)
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