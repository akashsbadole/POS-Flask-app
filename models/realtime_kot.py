"""
Real-time KOT (Kitchen Order Ticket) Models
Enhanced models for WebSocket-based real-time order management
"""

from datetime import datetime, timedelta
from . import db
import json
import uuid

class KitchenDisplay(db.Model):
    """Kitchen Display sessions for real-time order management"""
    __tablename__ = 'kitchen_displays'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    station_type = db.Column(db.String(50), default='general')  # general, grill, fry, salad, dessert
    kitchen_role = db.Column(db.String(50), default='kitchen_staff')  # kitchen_staff, chef, head_chef
    
    # Connection management
    socket_id = db.Column(db.String(100), nullable=True)
    is_connected = db.Column(db.Boolean, default=False)
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
    connected_at = db.Column(db.DateTime, nullable=True)
    disconnected_at = db.Column(db.DateTime, nullable=True)
    
    # Display preferences
    auto_refresh = db.Column(db.Boolean, default=True)
    refresh_interval = db.Column(db.Integer, default=30)  # seconds
    sound_enabled = db.Column(db.Boolean, default=True)
    priority_orders_only = db.Column(db.Boolean, default=False)
    
    # Filter preferences
    status_filter = db.Column(db.String(50), default='all')  # all, new, progress, ready
    urgency_filter = db.Column(db.String(20), default='all')  # all, normal, medium, high
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __init__(self, session_id, display_name, kitchen_role='kitchen_staff', created_by=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.display_name = display_name
        self.kitchen_role = kitchen_role
        self.created_by = created_by
    
    @property
    def is_active(self):
        """Check if display is currently active"""
        return self.is_connected and self.last_heartbeat > datetime.utcnow() - timedelta(minutes=5)
    
    @property
    def connection_duration(self):
        """Get connection duration in minutes"""
        if not self.connected_at:
            return 0
        end_time = self.disconnected_at or datetime.utcnow()
        return int((end_time - self.connected_at).total_seconds() / 60)
    
    def update_heartbeat(self):
        """Update heartbeat timestamp"""
        self.last_heartbeat = datetime.utcnow()
        if not self.is_connected:
            self.is_connected = True
            self.connected_at = datetime.utcnow()
        db.session.commit()
    
    def connect(self, socket_id):
        """Connect display with socket ID"""
        self.socket_id = socket_id
        self.is_connected = True
        self.connected_at = self.connected_at or datetime.utcnow()
        self.update_heartbeat()
        db.session.commit()
    
    def disconnect(self):
        """Disconnect display"""
        self.socket_id = None
        self.is_connected = False
        self.disconnected_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'display_name': self.display_name,
            'station_type': self.station_type,
            'kitchen_role': self.kitchen_role,
            'is_connected': self.is_connected,
            'is_active': self.is_active,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'disconnected_at': self.disconnected_at.isoformat() if self.disconnected_at else None,
            'connection_duration': self.connection_duration,
            'auto_refresh': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'sound_enabled': self.sound_enabled,
            'priority_orders_only': self.priority_orders_only,
            'status_filter': self.status_filter,
            'urgency_filter': self.urgency_filter,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<KitchenDisplay {self.display_name} ({self.session_id})>'


class KOTEvent(db.Model):
    """KOT Events for real-time order tracking"""
    __tablename__ = 'kot_events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(100), unique=True, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # new_order, order_update, order_modification, order_complete, kitchen_alert
    
    # Related objects
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=True)
    kitchen_display_id = db.Column(db.Integer, db.ForeignKey('kitchen_displays.id'), nullable=True)
    
    # Event data
    event_data = db.Column(db.Text, nullable=True)  # JSON string
    old_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=True)
    
    # User information
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_role = db.Column(db.String(50), nullable=False)
    
    # Event metadata
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, critical
    is_urgent = db.Column(db.Boolean, default=False)
    requires_action = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    order = db.relationship('Order', backref='kot_events', foreign_keys=[order_id])
    order_item = db.relationship('OrderItem', backref='kot_events', foreign_keys=[order_item_id])
    kitchen_display = db.relationship('KitchenDisplay', backref='kot_events')
    
    def __init__(self, event_type, user_id, user_role, order_id=None, order_item_id=None, kitchen_display_id=None):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.user_id = user_id
        self.user_role = user_role
        self.order_id = order_id
        self.order_item_id = order_item_id
        self.kitchen_display_id = kitchen_display_id
    
    def set_event_data(self, data):
        """Set event data as JSON"""
        self.event_data = json.dumps(data) if data else None
    
    def get_event_data(self):
        """Get event data from JSON"""
        return json.loads(self.event_data) if self.event_data else None
    
    def mark_processed(self):
        """Mark event as processed"""
        self.processed_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'event_type': self.event_type,
            'order_id': self.order_id,
            'order_item_id': self.order_item_id,
            'kitchen_display_id': self.kitchen_display_id,
            'event_data': self.get_event_data(),
            'old_status': self.old_status,
            'new_status': self.new_status,
            'user_id': self.user_id,
            'user_role': self.user_role,
            'priority': self.priority,
            'is_urgent': self.is_urgent,
            'requires_action': self.requires_action,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
    
    def __repr__(self):
        return f'<KOTEvent {self.event_type} (Order: {self.order_id})>'


class OrderStatusHistory(db.Model):
    """Complete audit trail for order status changes"""
    __tablename__ = 'order_status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    
    # Status change information
    previous_status = db.Column(db.String(50), nullable=False)
    new_status = db.Column(db.String(50), nullable=False)
    status_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User information
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    changed_by_username = db.Column(db.String(100), nullable=False)
    changed_by_role = db.Column(db.String(50), nullable=False)
    
    # Additional context
    reason = db.Column(db.String(255), nullable=True)  # Reason for status change
    notes = db.Column(db.Text, nullable=True)  # Additional notes
    
    # Item-specific changes (for individual item status updates)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=True)
    
    # WebSocket event linkage
    related_event_id = db.Column(db.Integer, db.ForeignKey('kot_events.id'), nullable=True)
    
    # Metadata
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    user_agent = db.Column(db.Text, nullable=True)
    
    # Relationships
    order = db.relationship('Order', backref='status_history')
    order_item = db.relationship('OrderItem', backref='status_history')
    related_event = db.relationship('KOTEvent', backref='status_changes')
    
    def __repr__(self):
        return f'<OrderStatusHistory Order {self.order_id}: {self.previous_status} -> {self.new_status}>'


class RealTimeMetrics(db.Model):
    """Real-time performance metrics for kitchen operations"""
    __tablename__ = 'real_time_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_type = db.Column(db.String(50), nullable=False)  # kitchen_performance, order_velocity, display_health
    
    # Metric data
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Numeric(10, 2), nullable=False)
    metric_unit = db.Column(db.String(20), nullable=True)  # minutes, orders, percentage, etc.
    
    # Context
    station_type = db.Column(db.String(50), nullable=True)  # general, grill, fry, etc.
    time_period = db.Column(db.String(50), default='realtime')  # realtime, hourly, daily
    
    # Metadata
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    data_source = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<RealTimeMetrics {self.metric_name}: {self.metric_value} {self.metric_unit}>'


# Enhanced Order model extensions for real-time features
def enhance_order_model():
    """Add real-time fields to Order model"""
    from .order import Order
    
    # Add real-time specific fields to Order model using try-catch to avoid duplicate errors
    try:
        if not hasattr(Order, 'realtime_enabled'):
            Order.realtime_enabled = db.Column(db.Boolean, default=True)
    except Exception:
        pass
    
    try:
        if not hasattr(Order, 'websocket_broadcast'):
            Order.websocket_broadcast = db.Column(db.Boolean, default=True)
    except Exception:
        pass
    
    try:
        if not hasattr(Order, 'priority_level'):
            Order.priority_level = db.Column(db.String(20), default='normal')  # low, normal, high, critical
    except Exception:
        pass
    
    try:
        if not hasattr(Order, 'estimated_prep_time'):
            Order.estimated_prep_time = db.Column(db.Integer, nullable=True)  # minutes
    except Exception:
        pass
    
    try:
        if not hasattr(Order, 'actual_prep_time'):
            Order.actual_prep_time = db.Column(db.Integer, nullable=True)  # minutes
    except Exception:
        pass
    
    try:
        if not hasattr(Order, 'kitchen_station'):
            Order.kitchen_station = db.Column(db.String(50), nullable=True)  # grill, fry, salad, dessert
    except Exception:
        pass
    
    try:
        if not hasattr(Order, 'last_websocket_update'):
            Order.last_websocket_update = db.Column(db.DateTime, nullable=True)
    except Exception:
        pass
    
    try:
        if not hasattr(Order, 'realtime_subscribers'):
            Order.realtime_subscribers = db.Column(db.Integer, default=0)
    except Exception:
        pass
    
    # Add method to Order class for real-time updates
    def broadcast_status_change(self, old_status, new_status, user_id, user_role):
        """Broadcast status change via WebSocket"""
        from . import db
        
        # Create KOT event
        event = KOTEvent(
            event_type='order_update',
            user_id=user_id,
            user_role=user_role,
            order_id=self.id
        )
        event.old_status = old_status
        event.new_status = new_status
        event.set_event_data({
            'order_id': self.id,
            'order_number': self.order_number,
            'old_status': old_status,
            'new_status': new_status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Create status history entry
        history = OrderStatusHistory(
            order_id=self.id,
            previous_status=old_status,
            new_status=new_status,
            changed_by_user_id=user_id,
            changed_by_role=user_role
        )
        
        # Update order timestamp
        self.last_websocket_update = datetime.utcnow()
        
        db.session.add(event)
        db.session.add(history)
        db.session.commit()
        
        return event
    
    # Add method to OrderItem model for real-time updates
    def broadcast_item_status_change(self, old_status, new_status, user_id, user_role):
        """Broadcast item status change via WebSocket"""
        from . import db
        
        # Create KOT event
        event = KOTEvent(
            event_type='order_update',
            user_id=user_id,
            user_role=user_role,
            order_id=self.order_id,
            order_item_id=self.id
        )
        event.old_status = old_status
        event.new_status = new_status
        event.set_event_data({
            'order_id': self.order_id,
            'order_item_id': self.id,
            'item_name': self.item_name,
            'old_status': old_status,
            'new_status': new_status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Create status history entry
        history = OrderStatusHistory(
            order_id=self.order_id,
            previous_status=old_status,
            new_status=new_status,
            changed_by_user_id=user_id,
            changed_by_role=user_role,
            order_item_id=self.id
        )
        
        db.session.add(event)
        db.session.add(history)
        db.session.commit()
        
        return event
    
    # Bind methods to models
    Order.broadcast_status_change = broadcast_status_change
    from .order import OrderItem
    OrderItem.broadcast_status_change = broadcast_item_status_change