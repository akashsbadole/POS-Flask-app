from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Supplier, SupplierCategory, SupplierContact, SupplierDocument, SupplierRating
from models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderApproval, PurchaseOrderReceipt, PurchaseOrderTemplate, SupplierPriceHistory
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, func, desc
import json

supplier_bp = Blueprint('supplier_management', __name__, url_prefix='/suppliers')

# ==================== SUPPLIER CATEGORIES ====================

@supplier_bp.route('/categories', methods=['GET'])
@login_required
def list_categories():
    """List all supplier categories"""
    try:
        categories = SupplierCategory.query.filter_by(is_active=True).order_by(SupplierCategory.name).all()
        return jsonify({
            'success': True,
            'categories': [category.to_dict() for category in categories]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    """Create new supplier category"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        color_code = data.get('color_code')
        
        if not name:
            return jsonify({'success': False, 'message': 'Category name is required'}), 400
        
        # Check if category already exists
        if SupplierCategory.query.filter_by(name=name).first():
            return jsonify({'success': False, 'message': 'Category already exists'}), 400
        
        category = SupplierCategory(name, description, color_code)
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'category': category.to_dict(),
            'message': 'Category created successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/categories/<int:category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    """Update supplier category"""
    try:
        category = SupplierCategory.query.get_or_404(category_id)
        data = request.get_json()
        
        if 'name' in data:
            # Check for name uniqueness
            existing = SupplierCategory.query.filter(
                and_(SupplierCategory.name == data['name'], SupplierCategory.id != category_id)
            ).first()
            if existing:
                return jsonify({'success': False, 'message': 'Category name already exists'}), 400
            category.name = data['name']
        
        if 'description' in data:
            category.description = data['description']
        if 'color_code' in data:
            category.color_code = data['color_code']
        if 'is_active' in data:
            category.is_active = data['is_active']
        
        category.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'category': category.to_dict(),
            'message': 'Category updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """Delete supplier category"""
    try:
        category = SupplierCategory.query.get_or_404(category_id)
        
        # Check if category has suppliers
        if category.suppliers:
            return jsonify({'success': False, 'message': 'Cannot delete category with existing suppliers'}), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== SUPPLIER CRUD OPERATIONS ====================

@supplier_bp.route('/', methods=['GET'])
@login_required
def list_suppliers():
    """List suppliers with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        category_id = request.args.get('category_id', type=int)
        status = request.args.get('status', '')
        is_preferred = request.args.get('is_preferred')
        
        query = Supplier.query
        
        # Apply filters
        if search:
            query = query.filter(
                or_(
                    Supplier.name.contains(search),
                    Supplier.business_name.contains(search),
                    Supplier.email.contains(search),
                    Supplier.phone.contains(search),
                    Supplier.supplier_code.contains(search)
                )
            )
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if is_preferred is not None:
            query = query.filter_by(is_preferred=is_preferred.lower() == 'true')
        
        # Order by name
        query = query.order_by(Supplier.name)
        
        # Paginate
        suppliers = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'suppliers': [supplier.to_dict() for supplier in suppliers.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'pages': suppliers.pages,
                'total': suppliers.total,
                'has_next': suppliers.has_next,
                'has_prev': suppliers.has_prev
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/', methods=['POST'])
@login_required
def create_supplier():
    """Create new supplier"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'category_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Check if supplier code already exists
        if data.get('supplier_code'):
            existing = Supplier.query.filter_by(supplier_code=data['supplier_code']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Supplier code already exists'}), 400
        
        # Create supplier
        supplier = Supplier(
            name=data['name'],
            category_id=data['category_id'],
            supplier_code=data.get('supplier_code')
        )
        
        # Set optional fields
        optional_fields = [
            'business_name', 'tax_id', 'registration_number', 'website',
            'email', 'phone', 'mobile', 'fax', 'address_line_1', 'address_line_2',
            'city', 'state', 'postal_code', 'country', 'payment_terms',
            'credit_limit', 'currency', 'lead_time_days', 'minimum_order_value',
            'delivery_charge', 'notes', 'special_instructions'
        ]
        
        for field in optional_fields:
            if field in data and data[field] is not None:
                setattr(supplier, field, data[field])
        
        db.session.add(supplier)
        db.session.flush()  # Get supplier ID
        
        # Add contacts if provided
        if 'contacts' in data and data['contacts']:
            for contact_data in data['contacts']:
                contact = SupplierContact(
                    supplier_id=supplier.id,
                    name=contact_data['name'],
                    position=contact_data.get('position'),
                    email=contact_data.get('email'),
                    phone=contact_data.get('phone')
                )
                db.session.add(contact)
        
        # Set preferences if provided
        if 'preferences' in data:
            supplier.set_preferences(data['preferences'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'supplier': supplier.to_dict(include_relationships=True),
            'message': 'Supplier created successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/<int:supplier_id>', methods=['GET'])
@login_required
def get_supplier(supplier_id):
    """Get supplier by ID"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        return jsonify({
            'success': True,
            'supplier': supplier.to_dict(include_relationships=True)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/<int:supplier_id>', methods=['PUT'])
@login_required
def update_supplier(supplier_id):
    """Update supplier"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        data = request.get_json()
        
        # Update basic fields
        updatable_fields = [
            'name', 'business_name', 'category_id', 'tax_id', 'registration_number',
            'website', 'email', 'phone', 'mobile', 'fax', 'address_line_1',
            'address_line_2', 'city', 'state', 'postal_code', 'country',
            'payment_terms', 'credit_limit', 'currency', 'lead_time_days',
            'minimum_order_value', 'delivery_charge', 'notes', 'special_instructions',
            'is_preferred', 'status'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(supplier, field, data[field])
        
        # Update contract dates
        if 'contract_start_date' in data:
            supplier.contract_start_date = data['contract_start_date']
        if 'contract_end_date' in data:
            supplier.contract_end_date = data['contract_end_date']
        if 'contract_value' in data:
            supplier.contract_value = data['contract_value']
        
        # Update preferences
        if 'preferences' in data:
            supplier.set_preferences(data['preferences'])
        
        supplier.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'supplier': supplier.to_dict(include_relationships=True),
            'message': 'Supplier updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/<int:supplier_id>', methods=['DELETE'])
@login_required
def delete_supplier(supplier_id):
    """Delete supplier (soft delete by setting status)"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        
        # Check if supplier has purchase orders
        if supplier.purchase_orders:
            return jsonify({
                'success': False, 
                'message': 'Cannot delete supplier with existing purchase orders. Set status to inactive instead.'
            }), 400
        
        # Soft delete by setting status
        supplier.status = Supplier.STATUS_INACTIVE
        supplier.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Supplier deactivated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/<int:supplier_id>/approve', methods=['POST'])
@login_required
def approve_supplier(supplier_id):
    """Approve supplier"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        supplier.approve_supplier(current_user.id)
        
        return jsonify({
            'success': True,
            'supplier': supplier.to_dict(),
            'message': 'Supplier approved successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/<int:supplier_id>/suspend', methods=['POST'])
@login_required
def suspend_supplier(supplier_id):
    """Suspend supplier"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        supplier.suspend_supplier(reason)
        
        return jsonify({
            'success': True,
            'supplier': supplier.to_dict(),
            'message': 'Supplier suspended successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== SUPPLIER CONTACTS ====================

@supplier_bp.route('/<int:supplier_id>/contacts', methods=['POST'])
@login_required
def add_supplier_contact(supplier_id):
    """Add contact to supplier"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        data = request.get_json()
        
        contact = SupplierContact(
            supplier_id=supplier_id,
            name=data['name'],
            position=data.get('position'),
            department=data.get('department'),
            email=data.get('email'),
            phone=data.get('phone'),
            mobile=data.get('mobile'),
            fax=data.get('fax'),
            is_primary=data.get('is_primary', False),
            is_billing_contact=data.get('is_billing_contact', False),
            is_technical_contact=data.get('is_technical_contact', False),
            is_sales_contact=data.get('is_sales_contact', False),
            availability_hours=data.get('availability_hours'),
            preferred_contact_method=data.get('preferred_contact_method'),
            notes=data.get('notes')
        )
        
        db.session.add(contact)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'contact': contact.to_dict(),
            'message': 'Contact added successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/contacts/<int:contact_id>', methods=['PUT'])
@login_required
def update_supplier_contact(contact_id):
    """Update supplier contact"""
    try:
        contact = SupplierContact.query.get_or_404(contact_id)
        data = request.get_json()
        
        updatable_fields = [
            'name', 'position', 'department', 'email', 'phone', 'mobile', 'fax',
            'is_primary', 'is_billing_contact', 'is_technical_contact', 'is_sales_contact',
            'availability_hours', 'preferred_contact_method', 'notes'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(contact, field, data[field])
        
        contact.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'contact': contact.to_dict(),
            'message': 'Contact updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/contacts/<int:contact_id>', methods=['DELETE'])
@login_required
def delete_supplier_contact(contact_id):
    """Delete supplier contact"""
    try:
        contact = SupplierContact.query.get_or_404(contact_id)
        db.session.delete(contact)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Contact deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== SUPPLIER RATINGS ====================

@supplier_bp.route('/<int:supplier_id>/ratings', methods=['POST'])
@login_required
def add_supplier_rating(supplier_id):
    """Add rating for supplier"""
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        data = request.get_json()
        
        rating = SupplierRating(
            supplier_id=supplier_id,
            quality_rating=data['quality_rating'],
            delivery_rating=data['delivery_rating'],
            price_rating=data['price_rating'],
            service_rating=data.get('service_rating', 0),
            rated_by=current_user.id
        )
        
        # Set comments
        if 'quality_comments' in data:
            rating.quality_comments = data['quality_comments']
        if 'delivery_comments' in data:
            rating.delivery_comments = data['delivery_comments']
        if 'price_comments' in data:
            rating.price_comments = data['price_comments']
        if 'service_comments' in data:
            rating.service_comments = data['service_comments']
        if 'general_comments' in data:
            rating.general_comments = data['general_comments']
        if 'improvement_suggestions' in data:
            rating.improvement_suggestions = data['improvement_suggestions']
        if 'would_recommend' in data:
            rating.would_recommend = data['would_recommend']
        
        # Link to purchase order if provided
        if 'purchase_order_id' in data:
            rating.purchase_order_id = data['purchase_order_id']
        
        db.session.add(rating)
        db.session.flush()  # Get rating ID
        
        # Update supplier's average ratings
        supplier.update_rating(
            quality=rating.quality_rating,
            delivery=rating.delivery_rating,
            price=rating.price_rating
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'rating': rating.to_dict(),
            'message': 'Rating added successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/<int:supplier_id>/ratings', methods=['GET'])
@login_required
def get_supplier_ratings(supplier_id):
    """Get supplier ratings"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        ratings = SupplierRating.query.filter_by(supplier_id=supplier_id)\
            .order_by(SupplierRating.rated_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'ratings': [rating.to_dict() for rating in ratings.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'pages': ratings.pages,
                'total': ratings.total
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== PURCHASE ORDERS ====================

@supplier_bp.route('/purchase-orders', methods=['GET'])
@login_required
def list_purchase_orders():
    """List purchase orders with filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        supplier_id = request.args.get('supplier_id', type=int)
        status = request.args.get('status', '')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        query = PurchaseOrder.query
        
        # Apply filters
        if search:
            query = query.filter(
                or_(
                    PurchaseOrder.po_number.contains(search),
                    PurchaseOrder.reference_number.contains(search),
                    Supplier.name.contains(search)
                )
            ).join(Supplier)
        
        if supplier_id:
            query = query.filter_by(supplier_id=supplier_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if date_from:
            query = query.filter(PurchaseOrder.order_date >= date_from)
        
        if date_to:
            query = query.filter(PurchaseOrder.order_date <= date_to)
        
        # Order by creation date
        query = query.order_by(PurchaseOrder.created_at.desc())
        
        # Paginate
        purchase_orders = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'purchase_orders': [po.to_dict(include_items=True) for po in purchase_orders.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'pages': purchase_orders.pages,
                'total': purchase_orders.total,
                'has_next': purchase_orders.has_next,
                'has_prev': purchase_orders.has_prev
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@supplier_bp.route('/purchase-orders', methods=['POST'])
@login_required
def create_purchase_order():
    """Create new purchase order"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['supplier_id', 'items']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Create purchase order
        po = PurchaseOrder(
            supplier_id=data['supplier_id'],
            created_by=current_user.id,
            po_number=data.get('po_number')
        )
        
        # Set optional fields
        optional_fields = [
            'expected_delivery_date', 'delivery_address', 'priority',
            'payment_terms', 'payment_due_date', 'reference_number',
            'special_instructions', 'internal_notes', 'requires_approval',
            'approval_level'
        ]
        
        for field in optional_fields:
            if field in data and data[field] is not None:
                setattr(po, field, data[field])
        
        db.session.add(po)
        db.session.flush()  # Get PO ID
        
        # Add items
        for item_data in data['items']:
            item = PurchaseOrderItem(
                purchase_order_id=po.id,
                item_name=item_data['item_name'],
                quantity_ordered=item_data['quantity'],
                unit_price=item_data['unit_price'],
                inventory_item_id=item_data.get('inventory_item_id'),
                description=item_data.get('description'),
                item_code=item_data.get('item_code'),
                unit_of_measure=item_data.get('unit_of_measure', 'pcs'),
                tax_rate=item_data.get('tax_rate', 0),
                discount_rate=item_data.get('discount_rate', 0),
                expected_delivery_date=item_data.get('expected_delivery_date')
            )
            db.session.add(item)
        
        # Calculate totals
        po.calculate_totals()
        
        # Set up approval workflow if required
        if po.requires_approval and data.get('setup_approval', True):
            # Create approval records based on amount and approval level
            setup_approval_workflow(po)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'purchase_order': po.to_dict(include_items=True),
            'message': 'Purchase order created successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

def setup_approval_workflow(po):
    """Set up approval workflow for purchase order"""
    try:
        # This is a simplified version - in production, you'd have more sophisticated logic
        # based on amounts, user roles, department policies, etc.
        
        amount = float(po.total_amount)
        
        # Level 1 approval (Manager) - for all orders
        approval1 = PurchaseOrderApproval(
            purchase_order_id=po.id,
            approval_level=1,
            approver_id=current_user.id,  # This should be the manager's ID
            amount_limit=10000  # Manager can approve up to ₹10,000
        )
        db.session.add(approval1)
        
        # Level 2 approval (Senior Manager) - for orders over ₹5,000
        if amount > 5000:
            approval2 = PurchaseOrderApproval(
                purchase_order_id=po.id,
                approval_level=2,
                approver_id=current_user.id,  # This should be the senior manager's ID
                amount_limit=50000  # Senior manager can approve up to ₹50,000
            )
            db.session.add(approval2)
        
        # Level 3 approval (Director) - for orders over ₹25,000
        if amount > 25000:
            approval3 = PurchaseOrderApproval(
                purchase_order_id=po.id,
                approval_level=3,
                approver_id=current_user.id,  # This should be the director's ID
                amount_limit=100000  # Director can approve up to ₹1,00,000
            )
            db.session.add(approval3)
    
    except Exception as e:
        print(f"Error setting up approval workflow: {e}")


@supplier_bp.route('/purchase-orders/<int:po_id>', methods=['GET'])
@login_required
def get_purchase_order(po_id):
    """Get purchase order by ID"""
    try:
        po = PurchaseOrder.query.get_or_404(po_id)
        return jsonify({
            'success': True,
            'purchase_order': po.to_dict(include_items=True)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@supplier_bp.route('/purchase-orders/<int:po_id>', methods=['PUT'])
@login_required
def update_purchase_order(po_id):
    """Update purchase order"""
    try:
        po = PurchaseOrder.query.get_or_404(po_id)
        
        # Only allow updates for draft and pending orders
        if po.status not in [PurchaseOrder.STATUS_DRAFT, PurchaseOrder.STATUS_PENDING]:
            return jsonify({'success': False, 'message': 'Cannot update order in current status'}), 400
        
        data = request.get_json()
        
        # Update fields
        updatable_fields = [
            'expected_delivery_date', 'delivery_address', 'priority',
            'payment_terms', 'payment_due_date', 'reference_number',
            'special_instructions', 'internal_notes'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(po, field, data[field])
        
        # Update items if provided
        if 'items' in data and data['items']:
            # Remove existing items
            for item in po.items:
                db.session.delete(item)
            
            # Add new items
            for item_data in data['items']:
                item = PurchaseOrderItem(
                    purchase_order_id=po.id,
                    item_name=item_data['item_name'],
                    quantity_ordered=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    inventory_item_id=item_data.get('inventory_item_id'),
                    description=item_data.get('description'),
                    item_code=item_data.get('item_code'),
                    unit_of_measure=item_data.get('unit_of_measure', 'pcs'),
                    tax_rate=item_data.get('tax_rate', 0),
                    discount_rate=item_data.get('discount_rate', 0)
                )
                db.session.add(item)
            
            # Recalculate totals
            po.calculate_totals()
        
        po.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'purchase_order': po.to_dict(include_items=True),
            'message': 'Purchase order updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@supplier_bp.route('/purchase-orders/<int:po_id>/status', methods=['PUT'])
@login_required
def update_po_status(po_id):
    """Update purchase order status"""
    try:
        po = PurchaseOrder.query.get_or_404(po_id)
        data = request.get_json()
        
        new_status = data.get('status')
        notes = data.get('notes')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status is required'}), 400
        
        success, message = po.update_status(new_status, current_user.id, notes)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 400
        
        return jsonify({
            'success': True,
            'purchase_order': po.to_dict(include_items=True),
            'message': message
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@supplier_bp.route('/purchase-orders/<int:po_id>/approve', methods=['POST'])
@login_required
def approve_purchase_order(po_id):
    """Approve purchase order"""
    try:
        po = PurchaseOrder.query.get_or_404(po_id)
        data = request.get_json()
        notes = data.get('notes', '')
        
        success, message = po.approve(current_user.id, notes)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 400
        
        return jsonify({
            'success': True,
            'purchase_order': po.to_dict(include_items=True),
            'message': message
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@supplier_bp.route('/purchase-orders/<int:po_id>/receive', methods=['POST'])
@login_required
def receive_purchase_order(po_id):
    """Mark items as received"""
    try:
        po = PurchaseOrder.query.get_or_404(po_id)
        data = request.get_json()
        
        receipts = data.get('receipts', [])
        delivery_date = data.get('delivery_date')
        notes = data.get('notes')
        
        if not receipts:
            return jsonify({'success': False, 'message': 'At least one receipt is required'}), 400
        
        receipt_records = []
        
        for receipt_data in receipts:
            item_id = receipt_data.get('item_id')
            quantity = receipt_data.get('quantity')
            quality_passed = receipt_data.get('quality_passed', True)
            condition_notes = receipt_data.get('condition_notes')
            batch_number = receipt_data.get('batch_number')
            expiry_date = receipt_data.get('expiry_date')
            
            # Get the purchase order item
            po_item = PurchaseOrderItem.query.filter_by(
                id=item_id, 
                purchase_order_id=po_id
            ).first()
            
            if not po_item:
                return jsonify({'success': False, 'message': f'Item {item_id} not found'}), 400
            
            # Create receipt record
            receipt = PurchaseOrderReceipt(
                purchase_order_id=po_id,
                purchase_order_item_id=item_id,
                received_quantity=quantity,
                received_by=current_user.id
            )
            
            # Set additional fields
            if batch_number:
                receipt.batch_number = batch_number
            if expiry_date:
                receipt.expiry_date = expiry_date
            
            db.session.add(receipt)
            db.session.flush()
            
            # Update item received quantity
            success, message = po_item.receive_quantity(
                quantity, quality_passed, condition_notes, delivery_date
            )
            
            if not success:
                return jsonify({'success': False, 'message': message}), 400
            
            # Update receipt quality status
            if quality_passed:
                receipt.mark_quality_passed(condition_notes)
            else:
                receipt.mark_quality_failed(condition_notes)
            
            receipt_records.append(receipt.to_dict())
        
        # Update purchase order status
        if delivery_date:
            po.actual_delivery_date = delivery_date
        
        if notes:
            po.delivery_performance_notes = (po.delivery_performance_notes or "") + f"\n{date.today()}: {notes}"
        
        # Determine new status
        if po.is_fully_received:
            new_status = PurchaseOrder.STATUS_COMPLETED
        elif po.is_partially_received:
            new_status = PurchaseOrder.STATUS_PARTIALLY_RECEIVED
        else:
            new_status = PurchaseOrder.STATUS_RECEIVED
        
        po.update_status(new_status, notes=notes)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'purchase_order': po.to_dict(include_items=True),
            'receipts': receipt_records,
            'message': f'Received {len(receipt_records)} items successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== SUPPLIER ANALYTICS ====================

@supplier_bp.route('/analytics/overview')
@login_required
def supplier_analytics_overview():
    """Get supplier analytics overview"""
    try:
        # Get date range from request
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        if not date_from:
            date_from = (date.today() - timedelta(days=30)).isoformat()
        if not date_to:
            date_to = date.today().isoformat()
        
        # Convert to date objects
        from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        # Supplier statistics
        total_suppliers = Supplier.query.filter_by(status=Supplier.STATUS_ACTIVE).count()
        pending_suppliers = Supplier.query.filter_by(status=Supplier.STATUS_PENDING).count()
        preferred_suppliers = Supplier.query.filter_by(is_preferred=True).count()
        
        # Purchase order statistics
        total_pos = PurchaseOrder.query.filter(
            PurchaseOrder.order_date >= from_date,
            PurchaseOrder.order_date <= to_date
        ).count()
        
        pending_pos = PurchaseOrder.query.filter(
            PurchaseOrder.status.in_([PurchaseOrder.STATUS_PENDING, PurchaseOrder.STATUS_APPROVED]),
            PurchaseOrder.order_date >= from_date,
            PurchaseOrder.order_date <= to_date
        ).count()
        
        completed_pos = PurchaseOrder.query.filter(
            PurchaseOrder.status == PurchaseOrder.STATUS_COMPLETED,
            PurchaseOrder.order_date >= from_date,
            PurchaseOrder.order_date <= to_date
        ).count()
        
        # Financial statistics
        total_spend = db.session.query(func.sum(PurchaseOrder.total_amount)).filter(
            PurchaseOrder.order_date >= from_date,
            PurchaseOrder.order_date <= to_date,
            PurchaseOrder.status.in_([PurchaseOrder.STATUS_COMPLETED, PurchaseOrder.STATUS_RECEIVED])
        ).scalar() or 0
        
        # Average order value
        avg_order_value = db.session.query(func.avg(PurchaseOrder.total_amount)).filter(
            PurchaseOrder.order_date >= from_date,
            PurchaseOrder.order_date <= to_date
        ).scalar() or 0
        
        # Top suppliers by spend
        top_suppliers = db.session.query(
            Supplier.name,
            func.sum(PurchaseOrder.total_amount).label('total_spend'),
            func.count(PurchaseOrder.id).label('order_count')
        ).join(PurchaseOrder).filter(
            PurchaseOrder.order_date >= from_date,
            PurchaseOrder.order_date <= to_date,
            PurchaseOrder.status.in_([PurchaseOrder.STATUS_COMPLETED, PurchaseOrder.STATUS_RECEIVED])
        ).group_by(Supplier.id, Supplier.name).order_by(desc('total_spend')).limit(5).all()
        
        # Supplier performance metrics
        supplier_performance = db.session.query(
            Supplier.name,
            func.avg(Supplier.overall_rating).label('avg_rating'),
            func.count(PurchaseOrder.id).label('total_orders'),
            func.avg(PurchaseOrder.on_time_delivery_rate).label('avg_delivery_rate')
        ).outerjoin(PurchaseOrder).group_by(Supplier.id, Supplier.name).all()
        
        return jsonify({
            'success': True,
            'data': {
                'date_range': {'from': date_from, 'to': date_to},
                'supplier_stats': {
                    'total_suppliers': total_suppliers,
                    'pending_suppliers': pending_suppliers,
                    'preferred_suppliers': preferred_suppliers
                },
                'purchase_order_stats': {
                    'total_orders': total_pos,
                    'pending_orders': pending_pos,
                    'completed_orders': completed_pos,
                    'completion_rate': (completed_pos / total_pos * 100) if total_pos > 0 else 0
                },
                'financial_stats': {
                    'total_spend': float(total_spend),
                    'average_order_value': float(avg_order_value),
                    'formatted_total_spend': f"₹{float(total_spend):,.2f}",
                    'formatted_avg_order': f"₹{float(avg_order_value):,.2f}"
                },
                'top_suppliers': [{
                    'name': supplier[0],
                    'total_spend': float(supplier[1]) if supplier[1] else 0,
                    'order_count': supplier[2],
                    'formatted_spend': f"₹{float(supplier[1] or 0):,.2f}"
                } for supplier in top_suppliers],
                'supplier_performance': [{
                    'name': perf[0],
                    'avg_rating': float(perf[1]) if perf[1] else 0,
                    'total_orders': perf[2] or 0,
                    'avg_delivery_rate': float(perf[3]) if perf[3] else 0
                } for perf in supplier_performance]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@supplier_bp.route('/analytics/performance')
@login_required
def supplier_performance_analytics():
    """Get detailed supplier performance analytics"""
    try:
        # Get top performing suppliers
        top_suppliers = Supplier.query.filter(
            Supplier.status == Supplier.STATUS_ACTIVE,
            Supplier.overall_rating > 0
        ).order_by(Supplier.overall_rating.desc()).limit(10).all()
        
        # Get suppliers with performance issues
        low_performance_suppliers = Supplier.query.filter(
            Supplier.status == Supplier.STATUS_ACTIVE,
            Supplier.overall_rating > 0,
            Supplier.overall_rating < 3.0
        ).order_by(Supplier.overall_rating).limit(10).all()
        
        # Get delivery performance stats
        delivery_stats = db.session.query(
            func.avg(PurchaseOrder.on_time_delivery_rate).label('avg_on_time_rate'),
            func.avg(PurchaseOrder.average_delivery_time).label('avg_delivery_time')
        ).filter(
            PurchaseOrder.on_time_delivery_rate.isnot(None)
        ).first()
        
        # Get quality metrics
        quality_stats = db.session.query(
            func.avg(PurchaseOrder.quality_issue_rate).label('avg_quality_issues')
        ).filter(
            PurchaseOrder.has_quality_issues.isnot(None)
        ).first()
        
        return jsonify({
            'success': True,
            'data': {
                'top_suppliers': [supplier.to_dict() for supplier in top_suppliers],
                'low_performance_suppliers': [supplier.to_dict() for supplier in low_performance_suppliers],
                'delivery_performance': {
                    'average_on_time_rate': float(delivery_stats[0]) if delivery_stats[0] else 0,
                    'average_delivery_time_hours': float(delivery_stats[1]) if delivery_stats[1] else 0
                },
                'quality_metrics': {
                    'average_quality_issue_rate': float(quality_stats[0]) if quality_stats[0] else 0
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== DASHBOARD ROUTES ====================

@supplier_bp.route('/dashboard')
@login_required
def supplier_dashboard():
    """Supplier management dashboard"""
    return render_template('suppliers/dashboard.html')


@supplier_bp.route('/dashboard/data')
@login_required
def dashboard_data():
    """Get dashboard data"""
    try:
        # Get recent activity
        recent_suppliers = Supplier.query.order_by(Supplier.created_at.desc()).limit(5).all()
        recent_orders = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).limit(5).all()
        
        # Get pending approvals
        pending_approvals = PurchaseOrder.query.filter_by(
            status=PurchaseOrder.STATUS_PENDING
        ).order_by(PurchaseOrder.created_at.desc()).limit(5).all()
        
        # Get low-rated suppliers
        low_rated_suppliers = Supplier.query.filter(
            Supplier.overall_rating < 3.0,
            Supplier.overall_rating > 0
        ).order_by(Supplier.overall_rating).limit(5).all()
        
        return jsonify({
            'success': True,
            'data': {
                'recent_suppliers': [supplier.to_dict() for supplier in recent_suppliers],
                'recent_orders': [po.to_dict() for po in recent_orders],
                'pending_approvals': [po.to_dict() for po in pending_approvals],
                'low_rated_suppliers': [supplier.to_dict() for supplier in low_rated_suppliers]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@supplier_bp.route('/')
@login_required
def supplier_management_index():
    """Supplier management main page"""
    return render_template('suppliers/index.html')


@supplier_bp.route('/<int:supplier_id>')
@login_required
def supplier_detail(supplier_id):
    """Supplier detail page"""
    return render_template('suppliers/detail.html', supplier_id=supplier_id)


@supplier_bp.route('/purchase-orders/new')
@login_required
def create_po_page():
    """Create purchase order page"""
    return render_template('purchase_orders/create.html')


@supplier_bp.route('/purchase-orders/<int:po_id>')
@login_required
def po_detail_page(po_id):
    """Purchase order detail page"""
    return render_template('purchase_orders/detail.html', po_id=po_id)


@supplier_bp.route('/purchase-orders/<int:po_id>/receive')
@login_required
def receive_po_page(po_id):
    """Receive purchase order page"""
    return render_template('purchase_orders/receive.html', po_id=po_id)