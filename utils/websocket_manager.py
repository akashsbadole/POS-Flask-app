"""
WebSocket Integration for Real-time Workflow Updates

This module provides WebSocket support for real-time notifications
and updates across the workflow system.
"""

from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user
from datetime import datetime
import json
import uuid


class WorkflowWebSocketManager:
    """Manager for WebSocket connections and real-time workflow updates"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.connected_users = {}  # user_id -> set of session_ids
        self.order_rooms = {}      # order_id -> set of session_ids
        self.inventory_rooms = {}  # inventory_item_id -> set of session_ids
        
        # Register event handlers
        self.register_handlers()
    
    def register_handlers(self):
        """Register WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            if current_user.is_authenticated:
                user_id = str(current_user.id)
                session_id = request.sid
                
                if user_id not in self.connected_users:
                    self.connected_users[user_id] = set()
                self.connected_users[user_id].add(session_id)
                
                # Join user-specific room
                join_room(f"user_{user_id}")
                
                emit('connected', {
                    'user_id': user_id,
                    'session_id': session_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            if current_user.is_authenticated:
                user_id = str(current_user.id)
                session_id = request.sid
                
                if user_id in self.connected_users:
                    self.connected_users[user_id].discard(session_id)
                    if not self.connected_users[user_id]:
                        del self.connected_users[user_id]
                
                # Clean up order rooms
                for order_id, sessions in list(self.order_rooms.items()):
                    sessions.discard(session_id)
                    if not sessions:
                        del self.order_rooms[order_id]
                
                # Clean up inventory rooms
                for item_id, sessions in list(self.inventory_rooms.items()):
                    sessions.discard(session_id)
                    if not sessions:
                        del self.inventory_rooms[item_id]
        
        @self.socketio.on('join_order')
        def handle_join_order(data):
            order_id = data.get('order_id')
            if order_id:
                session_id = request.sid
                
                if order_id not in self.order_rooms:
                    self.order_rooms[order_id] = set()
                self.order_rooms[order_id].add(session_id)
                
                join_room(f"order_{order_id}")
                emit('joined_order', {'order_id': order_id})
        
        @self.socketio.on('leave_order')
        def handle_leave_order(data):
            order_id = data.get('order_id')
            if order_id:
                session_id = request.sid
                
                if order_id in self.order_rooms:
                    self.order_rooms[order_id].discard(session_id)
                    if not self.order_rooms[order_id]:
                        del self.order_rooms[order_id]
                
                leave_room(f"order_{order_id}")
                emit('left_order', {'order_id': order_id})
        
        @self.socketio.on('join_inventory')
        def handle_join_inventory(data):
            item_id = data.get('item_id')
            if item_id:
                session_id = request.sid
                
                if item_id not in self.inventory_rooms:
                    self.inventory_rooms[item_id] = set()
                self.inventory_rooms[item_id].add(session_id)
                
                join_room(f"inventory_{item_id}")
                emit('joined_inventory', {'item_id': item_id})
        
        @self.socketio.on('join_kitchen')
        def handle_join_kitchen():
            join_room('kitchen_display')
            emit('joined_kitchen', {'message': 'Connected to kitchen display'})
        
        @self.socketio.on('workflow_action')
        def handle_workflow_action(data):
            """Handle workflow action requests via WebSocket"""
            action_type = data.get('type')  # 'order' or 'inventory'
            action = data.get('action')
            entity_id = data.get('entity_id')
            data_payload = data.get('data', {})
            
            if action_type == 'order':
                self.handle_order_workflow_action(entity_id, action, data_payload)
            elif action_type == 'inventory':
                self.handle_inventory_workflow_action(entity_id, action, data_payload)
    
    def handle_order_workflow_action(self, order_id, action, data):
        """Handle order workflow actions via WebSocket"""
        try:
            from utils.order_workflow import order_workflow, WorkflowAction
            from models import Order
            
            order = Order.query.get(order_id)
            if not order:
                emit('workflow_error', {
                    'type': 'order',
                    'action': action,
                    'error': 'Order not found'
                })
                return
            
            # Convert string action to enum
            try:
                workflow_action = WorkflowAction(action)
            except ValueError:
                emit('workflow_error', {
                    'type': 'order',
                    'action': action,
                    'error': 'Invalid workflow action'
                })
                return
            
            # Execute workflow action
            success, message, result = order_workflow.execute_workflow_action(
                current_user, order_id, workflow_action, data
            )
            
            if success:
                # Broadcast to all users watching this order
                emit('order_workflow_update', {
                    'order_id': order_id,
                    'action': action,
                    'result': result,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"order_{order_id}")
                
                # Also broadcast to kitchen display if relevant
                if action in ['send_to_kitchen', 'mark_ready']:
                    emit('kitchen_update', {
                        'order_id': order_id,
                        'action': action,
                        'order_data': order.to_dict(),
                        'timestamp': datetime.utcnow().isoformat()
                    }, room='kitchen_display')
                
                emit('workflow_success', {
                    'type': 'order',
                    'action': action,
                    'message': message,
                    'result': result
                })
            else:
                emit('workflow_error', {
                    'type': 'order',
                    'action': action,
                    'error': message
                })
        
        except Exception as e:
            emit('workflow_error', {
                'type': 'order',
                'action': action,
                'error': str(e)
            })
    
    def handle_inventory_workflow_action(self, item_id, action, data):
        """Handle inventory workflow actions via WebSocket"""
        try:
            from utils.inventory_workflow import inventory_workflow, InventoryAction
            from models import MenuItem
            
            item = MenuItem.query.get(item_id)
            if not item:
                emit('workflow_error', {
                    'type': 'inventory',
                    'action': action,
                    'error': 'Item not found'
                })
                return
            
            # Convert string action to enum
            try:
                inventory_action = InventoryAction(action)
            except ValueError:
                emit('workflow_error', {
                    'type': 'inventory',
                    'action': action,
                    'error': 'Invalid inventory action'
                })
                return
            
            # Execute workflow action
            success, message, result = inventory_workflow.process_inventory_action(
                current_user, item_id, inventory_action, data
            )
            
            if success:
                # Broadcast to all users watching this inventory item
                emit('inventory_workflow_update', {
                    'item_id': item_id,
                    'action': action,
                    'result': result,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"inventory_{item_id}")
                
                # Broadcast inventory alerts if critical
                if result.get('status') in ['critical', 'out_of_stock']:
                    emit('inventory_alert', {
                        'item_id': item_id,
                        'item_name': item.name,
                        'status': result.get('status'),
                        'message': message,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
                emit('workflow_success', {
                    'type': 'inventory',
                    'action': action,
                    'message': message,
                    'result': result
                })
            else:
                emit('workflow_error', {
                    'type': 'inventory',
                    'action': action,
                    'error': message
                })
        
        except Exception as e:
            emit('workflow_error', {
                'type': 'inventory',
                'action': action,
                'error': str(e)
            })
    
    def broadcast_order_update(self, order_id, update_type, data):
        """Broadcast order update to connected clients"""
        self.socketio.emit('order_update', {
            'order_id': order_id,
            'update_type': update_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"order_{order_id}")
    
    def broadcast_inventory_update(self, item_id, update_type, data):
        """Broadcast inventory update to connected clients"""
        self.socketio.emit('inventory_update', {
            'item_id': item_id,
            'update_type': update_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"inventory_{item_id}")
    
    def broadcast_kitchen_update(self, update_type, data):
        """Broadcast update to all kitchen displays"""
        self.socketio.emit('kitchen_update', {
            'update_type': update_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }, room='kitchen_display')
    
    def send_notification(self, user_id, notification_type, title, message, data=None):
        """Send notification to specific user"""
        self.socketio.emit('notification', {
            'type': notification_type,
            'title': title,
            'message': message,
            'data': data or {},
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"user_{user_id}")
    
    def broadcast_system_notification(self, notification_type, title, message, data=None):
        """Broadcast notification to all connected users"""
        self.socketio.emit('system_notification', {
            'type': notification_type,
            'title': title,
            'message': message,
            'data': data or {},
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_connected_users_count(self):
        """Get count of connected users"""
        return len(self.connected_users)
    
    def get_order_viewers_count(self, order_id):
        """Get count of users viewing specific order"""
        return len(self.order_rooms.get(order_id, set()))
    
    def get_kitchen_viewers_count(self):
        """Get count of users connected to kitchen display"""
        # This would require tracking kitchen room members
        return len(self.connected_users)  # Simplified for now


# Global WebSocket manager instance
websocket_manager = None

def init_websocket(app):
    """Initialize WebSocket with Flask app"""
    global websocket_manager
    
    socketio = SocketIO(app, cors_allowed_origins="*")
    websocket_manager = WorkflowWebSocketManager(socketio)
    
    return socketio

def get_websocket_manager():
    """Get the global WebSocket manager instance"""
    return websocket_manager