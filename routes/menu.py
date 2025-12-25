from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models import db, MenuItem, Category
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from utils.image_handler import FlaskImageHandler

menu_bp = Blueprint('menu', __name__)

@menu_bp.route('/')
@login_required
def index():
    """Menu management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    
    query = MenuItem.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            MenuItem.name.contains(search) |
            MenuItem.description.contains(search)
        )
    
    if category_filter:
        query = query.filter_by(category_id=category_filter)
    
    menu_items = query.order_by(MenuItem.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = Category.query.filter_by(is_active=True).all()
    
    return render_template('menu/index.html', 
                        menu_items=menu_items, 
                        categories=categories,
                        search=search,
                        category_filter=category_filter)

@menu_bp.route('/categories')
@login_required
def categories():
    """Manage categories"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    return render_template('menu/categories.html', categories=categories)

@menu_bp.route('/add_category', methods=['POST'])
@login_required
def add_category():
    """Add new category"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'success': False, 'message': 'Category name is required'}), 400
        
        if Category.query.filter_by(name=name).first():
            return jsonify({'success': False, 'message': 'Category already exists'}), 400
        
        category = Category.create_category(name, description)
        
        if category:
            return jsonify({
                'success': True,
                'category': category.to_dict(),
                'message': 'Category created successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create category'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@menu_bp.route('/update_category', methods=['POST'])
@login_required
def update_category():
    """Update category"""
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not category_id or not name:
            return jsonify({'success': False, 'message': 'Invalid data'}), 400
        
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'}), 404
        
        if category.update(name, description):
            return jsonify({
                'success': True,
                'category': category.to_dict(),
                'message': 'Category updated successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to update category'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@menu_bp.route('/delete_category', methods=['POST'])
@login_required
def delete_category():
    """Delete category"""
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        
        if not category_id:
            return jsonify({'success': False, 'message': 'Category ID required'}), 400
        
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'}), 404
        
        # Check if category has items
        if category.get_item_count() > 0:
            category.delete()  # Soft delete
            return jsonify({
                'success': True,
                'message': 'Category deleted successfully (items marked as inactive)'
            })
        else:
            category.hard_delete()
            return jsonify({
                'success': True,
                'message': 'Category deleted successfully'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@menu_bp.route('/add_item', methods=['POST'])
@login_required
def add_item():
    """Add new menu item"""
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id', type=int)
        price = request.form.get('price', type=float)
        stock_quantity = request.form.get('stock_quantity', type=int)
        
        if not name or not category_id or price is None:
            flash('Name, category, and price are required', 'error')
            return redirect(url_for('menu.index'))
        
        # Handle image upload using the new image handler
        image_path = None
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'menu_items')
        
        if 'image' in request.files and request.files['image'].filename:
            success, result = FlaskImageHandler.handle_image_upload_in_route(
                request, upload_folder, 'menu_item'
            )
            
            if not success:
                flash(f'Error uploading image: {result}', 'error')
                return redirect(url_for('menu.index'))
            
            image_path = result
        
        menu_item = MenuItem.create_menu_item(
            name=name,
            price=price,
            category_id=category_id,
            description=description,
            stock_quantity=stock_quantity,
            image_path=image_path
        )
        
        if not menu_item:
            flash('Error creating menu item', 'error')
            return redirect(url_for('menu.index'))
        
        flash('Menu item added successfully', 'success')
        return redirect(url_for('menu.index'))
        
    except Exception as e:
        flash(f'Error adding menu item: {str(e)}', 'error')
        return redirect(url_for('menu.index'))

@menu_bp.route('/update_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def update_item(item_id):
    """Update menu item"""
    menu_item = MenuItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            category_id = request.form.get('category_id', type=int)
            price = request.form.get('price', type=float)
            stock_quantity = request.form.get('stock_quantity', type=int)
            
            if not name or not category_id or price is None:
                flash('Name, category, and price are required', 'error')
                categories = Category.query.filter_by(is_active=True).all()
                return render_template('menu/edit_item.html', menu_item=menu_item, categories=categories)
            
            # Handle image upload using the new image handler
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'menu_items')
            
            if 'image' in request.files and request.files['image'].filename:
                success, result = FlaskImageHandler.handle_image_upload_in_route(
                    request, upload_folder, 'menu_item'
                )
                
                if not success:
                    flash(f'Error uploading image: {result}', 'error')
                else:
                    # Delete old image if it exists
                    if menu_item.image_path:
                        old_image_path = FlaskImageHandler.get_full_path(
                            menu_item.image_path, upload_folder
                        )
                        old_thumbnail_path = os.path.join(
                            os.path.dirname(old_image_path),
                            f"thumb_{os.path.basename(old_image_path)}"
                        )
                        FlaskImageHandler.delete_image_files(old_image_path, old_thumbnail_path)
                    
                    # Set new image path
                    menu_item.image_path = result
            
            # Update other fields
            success = menu_item.update(
                name=name,
                description=description,
                category_id=category_id,
                price=price,
                stock_quantity=stock_quantity
            )
            
            if not success:
                flash('Error updating menu item - name may already exist', 'error')
                categories = Category.query.filter_by(is_active=True).all()
                return render_template('menu/edit_item.html', menu_item=menu_item, categories=categories)
            
            flash('Menu item updated successfully', 'success')
            return redirect(url_for('menu.index'))
            
        except Exception as e:
            flash(f'Error updating menu item: {str(e)}', 'error')
    
    categories = Category.query.filter_by(is_active=True).all()
    return render_template('menu/edit_item.html', menu_item=menu_item, categories=categories)

@menu_bp.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    """Delete menu item"""
    try:
        menu_item = MenuItem.query.get_or_404(item_id)
        
        # Delete associated image files
        if menu_item.image_path:
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'menu_items')
            image_path = FlaskImageHandler.get_full_path(menu_item.image_path, upload_folder)
            thumbnail_path = os.path.join(
                os.path.dirname(image_path),
                f"thumb_{os.path.basename(image_path)}"
            )
            FlaskImageHandler.delete_image_files(image_path, thumbnail_path)
        
        # Soft delete
        menu_item.is_active = False
        menu_item.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Menu item deleted successfully', 'success')
        
    except Exception as e:
        flash(f'Error deleting menu item: {str(e)}', 'error')
    
    return redirect(url_for('menu.index'))

@menu_bp.route('/api/items')
@login_required
def api_items():
    """Get menu items via AJAX"""
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '')
    
    query = MenuItem.query.filter_by(is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(
            MenuItem.name.contains(search) |
            MenuItem.description.contains(search)
        )
    
    items = query.order_by(MenuItem.name).all()
    
    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in items]
    })

@menu_bp.route('/api/categories')
@login_required
def api_categories():
    """Get categories via AJAX"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    
    return jsonify({
        'success': True,
        'categories': [cat.to_dict() for cat in categories]
    })

@menu_bp.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    """Handle AJAX image upload"""
    try:
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'menu_items')
        
        success, result = FlaskImageHandler.handle_image_upload_in_route(
            request, upload_folder, 'menu_item'
        )
        
        if not success:
            return jsonify({
                'success': False,
                'message': result
            }), 400
        
        # Generate URL for the uploaded image
        image_url = FlaskImageHandler.get_url_path(result, '/static/uploads/menu_items')
        thumbnail_url = FlaskImageHandler.get_url_path(
            f"thumb_{os.path.basename(result)}",
            '/static/uploads/menu_items'
        )
        
        return jsonify({
            'success': True,
            'image_path': result,
            'image_url': image_url,
            'thumbnail_url': thumbnail_url,
            'message': 'Image uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error uploading image: {str(e)}'
        }), 500
