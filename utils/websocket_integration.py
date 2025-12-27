"""
WebSocket Integration for Order Modifications
Real-time notifications and updates for modification system
"""

from datetime import datetime
from models import db
from models.order_modification import OrderModification, OrderItemModification
from models.realtime_kot import KOTEvent
import json


class ModificationWebSocketManager:
    """Manages WebSocket integration for order modifications"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        
        # Modification event types
        self.MODIFICATION_EVENTS = {
            'created': 'modification_created',
            'approved': 'modification_approved',
            'rejected': 'modification_rejected',
            'implemented': 'modification_implemented',
            'cancelled': 'modification_cancelled',
            'failed': 'modification_failed'
        }
        
        # Kitchen-specific modification notifications
        self.KITCHEN_EVENTS = {
            'new_items': 'kitchen_new_items',
            'removed_items': 'kitchen_removed_items',
            'quantity_changes': 'kitchen_quantity_changes',
            'item_substitutions': 'kitchen_item_substitutions',
            'special_instructions': 'kitchen_special_instructions',
            'order_hold': 'kitchen_order_hold',
            'order_cancel': 'kitchen_order_cancel'
        }
    
    def broadcast_modification_event(self, modification, event_type, target_rooms=None):
        """Broadcast modification event to connected clients"""
        try:
            if not self.socketio:
                return False
            
            event_data = self._prepare_modification_event_data(modification, event_type)
            
            # Default target rooms
            if not target_rooms:
                target_rooms = self._get_target_rooms(modification)
            
            # Broadcast to all target rooms
            for room in target_rooms:
                self.socketio.emit(self.MODIFICATION_EVENTS.get(event_type, 'modification_update'), 
                                 event_data, room=room)
            
            return True
            
        except Exception as e:
            print(f"Error broadcasting modification event: {e}")
            return False
    
    def broadcast_kitchen_modification_notification(self, modification):
        """Send specific notifications to kitchen displays"""
        try:
            if not self.socketio:
                return False
            
            kitchen_rooms = ['kitchen_general', 'kitchen_grill', 'kitchen_fry', 'kitchen_salad', 'kitchen_dessert']
            
            # Process each item modification
            for item_mod in modification.item_modifications:
                kitchen_data = self._prepare_kitchen_notification_data(modification, item_mod)
                event_type = self._get_kitchen_event_type(item_mod)
                
                # Broadcast to all kitchen rooms
                for room in kitchen_rooms:
                    self.socketio.emit(event_type, kitchen_data, room=room)
            
            return True
            
        except Exception as e:
            print(f"Error broadcasting kitchen modification notification: {e}")
            return False
    
    def notify_modification_request(self, modification, request_data):
        """Notify managers about new modification requests"""
        try:
            if not self.socketio:
                return False
            
            notification_data = {
                'type': 'modification_request',
                'modification_id': modification.modification_id,
                'order_id': modification.order_id,
                'order_number': modification.order.order_number if modification.order else 'Unknown',
                'modification_type': modification.modification_type,
                'priority': modification.priority,
                'price_difference': float(modification.price_difference),
                'requested_by': modification.requested_by.username if modification.requested_by else 'Unknown',
                'reason': modification.reason,
                'timestamp': modification.requested_at.isoformat(),
                'requires_approval': modification.requires_approval,
                'estimated_response_time': self._calculate_estimated_response_time(modification)
            }
            
            # Notify manager rooms
            manager_rooms = ['managers', 'admins']
            for room in manager_rooms:
                self.socketio.emit('new_modification_request', notification_data, room=room)
            
            return True
            
        except Exception as e:
            print(f"Error notifying modification request: {e}")
            return False
    
    def notify_modification_approval(self, modification, approver, notes=None):
        """Notify about modification approval"""
        try:
            if not self.socketio:
                return False
            
            approval_data = {
                'type': 'modification_approved',
                'modification_id': modification.modification_id,
                'order_id': modification.order_id,
                'order_number': modification.order.order_number if modification.order else 'Unknown',
                'approved_by': approver.username,
                'approved_by_role': approver.role,
                'notes': notes,
                'auto_approved': modification.auto_approved,
                'timestamp': modification.approved_at.isoformat()
            }
            
            # Notify relevant parties
            target_rooms = ['kitchen_general', 'managers']
            for room in target_rooms:
                self.socketio.emit('modification_approved', approval_data, room=room)
            
            return True
            
        except Exception as e:
            print(f"Error notifying modification approval: {e}")
            return False
    
    def notify_modification_rejection(self, modification, rejector, reason):
        """Notify about modification rejection"""
        try:
            if not self.socketio:
                return False
            
            rejection_data = {
                'type': 'modification_rejected',
                'modification_id': modification.modification_id,
                'order_id': modification.order_id,
                'order_number': modification.order.order_number if modification.order else 'Unknown',
                'rejected_by': rejector.username,
                'rejected_by_role': rejector.role,
                'reason': reason,
                'timestamp': modification.approved_at.isoformat()
            }
            
            # Notify requester and managers
            target_rooms = ['managers']
            if modification.requested_by_user_id:
                target_rooms.append(f'user_{modification.requested_by_user_id}')
            
            for room in target_rooms:
                self.socketio.emit('modification_rejected', rejection_data, room=room)
            
            return True
            
        except Exception as e:
            print(f"Error notifying modification rejection: {e}")
            return False
    
    def notify_modification_implementation(self, modification, implementer):
        """Notify about modification implementation start/completion"""
        try:
            if not self.socketio:
                return False
            
            implementation_data = {
                'type': 'modification_implementation',
                'modification_id': modification.modification_id,
                'order_id': modification.order_id,
                'order_number': modification.order.order_number if modification.order else 'Unknown',
                'status': modification.status,
                'implemented_by': implementer.username,
                'implemented_by_role': implementer.role,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Notify all relevant parties
            target_rooms = ['kitchen_general', 'managers', 'waiters']
            for room in target_rooms:
                self.socketio.emit('modification_implementation', implementation_data, room=room)
            
            return True
            
        except Exception as e:
            print(f"Error notifying modification implementation: {e}")
            return False
    
    def update_kitchen_display_with_modification(self, modification):
        """Update kitchen displays with modification information"""
        try:
            if not self.socketio:
                return False
            
            # Get order information
            order = modification.order
            if not order:
                return False
            
            # Prepare display update
            display_update = {
                'order_id': order.id,
                'order_number': order.order_number,
                'modification_id': modification.modification_id,
                'modification_type': modification.modification_type,
                'status': modification.status,
                'priority': modification.priority,
                'items_affected': len(modification.item_modifications),
                'price_impact': float(modification.price_difference),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Add item details for kitchen
            if modification.item_modifications:
                display_update['item_changes'] = [
                    {
                        'type': item_mod.modification_type,
                        'item_name': item_mod.get_item_name(),
                        'original_quantity': item_mod.original_quantity,
                        'new_quantity': item_mod.new_quantity,
                        'special_instructions': item_mod.new_instructions,
                        'status': item_mod.status
                    }
                    for item_mod in modification.item_modifications
                ]
            
            # Update all kitchen displays
            kitchen_rooms = ['kitchen_general', 'kitchen_grill', 'kitchen_fry', 'kitchen_salad', 'kitchen_dessert']
            for room in kitchen_rooms:
                self.socketio.emit('order_modification_update', display_update, room=room)
            
            return True
            
        except Exception as e:
            print(f"Error updating kitchen display: {e}")
            return False
    
    def create_kot_event_for_modification(self, modification, event_type='order_modification'):
        """Create KOT event for modification tracking"""
        try:
            # Create KOT event for audit trail
            kot_event = KOTEvent(
                event_type=event_type,
                user_id=modification.requested_by_user_id,
                user_role=modification.requested_by.role if modification.requested_by else 'system',
                order_id=modification.order_id
            )
            
            # Set event data
            event_data = {
                'modification_id': modification.modification_id,
                'modification_type': modification.modification_type,
                'status': modification.status,
                'price_difference': float(modification.price_difference),
                'requested_at': modification.requested_at.isoformat(),
                'item_count': len(modification.item_modifications)
            }
            
            kot_event.set_event_data(event_data)
            kot_event.old_status = None
            kot_event.new_status = modification.status
            
            db.session.add(kot_event)
            db.session.commit()
            
            return kot_event
            
        except Exception as e:
            print(f"Error creating KOT event: {e}")
            return None
    
    def _prepare_modification_event_data(self, modification, event_type):
        """Prepare modification event data for broadcasting"""
        return {
            'type': self.MODIFICATION_EVENTS.get(event_type, 'modification_update'),
            'modification_id': modification.modification_id,
            'order_id': modification.order_id,
            'order_number': modification.order.order_number if modification.order else 'Unknown',
            'modification_type': modification.modification_type,
            'status': modification.status,
            'price_difference': float(modification.price_difference),
            'requested_by': modification.requested_by.username if modification.requested_by else 'Unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type
        }
    
    def _prepare_kitchen_notification_data(self, modification, item_modification):
        """Prepare kitchen-specific notification data"""
        return {
            'order_id': modification.order_id,
            'order_number': modification.order.order_number if modification.order else 'Unknown',
            'modification_id': modification.modification_id,
            'item_name': item_modification.get_item_name(),
            'modification_type': item_modification.modification_type,
            'original_quantity': item_modification.original_quantity,
            'new_quantity': item_modification.new_quantity,
            'special_instructions': item_modification.new_instructions,
            'timestamp': datetime.utcnow().isoformat(),
            'priority': modification.priority
        }
    
    def _get_target_rooms(self, modification):
        """Get target rooms for modification broadcast"""
        rooms = ['kitchen_general']
        
        # Add role-specific rooms
        if modification.requested_by_user_id:
            rooms.append(f'user_{modification.requested_by_user_id}')
        
        # Add kitchen stations based on modification type
        if modification.modification_type in ['add_items', 'remove_items', 'modify_items']:
            rooms.extend(['kitchen_grill', 'kitchen_fry', 'kitchen_salad'])
        
        # Add manager rooms for approvals
        if modification.requires_approval:
            rooms.extend(['managers', 'admins'])
        
        return rooms
    
    def _get_kitchen_event_type(self, item_modification):
        """Get appropriate kitchen event type for item modification"""
        event_mapping = {
            'add_item': self.KITCHEN_EVENTS['new_items'],
            'remove_item': self.KITCHEN_EVENTS['removed_items'],
            'change_quantity': self.KITCHEN_EVENTS['quantity_changes'],
            'change_item': self.KITCHEN_EVENTS['item_substitutions'],
            'update_instructions': self.KITCHEN_EVENTS['special_instructions']
        }
        
        return event_mapping.get(item_modification.modification_type, 'kitchen_modification_update')
    
    def _calculate_estimated_response_time(self, modification):
        """Calculate estimated response time for modification"""
        priority_times = {
            'low': 60,      # 60 minutes
            'normal': 30,   # 30 minutes
            'high': 15,     # 15 minutes
            'critical': 5   # 5 minutes
        }
        
        return priority_times.get(modification.priority, 30)


# Global instance
modification_websocket = ModificationWebSocketManager()


def init_modification_websocket(socketio):
    """Initialize modification WebSocket integration"""
    global modification_websocket
    modification_websocket.socketio = socketio
    return modification_websocket


def broadcast_modification_to_kitchen(modification, event_type='created'):
    """Helper function to broadcast modification to kitchen"""
    return modification_websocket.broadcast_modification_event(modification, event_type)


def notify_kitchen_of_modification(modification):
    """Helper function to notify kitchen of modification details"""
    return modification_websocket.broadcast_kitchen_modification_notification(modification)


def create_modification_kot_event(modification, event_type='order_modification'):
    """Helper function to create KOT event for modification"""
    return modification_websocket.create_kot_event_for_modification(modification, event_type)