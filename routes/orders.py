from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Order, OrderItem, MenuItem, Payment, Table, Settings, Category
from datetime import datetime, timedelta
from decimal import Decimal
from utils.pdf_invoice_generator import generate_invoice_pdf, generate_kot_pdf
import os

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/new')
@login_required
def new_order():
    """Create new order page - split screen layout"""
    # Get menu items and categories for left panel
    menu_items = MenuItem.query.filter_by(is_active=True).all()
    categories = [cat for cat in Category.query.filter_by(is_active=True).all()]
    tables = Table.query.filter_by(status='Available', is_active=True).all()
    
    # Convert objects to dictionaries for JSON serialization
    categories_dict = [{'id': cat.id, 'name': cat.name, 'description': cat.description, 'is_active': cat.is_active} for cat in categories]
    menu_items_dict = [{'id': item.id, 'name': item.name, 'description': item.description, 'price': float(item.price), 'category_id': item.category_id, 'stock_quantity': item.stock_quantity, 'min_stock_level': item.min_stock_level, 'is_active': item.is_active} for item in menu_items]
    tables_dict = [{'id': table.id, 'table_number': table.table_number, 'capacity': table.capacity, 'status': table.status, 'location': table.location, 'is_active': table.is_active} for table in tables]
    
    return render_template('orders/new.html',
                        menu_items=menu_items_dict,
                        categories=categories_dict,
                        tables=tables_dict)

@orders_bp.route('/list')
@login_required
def list_orders():
    """List all orders"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    
    query = Order.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Order.created_at) == filter_date)
        except ValueError:
            pass
    
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('orders/list.html', orders=orders, 
                        status_filter=status_filter, date_filter=date_filter)

@orders_bp.route('/view/<int:order_id>')
@login_required
def view_order(order_id):
    """View order details"""
    order = Order.query.get_or_404(order_id)
    payments = Payment.get_by_order(order_id)
    
    return render_template('orders/view.html', order=order, payments=payments)

@orders_bp.route('/save', methods=['POST'])
@login_required
def save_order():
    """Save order via AJAX"""
    try:
        data = request.get_json()
        
        # Create or update order
        if data.get('order_id'):
            order = Order.query.get(data['order_id'])
            if not order:
                return jsonify({'success': False, 'message': 'Order not found'}), 404
        else:
            order = Order()
            order.order_number = generate_order_number()
            order.status = 'New'
            order.created_by = current_user.id
        
        # Update order details
        order.customer_name = data.get('customer_name', '')
        order.customer_mobile = data.get('customer_mobile', '')
        order.order_type = data.get('order_type', 'Dine-in')
        order.table_id = data.get('table_id') if data.get('table_id') else None
        order.special_instructions = data.get('special_instructions', '')
        
        # Calculate totals
        items = data.get('items', [])
        subtotal = Decimal('0')
        
        for item_data in items:
            item = MenuItem.query.get(item_data['menu_item_id'])
            if item:
                quantity = Decimal(str(item_data['quantity']))
                price = Decimal(str(item.price))
                subtotal += price * quantity
        
        order.subtotal = subtotal
        order.cgst_amount = subtotal * Decimal('0.025')  # 2.5%
        order.sgst_amount = subtotal * Decimal('0.025')  # 2.5%
        order.discount_amount = Decimal(str(data.get('discount_amount', 0)))
        order.grand_total = subtotal + order.cgst_amount + order.sgst_amount - order.discount_amount
        
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Update order items
        OrderItem.query.filter_by(order_id=order.id).delete()
        
        for item_data in items:
            item = MenuItem.query.get(item_data['menu_item_id'])
            if item:
                order_item = OrderItem()
                order_item.order_id = order.id
                order_item.menu_item_id = item.id
                order_item.quantity = item_data['quantity']
                order_item.price = item.price
                order_item.special_instructions = item_data.get('special_instructions', '')
                order_item.status = 'Pending'
                
                db.session.add(order_item)
                
                # Update stock
                item.stock_quantity = max(0, item.stock_quantity - item_data['quantity'])
                item.update_stock_status()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number,
            'message': 'Order saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/add_item', methods=['POST'])
@login_required
def add_item():
    """Add item to order via AJAX"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        menu_item_id = data.get('menu_item_id')
        quantity = data.get('quantity', 1)
        
        # Get or create order
        if order_id:
            order = Order.query.get(order_id)
            if not order:
                return jsonify({'success': False, 'message': 'Order not found'}), 404
        else:
            order = Order()
            order.order_number = generate_order_number()
            order.status = 'New'
            order.created_by = current_user.id
            db.session.add(order)
            db.session.flush()
        
        # Add item
        menu_item = MenuItem.query.get(menu_item_id)
        if not menu_item or menu_item.is_out_of_stock:
            return jsonify({'success': False, 'message': 'Item not available'}), 400
        
        # Check if item already exists in order
        existing_item = OrderItem.query.filter_by(
            order_id=order.id, 
            menu_item_id=menu_item_id
        ).first()
        
        if existing_item:
            existing_item.quantity += quantity
        else:
            order_item = OrderItem()
            order_item.order_id = order.id
            order_item.menu_item_id = menu_item_id
            order_item.quantity = quantity
            order_item.price = menu_item.price
            order_item.status = 'Pending'
            db.session.add(order_item)
        
        # Update order totals
        update_order_totals(order)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order': order.to_dict(),
            'message': 'Item added successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/update_quantity', methods=['POST'])
@login_required
def update_quantity():
    """Update item quantity via AJAX"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        item_id = data.get('item_id')
        quantity = data.get('quantity')
        
        order_item = OrderItem.query.get(item_id)
        if not order_item or order_item.order_id != order_id:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        order_item.quantity = quantity
        order = Order.query.get(order_id)
        update_order_totals(order)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order': order.to_dict(),
            'message': 'Quantity updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/remove_item', methods=['POST'])
@login_required
def remove_item():
    """Remove item from order via AJAX"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        item_id = data.get('item_id')
        
        order_item = OrderItem.query.get(item_id)
        if not order_item or order_item.order_id != order_id:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        db.session.delete(order_item)
        order = Order.query.get(order_id)
        update_order_totals(order)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order': order.to_dict(),
            'message': 'Item removed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/update_status', methods=['POST'])
@login_required
def update_status():
    """Update order status via AJAX"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        status = data.get('status')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        valid_statuses = ['New', 'In Progress', 'Ready', 'Completed', 'Cancelled']
        if status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        order.status = status
        
        # Update table availability if order is completed
        if status == 'Completed' and order.table_id:
            table = Table.query.get(order.table_id)
            if table:
                table.is_available = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order': order.to_dict(),
            'message': f'Order status updated to {status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    """Process payment with multiple payment methods"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        payment_method = data.get('payment_method')
        amount_paid = data.get('amount_paid')
        discount = data.get('discount', 0)
        payment_details = data.get('payment_details', {})
        
        # Get order
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        if order.items.count() == 0:
            return jsonify({'success': False, 'message': 'Cannot process payment for empty order'}), 400
        
        # Apply discount if provided
        if discount > 0:
            order.apply_discount('fixed', discount)
        
        # Calculate final amount
        final_amount = order.grand_total
        
        # Validate payment amount
        if Decimal(str(amount_paid)) < final_amount:
            return jsonify({'success': False, 'message': 'Insufficient payment amount'}), 400
        
        # Create payment record with encrypted details
        payment = Payment.create_payment(
            order_id=order.id,
            payment_mode=payment_method,
            amount=final_amount,
            processed_by=current_user.id,
            reference_number=payment_details.get('reference_number'),
            payment_details=str(payment_details) if payment_details else None
        )
        
        # Update order status to Completed
        order.update_status('Completed')
        
        # Update table availability if dine-in
        if order.order_type == 'Dine-in' and order.table_id:
            table = Table.query.get(order.table_id)
            if table:
                table.is_available = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'payment_id': payment.id,
            'order_number': order.order_number,
            'amount_paid': float(final_amount),
            'payment_method': payment_method,
            'message': f'Payment processed successfully via {payment_method}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/payment/<int:order_id>')
@login_required
def payment_page(order_id):
    """Payment processing page"""
    order = Order.query.get_or_404(order_id)
    
    return render_template('orders/payment.html', order=order)

# API Endpoints for AJAX calls
@orders_bp.route('/api/orders')
@login_required
def api_orders():
    """API endpoint for orders list"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', '')
        date_filter = request.args.get('date', '')
        search = request.args.get('search', '')
        
        query = Order.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter(db.func.date(Order.created_at) == filter_date)
            except ValueError:
                pass
        
        if search:
            query = query.filter(
                db.or_(
                    Order.order_number.ilike(f'%{search}%'),
                    Order.customer_name.ilike(f'%{search}%'),
                    Order.customer_mobile.ilike(f'%{search}%')
                )
            )
        
        # Include user information
        query = query.join(db.User, Order.created_by == db.User.id)
        
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        orders_data = []
        for order in orders.items:
            order_dict = order.to_dict()
            order_dict['created_by_username'] = order.created_user.username if order.created_user else 'Unknown'
            order_dict['table_number'] = order.table.table_number if order.table else None
            orders_data.append(order_dict)
        
        return jsonify({
            'success': True,
            'orders': orders_data,
            'pagination': {
                'page': orders.page,
                'pages': orders.pages,
                'per_page': orders.per_page,
                'total': orders.total,
                'has_prev': orders.has_prev,
                'has_next': orders.has_next
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/api/orders/<int:order_id>')
@login_required
def api_get_order(order_id):
    """API endpoint to get specific order details"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Get order items with menu item names
        items = []
        for item in order.items:
            item_dict = {
                'id': item.id,
                'menu_item_id': item.menu_item_id,
                'item_name': item.menu_item.name if item.menu_item else 'Unknown',
                'quantity': item.quantity,
                'price': float(item.price),
                'total': float(item.price * item.quantity),
                'special_instructions': item.special_instructions,
                'status': item.status
            }
            items.append(item_dict)
        
        # Get payments
        payments = []
        for payment in order.payments:
            payment_dict = {
                'id': payment.id,
                'payment_mode': payment.payment_mode,
                'amount': float(payment.amount),
                'created_at': payment.created_at.isoformat(),
                'reference_number': payment.reference_number
            }
            payments.append(payment_dict)
        
        order_data = order.to_dict()
        order_data['items'] = items
        order_data['payments'] = payments
        order_data['created_by_username'] = order.created_user.username if order.created_user else 'Unknown'
        order_data['table_number'] = order.table.table_number if order.table else None
        
        return jsonify({
            'success': True,
            'order': order_data,
            'payments': payments
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/merge', methods=['POST'])
@login_required
def merge_orders():
    """Merge two orders"""
    try:
        data = request.get_json()
        source_order_id = data.get('source_order_id')
        target_order_number = data.get('target_order_number')
        
        # Get source order
        source_order = Order.query.get(source_order_id)
        if not source_order:
            return jsonify({'success': False, 'message': 'Source order not found'}), 404
        
        # Find target order by number
        target_order = Order.query.filter_by(order_number=target_order_number).first()
        if not target_order:
            return jsonify({'success': False, 'message': 'Target order not found'}), 404
        
        # Check if both orders can be merged
        if source_order.status not in ['New', 'In Progress'] or target_order.status not in ['New', 'In Progress']:
            return jsonify({'success': False, 'message': 'Only active orders can be merged'}), 400
        
        # Move items from source to target
        for item in source_order.items:
            item.order_id = target_order.id
        
        # Update target totals
        update_order_totals(target_order)
        
        # Delete source order
        db.session.delete(source_order)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'merged_order_id': target_order.id,
            'target_order_number': target_order.order_number,
            'message': 'Orders merged successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/invoice/<int:order_id>')
@login_required
def generate_invoice(order_id):
    """Generate and download invoice PDF"""
    try:
        order = Order.query.get_or_404(order_id)
        settings = Settings.get_all_as_dict()
        
        # Prepare order data for PDF generation
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
        
        # Generate PDF
        pdf_path = generate_invoice_pdf(order_data, settings)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"invoice_{order.order_number}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@orders_bp.route('/print/<int:order_id>')
@login_required
def print_order(order_id):
    """Print optimized bill for thermal printer"""
    try:
        order = Order.query.get_or_404(order_id)
        settings = Settings.get_all_as_dict()
        
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

def generate_order_number():
    """Generate unique order number"""
    prefix = Settings.get('order_prefix', 'ORD')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    import random
    suffix = ''.join(random.choices('0123456789', k=3))
    return f"{prefix}{timestamp}{suffix}"

def update_order_totals(order):
    """Update order totals based on items"""
    items = OrderItem.query.filter_by(order_id=order.id).all()
    
    subtotal = Decimal('0')
    for item in items:
        subtotal += Decimal(str(item.price)) * Decimal(str(item.quantity))
    
    order.subtotal = subtotal
    order.cgst_amount = subtotal * Decimal('0.025')  # 2.5%
    order.sgst_amount = subtotal * Decimal('0.025')  # 2.5%
    order.grand_total = subtotal + order.cgst_amount + order.sgst_amount - order.discount_amount
    order.item_count = len(items)

@orders_bp.route('/print-management')
@login_required
def print_management():
    """Print management interface"""
    return render_template('orders/print_management.html')
