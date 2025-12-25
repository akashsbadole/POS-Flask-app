from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from models import db, MenuItem
from datetime import datetime

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
