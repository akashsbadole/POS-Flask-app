from datetime import datetime, date
from decimal import Decimal
from . import db
import uuid
import json

class SupplierCategory(db.Model):
    """Supplier category model for organizing suppliers by product type"""
    __tablename__ = 'supplier_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    color_code = db.Column(db.String(7), nullable=True)  # Hex color code for UI
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    suppliers = db.relationship('Supplier', backref='category', lazy=True)
    
    def __init__(self, name, description=None, color_code=None):
        self.name = name
        self.description = description
        self.color_code = color_code
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color_code': self.color_code,
            'is_active': self.is_active,
            'supplier_count': len(self.suppliers),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<SupplierCategory {self.name}>'


class Supplier(db.Model):
    """Main supplier model with business information and preferences"""
    __tablename__ = 'suppliers'
    
    # Supplier status
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_SUSPENDED = 'suspended'
    STATUS_BLACKLISTED = 'blacklisted'
    
    # Payment terms
    PAYMENT_TERMS_NET_15 = 'net_15'
    PAYMENT_TERMS_NET_30 = 'net_30'
    PAYMENT_TERMS_NET_45 = 'net_45'
    PAYMENT_TERMS_NET_60 = 'net_60'
    PAYMENT_TERMS_COD = 'cod'
    PAYMENT_TERMS_PREPAID = 'prepaid'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    business_name = db.Column(db.String(200), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('supplier_categories.id'), nullable=False)
    
    # Business information
    tax_id = db.Column(db.String(50), nullable=True)  # GST/VAT number
    registration_number = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    
    # Contact information
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    fax = db.Column(db.String(20), nullable=True)
    
    # Address
    address_line_1 = db.Column(db.Text, nullable=True)
    address_line_2 = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True, default='India')
    
    # Business preferences
    payment_terms = db.Column(db.String(20), default=PAYMENT_TERMS_NET_30)
    credit_limit = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(3), default='INR')
    lead_time_days = db.Column(db.Integer, default=3)
    minimum_order_value = db.Column(db.Numeric(10, 2), default=0)
    delivery_charge = db.Column(db.Numeric(10, 2), default=0)
    
    # Status and ratings
    status = db.Column(db.String(20), default=STATUS_PENDING)
    overall_rating = db.Column(db.Numeric(3, 2), default=0)  # 0.00 to 5.00
    quality_rating = db.Column(db.Numeric(3, 2), default=0)
    delivery_rating = db.Column(db.Numeric(3, 2), default=0)
    price_rating = db.Column(db.Numeric(3, 2), default=0)
    
    # Performance metrics
    total_orders = db.Column(db.Integer, default=0)
    on_time_delivery_rate = db.Column(db.Numeric(5, 2), default=0)
    quality_issue_rate = db.Column(db.Numeric(5, 2), default=0)
    average_delivery_time = db.Column(db.Integer, default=0)  # in hours
    
    # Contract and certification
    contract_start_date = db.Column(db.Date, nullable=True)
    contract_end_date = db.Column(db.Date, nullable=True)
    contract_value = db.Column(db.Numeric(15, 2), nullable=True)
    is_preferred = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    
    # Notes and preferences
    notes = db.Column(db.Text, nullable=True)
    special_instructions = db.Column(db.Text, nullable=True)
    preferences = db.Column(db.Text, default='{}')  # JSON for additional preferences
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_order_date = db.Column(db.Date, nullable=True)
    last_contact_date = db.Column(db.Date, nullable=True)
    
    # Relationships
    contacts = db.relationship('SupplierContact', backref='supplier', lazy=True, cascade='all, delete-orphan')
    documents = db.relationship('SupplierDocument', backref='supplier', lazy=True, cascade='all, delete-orphan')
    ratings = db.relationship('SupplierRating', backref='supplier', lazy=True, cascade='all, delete-orphan')
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)
    price_histories = db.relationship('SupplierPriceHistory', backref='supplier', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, name, category_id, supplier_code=None):
        self.name = name
        self.category_id = category_id
        self.supplier_code = supplier_code or self.generate_supplier_code()
    
    @staticmethod
    def generate_supplier_code():
        """Generate unique supplier code"""
        prefix = "SUP"
        date_str = datetime.now().strftime("%Y%m")
        random_str = str(uuid.uuid4())[:4].upper()
        return f"{prefix}{date_str}{random_str}"
    
    @property
    def is_active_supplier(self):
        """Check if supplier is active"""
        return self.status == self.STATUS_ACTIVE
    
    @property
    def is_approved_supplier(self):
        """Check if supplier is approved"""
        return self.is_approved and self.status in [self.STATUS_ACTIVE, self.STATUS_PENDING]
    
    @property
    def contract_active(self):
        """Check if contract is currently active"""
        if not self.contract_start_date or not self.contract_end_date:
            return False
        today = date.today()
        return self.contract_start_date <= today <= self.contract_end_date
    
    @property
    def formatted_credit_limit(self):
        """Get formatted credit limit"""
        return f"₹{self.credit_limit:.2f}" if self.credit_limit else "₹0.00"
    
    @property
    def formatted_minimum_order(self):
        """Get formatted minimum order value"""
        return f"₹{self.minimum_order_value:.2f}" if self.minimum_order_value else "₹0.00"
    
    @property
    def formatted_delivery_charge(self):
        """Get formatted delivery charge"""
        return f"₹{self.delivery_charge:.2f}" if self.delivery_charge else "₹0.00"
    
    @property
    def full_address(self):
        """Get full address as string"""
        address_parts = []
        if self.address_line_1:
            address_parts.append(self.address_line_1)
        if self.address_line_2:
            address_parts.append(self.address_line_2)
        if self.city:
            address_parts.append(self.city)
        if self.state:
            address_parts.append(self.state)
        if self.postal_code:
            address_parts.append(self.postal_code)
        if self.country:
            address_parts.append(self.country)
        return ", ".join(address_parts)
    
    def get_preferences(self):
        """Get supplier preferences as dictionary"""
        try:
            return json.loads(self.preferences) if self.preferences else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_preferences(self, preferences):
        """Set supplier preferences from dictionary"""
        self.preferences = json.dumps(preferences)
    
    def update_rating(self, quality=None, delivery=None, price=None):
        """Update supplier ratings"""
        if quality is not None:
            self.quality_rating = quality
        if delivery is not None:
            self.delivery_rating = delivery
        if price is not None:
            self.price_rating = price
        
        # Calculate overall rating as weighted average
        weights = {'quality': 0.4, 'delivery': 0.3, 'price': 0.3}
        ratings = []
        weights_sum = 0
        
        if self.quality_rating > 0:
            ratings.append(self.quality_rating * weights['quality'])
            weights_sum += weights['quality']
        if self.delivery_rating > 0:
            ratings.append(self.delivery_rating * weights['delivery'])
            weights_sum += weights['delivery']
        if self.price_rating > 0:
            ratings.append(self.price_rating * weights['price'])
            weights_sum += weights['price']
        
        if weights_sum > 0:
            self.overall_rating = sum(ratings) / weights_sum
        else:
            self.overall_rating = 0
        
        db.session.commit()
    
    def update_performance_metrics(self):
        """Update supplier performance metrics based on purchase orders"""
        from sqlalchemy import func, and_
        
        # Get completed orders for this supplier
        completed_orders = PurchaseOrder.query.filter(
            and_(
                PurchaseOrder.supplier_id == self.id,
                PurchaseOrder.status.in_(['Completed', 'Received'])
            )
        ).all()
        
        self.total_orders = len(completed_orders)
        
        if completed_orders:
            # Calculate on-time delivery rate
            on_time_orders = sum(1 for order in completed_orders if order.on_time_delivery)
            self.on_time_delivery_rate = (on_time_orders / len(completed_orders)) * 100
            
            # Calculate average delivery time
            delivery_times = [order.actual_delivery_time for order in completed_orders if order.actual_delivery_time]
            self.average_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
            
            # Calculate quality issue rate
            orders_with_issues = sum(1 for order in completed_orders if order.has_quality_issues)
            self.quality_issue_rate = (orders_with_issues / len(completed_orders)) * 100
        else:
            self.on_time_delivery_rate = 0
            self.average_delivery_time = 0
            self.quality_issue_rate = 0
        
        db.session.commit()
    
    def approve_supplier(self, approved_by=None):
        """Approve supplier"""
        self.is_approved = True
        self.status = self.STATUS_ACTIVE
        if approved_by:
            self.notes = (self.notes or "") + f"\nApproved by user ID {approved_by} on {datetime.utcnow().isoformat()}"
        db.session.commit()
    
    def suspend_supplier(self, reason=None):
        """Suspend supplier"""
        self.status = self.STATUS_SUSPENDED
        if reason:
            self.notes = (self.notes or "") + f"\nSuspended: {reason} on {datetime.utcnow().isoformat()}"
        db.session.commit()
    
    def blacklist_supplier(self, reason=None):
        """Blacklist supplier"""
        self.status = self.STATUS_BLACKLISTED
        if reason:
            self.notes = (self.notes or "") + f"\nBlacklisted: {reason} on {datetime.utcnow().isoformat()}"
        db.session.commit()
    
    def to_dict(self, include_relationships=False):
        data = {
            'id': self.id,
            'supplier_code': self.supplier_code,
            'name': self.name,
            'business_name': self.business_name,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'tax_id': self.tax_id,
            'registration_number': self.registration_number,
            'website': self.website,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'fax': self.fax,
            'address_line_1': self.address_line_1,
            'address_line_2': self.address_line_2,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'full_address': self.full_address,
            'payment_terms': self.payment_terms,
            'credit_limit': float(self.credit_limit) if self.credit_limit else 0,
            'formatted_credit_limit': self.formatted_credit_limit,
            'currency': self.currency,
            'lead_time_days': self.lead_time_days,
            'minimum_order_value': float(self.minimum_order_value) if self.minimum_order_value else 0,
            'formatted_minimum_order': self.formatted_minimum_order,
            'delivery_charge': float(self.delivery_charge) if self.delivery_charge else 0,
            'formatted_delivery_charge': self.formatted_delivery_charge,
            'status': self.status,
            'overall_rating': float(self.overall_rating) if self.overall_rating else 0,
            'quality_rating': float(self.quality_rating) if self.quality_rating else 0,
            'delivery_rating': float(self.delivery_rating) if self.delivery_rating else 0,
            'price_rating': float(self.price_rating) if self.price_rating else 0,
            'total_orders': self.total_orders,
            'on_time_delivery_rate': float(self.on_time_delivery_rate) if self.on_time_delivery_rate else 0,
            'quality_issue_rate': float(self.quality_issue_rate) if self.quality_issue_rate else 0,
            'average_delivery_time': self.average_delivery_time,
            'contract_start_date': self.contract_start_date.isoformat() if self.contract_start_date else None,
            'contract_end_date': self.contract_end_date.isoformat() if self.contract_end_date else None,
            'contract_value': float(self.contract_value) if self.contract_value else None,
            'contract_active': self.contract_active,
            'is_preferred': self.is_preferred,
            'is_approved': self.is_approved,
            'is_active_supplier': self.is_active_supplier,
            'is_approved_supplier': self.is_approved_supplier,
            'notes': self.notes,
            'special_instructions': self.special_instructions,
            'preferences': self.get_preferences(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_order_date': self.last_order_date.isoformat() if self.last_order_date else None,
            'last_contact_date': self.last_contact_date.isoformat() if self.last_contact_date else None
        }
        
        if include_relationships:
            data.update({
                'contacts': [contact.to_dict() for contact in self.contacts],
                'documents': [doc.to_dict() for doc in self.documents],
                'recent_ratings': [rating.to_dict() for rating in self.ratings[-5:]]  # Last 5 ratings
            })
        
        return data
    
    def __repr__(self):
        return f'<Supplier {self.name} ({self.supplier_code})>'


class SupplierContact(db.Model):
    """Multiple contact persons for each supplier"""
    __tablename__ = 'supplier_contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    
    # Contact details
    name = db.Column(db.String(120), nullable=False)
    position = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    fax = db.Column(db.String(20), nullable=True)
    
    # Contact preferences
    is_primary = db.Column(db.Boolean, default=False)
    is_billing_contact = db.Column(db.Boolean, default=False)
    is_technical_contact = db.Column(db.Boolean, default=False)
    is_sales_contact = db.Column(db.Boolean, default=False)
    
    # Availability
    availability_hours = db.Column(db.String(100), nullable=True)  # e.g., "9 AM - 6 PM"
    preferred_contact_method = db.Column(db.String(20), nullable=True)  # email, phone, mobile
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, supplier_id, name, position=None, email=None, phone=None):
        self.supplier_id = supplier_id
        self.name = name
        self.position = position
        self.email = email
        self.phone = phone
    
    @property
    def full_name_with_position(self):
        """Get full name with position"""
        if self.position:
            return f"{self.name} ({self.position})"
        return self.name
    
    def to_dict(self):
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'name': self.name,
            'position': self.position,
            'department': self.department,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'fax': self.fax,
            'is_primary': self.is_primary,
            'is_billing_contact': self.is_billing_contact,
            'is_technical_contact': self.is_technical_contact,
            'is_sales_contact': self.is_sales_contact,
            'availability_hours': self.availability_hours,
            'preferred_contact_method': self.preferred_contact_method,
            'full_name_with_position': self.full_name_with_position,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<SupplierContact {self.name}>'


class SupplierDocument(db.Model):
    """Documents related to suppliers (contracts, certifications, etc.)"""
    __tablename__ = 'supplier_documents'
    
    # Document types
    TYPE_CONTRACT = 'contract'
    TYPE_CERTIFICATION = 'certification'
    TYPE_LICENSE = 'license'
    TYPE_INSURANCE = 'insurance'
    TYPE_TAX_DOCUMENT = 'tax_document'
    TYPE_QUALITY_CERTIFICATE = 'quality_certificate'
    TYPE_OTHER = 'other'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    
    # Document information
    name = db.Column(db.String(200), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=True)  # Path to uploaded file
    file_size = db.Column(db.Integer, nullable=True)  # File size in bytes
    mime_type = db.Column(db.String(100), nullable=True)
    
    # Document validity
    issue_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    is_expired = db.Column(db.Boolean, default=False)
    
    # Document status
    is_verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    verification_notes = db.Column(db.Text, nullable=True)
    
    # Document priority
    is_mandatory = db.Column(db.Boolean, default=False)
    priority_level = db.Column(db.Integer, default=1)  # 1=Low, 2=Medium, 3=High, 4=Critical
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    verified_by_user = db.relationship('User', backref='verified_documents', foreign_keys=[verified_by])
    
    def __init__(self, supplier_id, name, document_type, description=None):
        self.supplier_id = supplier_id
        self.name = name
        self.document_type = document_type
        self.description = description
    
    @property
    def is_valid(self):
        """Check if document is currently valid"""
        if not self.expiry_date:
            return True
        return date.today() <= self.expiry_date
    
    @property
    def days_until_expiry(self):
        """Get days until document expires"""
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days
    
    @property
    def expiry_status(self):
        """Get expiry status for display"""
        if not self.expiry_date:
            return 'No Expiry'
        
        days = self.days_until_expiry
        if days < 0:
            return 'Expired'
        elif days <= 30:
            return 'Expiring Soon'
        else:
            return 'Valid'
    
    def verify_document(self, verified_by, notes=None):
        """Verify document"""
        self.is_verified = True
        self.verified_by = verified_by
        self.verified_at = datetime.utcnow()
        if notes:
            self.verification_notes = notes
        db.session.commit()
    
    def mark_expired(self):
        """Mark document as expired"""
        self.is_expired = True
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'name': self.name,
            'document_type': self.document_type,
            'description': self.description,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_expired': self.is_expired,
            'is_valid': self.is_valid,
            'days_until_expiry': self.days_until_expiry,
            'expiry_status': self.expiry_status,
            'is_verified': self.is_verified,
            'verified_by': self.verified_by,
            'verified_by_name': self.verified_by_user.username if self.verified_by_user else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'verification_notes': self.verification_notes,
            'is_mandatory': self.is_mandatory,
            'priority_level': self.priority_level,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<SupplierDocument {self.name} ({self.document_type})>'


class SupplierRating(db.Model):
    """Supplier rating system for performance tracking"""
    __tablename__ = 'supplier_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=True)
    
    # Rating criteria (1-5 scale)
    quality_rating = db.Column(db.Numeric(3, 2), nullable=False)
    delivery_rating = db.Column(db.Numeric(3, 2), nullable=False)
    price_rating = db.Column(db.Numeric(3, 2), nullable=False)
    service_rating = db.Column(db.Numeric(3, 2), nullable=False)
    overall_rating = db.Column(db.Numeric(3, 2), nullable=False)
    
    # Additional feedback
    quality_comments = db.Column(db.Text, nullable=True)
    delivery_comments = db.Column(db.Text, nullable=True)
    price_comments = db.Column(db.Text, nullable=True)
    service_comments = db.Column(db.Text, nullable=True)
    general_comments = db.Column(db.Text, nullable=True)
    
    # Rating metadata
    rated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Improvement suggestions
    improvement_suggestions = db.Column(db.Text, nullable=True)
    would_recommend = db.Column(db.Boolean, nullable=True)
    
    # Relationships
    rated_by_user = db.relationship('User', backref='supplier_ratings', foreign_keys=[rated_by])
    
    def __init__(self, supplier_id, quality_rating, delivery_rating, price_rating, service_rating, rated_by):
        self.supplier_id = supplier_id
        self.quality_rating = quality_rating
        self.delivery_rating = delivery_rating
        self.price_rating = price_rating
        self.service_rating = service_rating
        self.rated_by = rated_by
        self.calculate_overall_rating()
    
    def calculate_overall_rating(self):
        """Calculate overall rating as weighted average"""
        weights = {
            'quality': 0.35,
            'delivery': 0.25,
            'price': 0.25,
            'service': 0.15
        }
        
        total_weighted_score = (
            float(self.quality_rating) * weights['quality'] +
            float(self.delivery_rating) * weights['delivery'] +
            float(self.price_rating) * weights['price'] +
            float(self.service_rating) * weights['service']
        )
        
        self.overall_rating = round(total_weighted_score, 2)
    
    @property
    def rating_stars(self):
        """Get star rating representation"""
        return '★' * int(float(self.overall_rating)) + '☆' * (5 - int(float(self.overall_rating)))
    
    def to_dict(self):
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'purchase_order_id': self.purchase_order_id,
            'quality_rating': float(self.quality_rating),
            'delivery_rating': float(self.delivery_rating),
            'price_rating': float(self.price_rating),
            'service_rating': float(self.service_rating),
            'overall_rating': float(self.overall_rating),
            'rating_stars': self.rating_stars,
            'quality_comments': self.quality_comments,
            'delivery_comments': self.delivery_comments,
            'price_comments': self.price_comments,
            'service_comments': self.service_comments,
            'general_comments': self.general_comments,
            'rated_by': self.rated_by,
            'rated_by_name': self.rated_by_user.username if self.rated_by_user else None,
            'rated_at': self.rated_at.isoformat() if self.rated_at else None,
            'improvement_suggestions': self.improvement_suggestions,
            'would_recommend': self.would_recommend
        }
    
    def __repr__(self):
        return f'<SupplierRating {self.supplier_id} - {self.overall_rating} stars>'