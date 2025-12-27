from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, MenuItem, Order, OrderItem
from datetime import datetime
from utils.inventory_workflow import inventory_workflow, InventoryAction
import json

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/')
@login_required
def index():
    """Inventory management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    filter_type = request.args.get('filter', 'all')  # all, low_stock, out_of_stock
    
    query = MenuItem.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            MenuItem.name.contains(search) |
            MenuItem.description.contains(search)
        )
    
    if filter_type == 'low_stock':
        query = query.filter(
            MenuItem.stock_quantity <= MenuItem.min_stock_level,
            MenuItem.stock_quantity > 0
        )
    elif filter_type == 'out_of_stock':
        query = query.filter_by(stock_quantity=0)
    
    items = query.order_by(MenuItem.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Convert items to dict before passing to template
    items_dict = [item.to_dict() for item in items.items]
    return render_template('inventory/index.html',
                        items={'items': items_dict,
                                'pages': items.pages,
                                'has_next': items.has_next,
                                'has_prev': items.has_prev},
                        search=search,
                        filter_type=filter_type)

@inventory_bp.route('/update_stock', methods=['POST'])
@login_required
def update_stock():
    """Update item stock via AJAX"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        new_quantity = int(data.get('quantity', 0)) if data.get('quantity') else 0
        
        if item_id is None or new_quantity is None:
            return jsonify({'success': False, 'message': 'Item ID and quantity required'}), 400
        
        menu_item = MenuItem.query.get(item_id)
        if not menu_item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        old_quantity = menu_item.stock_quantity
        menu_item.stock_quantity = max(0, new_quantity)
        menu_item.update_stock_status()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item': menu_item.to_dict(),
            'message': f'Stock updated from {old_quantity} to {new_quantity}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/add_stock', methods=['POST'])
@login_required
def add_stock():
    """Add stock to multiple items"""
    try:
        data = request.get_json()
        items = data.get('items', [])
        
        updated_items = []
        for item_data in items:
            item_id = item_data.get('item_id')
            quantity = int(item_data.get('quantity', 0)) if item_data.get('quantity') else 0
            
            if item_id and quantity:
                menu_item = MenuItem.query.get(item_id)
                if menu_item:
                    old_quantity = menu_item.stock_quantity
                    menu_item.stock_quantity += quantity
                    menu_item.update_stock_status()
                    updated_items.append({
                        'item': menu_item.to_dict(),
                        'old_quantity': old_quantity,
                        'new_quantity': menu_item.stock_quantity,
                        'added': quantity
                    })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'items': updated_items,
            'message': f'Stock updated for {len(updated_items)} items'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/data')
@login_required
def get_data():
    """Get all inventory items via AJAX"""
    try:
        items = MenuItem.query.filter_by(is_active=True).order_by(MenuItem.name).all()
        return jsonify({
            'success': True,
            'items': [item.to_dict() for item in items]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/low_stock')
@login_required
def low_stock():
    """Get low stock items via AJAX"""
    low_stock_items = MenuItem.query.filter(
        MenuItem.stock_quantity <= MenuItem.min_stock_level,
        MenuItem.stock_quantity > 0,
        MenuItem.is_active == True
    ).order_by(MenuItem.stock_quantity).all()
    
    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in low_stock_items],
        'count': len(low_stock_items)
    })

# Inventory Workflow Management Endpoints
@inventory_bp.route('/workflow/check_stock', methods=['POST'])
@login_required
def workflow_check_stock():
    """Check stock levels and update workflow states"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        
        stock_status = inventory_workflow.check_stock_levels(item_id)
        
        return jsonify({
            'success': True,
            'stock_status': stock_status
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/workflow/action', methods=['POST'])
@login_required
def workflow_inventory_action():
    """Execute inventory workflow action"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        action = data.get('action')
        action_data = data.get('data', {})
        
        # Convert string action to enum
        try:
            inventory_action = InventoryAction(action)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid inventory action'}), 400
        
        # Execute workflow action
        success, message, result = inventory_workflow.process_inventory_action(
            current_user, item_id, inventory_action, action_data
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'result': result
            })
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/workflow/request_reorder', methods=['POST'])
@login_required
def request_reorder():
    """Request reorder for inventory item"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        quantity = data.get('quantity')
        urgency = data.get('urgency', 'normal')
        
        result = inventory_workflow.request_reorder(item_id, quantity, urgency)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/workflow/process_reorder', methods=['POST'])
@login_required
def process_reorder():
    """Process reorder approval/rejection"""
    try:
        data = request.get_json()
        reorder_id = data.get('reorder_id')
        approved = data.get('approved', False)
        actual_quantity = data.get('actual_quantity')
        supplier_data = data.get('supplier_data', {})
        
        result = inventory_workflow.process_reorder(
            reorder_id, approved, current_user, actual_quantity, supplier_data
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/workflow/statistics')
@login_required
def inventory_workflow_statistics():
    """Get inventory workflow statistics"""
    try:
        date_filter = request.args.get('date_range')
        date_range = None
        
        if date_filter:
            try:
                start_date, end_date = date_filter.split(',')
                date_range = (
                    datetime.strptime(start_date, '%Y-%m-%d'),
                    datetime.strptime(end_date, '%Y-%m-%d')
                )
            except ValueError:
                pass
        
        stats = inventory_workflow.get_inventory_workflow_statistics(date_range)
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/workflow/alerts')
@login_required
def inventory_alerts():
    """Get active inventory alerts"""
    try:
        stock_status = inventory_workflow.check_stock_levels()
        
        return jsonify({
            'success': True,
            'alerts': stock_status.get('alerts', []),
            'summary': {
                'low_stock_count': len(stock_status.get('low_stock', [])),
                'critical_stock_count': len(stock_status.get('critical', [])),
                'out_of_stock_count': len(stock_status.get('out_of_stock', []))
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/bulk_update_stock', methods=['POST'])
@login_required
def bulk_update_stock():
    """Bulk update stock for multiple items"""
    try:
        data = request.get_json()
        updates = data.get('updates', [])
        
        results = []
        for update in updates:
            item_id = update.get('item_id')
            new_quantity = update.get('quantity', 0)
            reason = update.get('reason', 'Bulk update')
            
            # Use workflow engine for consistent handling
            success, message, result = inventory_workflow.process_inventory_action(
                current_user, item_id, InventoryAction.UPDATE_STOCK,
                {'quantity': new_quantity, 'reason': reason}
            )
            
            results.append({
                'item_id': item_id,
                'success': success,
                'message': message,
                'result': result
            })
        
        return jsonify({
            'success': True,
            'results': results,
            'updated_count': len([r for r in results if r['success']])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@inventory_bp.route('/workflow')
@login_required
def workflow_dashboard():
    """Inventory workflow management dashboard"""
    return render_template('inventory/workflow_dashboard.html')
