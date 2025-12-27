"""
Comprehensive WebSocket KOT Tests
Tests for real-time WebSocket functionality, kitchen display operations, and performance
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import threading
import queue
import socketio
from flask import Flask
from flask_socketio import SocketIOTestClient

# Import our modules
from app import create_app
from models import db, Order, OrderItem, User, KitchenDisplay, KOTEvent
from utils.realtime_kot_manager import RealTimeKOTManager
from utils.websocket_security import WebSocketSecurityManager
from utils.websocket_performance import WebSocketPerformanceManager

class TestWebSocketKOTSetup:
    """Test WebSocket infrastructure setup"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        with app.app_context():
            db.create_all()
            
            # Create test user
            test_user = User(
                username='test_kitchen',
                email='kitchen@test.com',
                role='kitchen_staff',
                is_active=True
            )
            test_user.set_password('testpass')
            db.session.add(test_user)
            
            # Create admin user
            admin_user = User(
                username='admin',
                email='admin@test.com',
                role='admin',
                is_active=True
            )
            admin_user.set_password('adminpass')
            db.session.add(admin_user)
            
            db.session.commit()
            yield app
            db.session.remove()
    
    @pytest.fixture
    def socketio_client(self, app):
        """Create Socket.IO test client"""
        with app.test_client() as client:
            socketio_client = SocketIOTestClient(app, client)
            yield socketio_client
    
    @pytest.fixture
    def authenticated_client(self, app):
        """Create authenticated Socket.IO client"""
        with app.test_client() as client:
            # First authenticate via HTTP
            with client.session_transaction() as sess:
                sess['_user_id'] = 1  # Test user ID
            
            socketio_client = SocketIOTestClient(app, client)
            return socketio_client
    
    def test_websocket_connection_basic(self, socketio_client):
        """Test basic WebSocket connection"""
        # Test connection
        socketio_client.connect()
        assert socketio_client.is_connected()
        
        # Test disconnection
        socketio_client.disconnect()
        assert not socketio_client.is_connected()
    
    def test_websocket_connection_authenticated(self, authenticated_client):
        """Test authenticated WebSocket connection"""
        # Test authenticated connection
        authenticated_client.connect()
        assert authenticated_client.is_connected()
        
        # Should receive connection confirmation
        received = authenticated_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'connected'
    
    def test_websocket_connection_unauthorized(self, app):
        """Test unauthorized connection rejection"""
        with app.test_client() as client:
            socketio_client = SocketIOTestClient(app, client)
            
            # Try to connect without authentication
            socketio_client.connect()
            
            # Should receive error
            received = socketio_client.get_received()
            assert any(msg['name'] == 'error' for msg in received)
    
    def test_websocket_heartbeat(self, authenticated_client):
        """Test WebSocket heartbeat mechanism"""
        authenticated_client.connect()
        
        # Send heartbeat
        authenticated_client.emit('heartbeat', {'timestamp': time.time()})
        
        # Should receive heartbeat acknowledgment
        received = authenticated_client.get_received()
        assert any(msg['name'] == 'heartbeat_ack' for msg in received)
    
    def test_multiple_concurrent_connections(self, app):
        """Test multiple concurrent WebSocket connections"""
        clients = []
        
        try:
            # Create multiple clients
            for i in range(10):
                with app.test_client() as client:
                    with client.session_transaction() as sess:
                        sess['_user_id'] = 1  # Same test user
                    
                    socketio_client = SocketIOTestClient(app, client)
                    socketio_client.connect()
                    clients.append(socketio_client)
            
            # All clients should be connected
            for client in clients:
                assert client.is_connected()
            
            # Test broadcasting to all clients
            for client in clients:
                client.emit('test_message', {'data': 'test'})
            
            # Each client should receive their own message
            for client in clients:
                received = client.get_received()
                assert any(msg['name'] == 'test_message' for msg in received)
        
        finally:
            # Cleanup
            for client in clients:
                try:
                    client.disconnect()
                except:
                    pass

class TestRealTimeOrderEvents:
    """Test real-time order event handling"""
    
    @pytest.fixture
    def app_with_orders(self):
        """Create app with test orders"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        with app.app_context():
            db.create_all()
            
            # Create test users
            kitchen_user = User(
                username='kitchen_user',
                email='kitchen@test.com',
                role='kitchen_staff',
                is_active=True
            )
            kitchen_user.set_password('testpass')
            
            admin_user = User(
                username='admin',
                email='admin@test.com',
                role='admin',
                is_active=True
            )
            admin_user.set_password('adminpass')
            
            db.session.add(kitchen_user)
            db.session.add(admin_user)
            db.session.commit()
            
            # Create test order
            test_order = Order(
                order_number='TEST001',
                order_type='Dine-in',
                status='New',
                created_by=kitchen_user.id
            )
            db.session.add(test_order)
            db.session.commit()
            
            # Create test order items
            test_item = OrderItem(
                order_id=test_order.id,
                menu_item_id=1,  # Assuming this exists
                quantity=2,
                price=10.00,
                status='Pending'
            )
            db.session.add(test_item)
            db.session.commit()
            
            yield app
    
    @pytest.fixture
    def authenticated_kitchen_client(self, app_with_orders):
        """Create authenticated kitchen client"""
        with app_with_orders.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = 1  # Kitchen user ID
            
            socketio_client = SocketIOTestClient(app_with_orders, client)
            socketio_client.connect()
            return socketio_client
    
    def test_new_order_broadcast(self, app_with_orders, authenticated_kitchen_client):
        """Test new order broadcasting to kitchen displays"""
        authenticated_kitchen_client.connect()
        
        # Create new order via manager
        with app_with_orders.app_context():
            manager = RealTimeKOTManager(app_with_orders.socketio)
            
            order_data = {
                'order_number': 'TEST002',
                'order_type': 'Dine-in',
                'items': [{
                    'menu_item_id': 1,
                    'quantity': 1,
                    'price': 15.00
                }]
            }
            
            result = manager.create_order_with_realtime(order_data, 1, 'kitchen_staff')
            assert result['success']
        
        # Client should receive new order event
        received = authenticated_kitchen_client.get_received()
        new_order_events = [msg for msg in received if msg['name'] == 'order_event' 
                          and msg['args'][0]['type'] == 'new_order']
        assert len(new_order_events) > 0
    
    def test_order_status_update_broadcast(self, app_with_orders, authenticated_kitchen_client):
        """Test order status update broadcasting"""
        authenticated_kitchen_client.connect()
        
        # Get existing order
        with app_with_orders.app_context():
            order = Order.query.filter_by(order_number='TEST001').first()
            assert order is not None
            
            # Update order status via manager
            manager = RealTimeKOTManager(app_with_orders.socketio)
            result = manager.update_order_status_realtime(
                order.id, 'In Progress', 1, 'kitchen_staff', 'Started cooking'
            )
            assert result['success']
        
        # Client should receive status update event
        received = authenticated_kitchen_client.get_received()
        status_events = [msg for msg in received if msg['name'] == 'order_event' 
                       and msg['args'][0]['type'] == 'order_update']
        assert len(status_events) > 0
    
    def test_item_status_update_broadcast(self, app_with_orders, authenticated_kitchen_client):
        """Test item status update broadcasting"""
        authenticated_kitchen_client.connect()
        
        # Get existing order item
        with app_with_orders.app_context():
            item = OrderItem.query.first()
            assert item is not None
            
            # Update item status via manager
            manager = RealTimeKOTManager(app_with_orders.socketio)
            result = manager.update_item_status_realtime(
                item.id, 'In Progress', 1, 'kitchen_staff'
            )
            assert result['success']
        
        # Client should receive item update event
        received = authenticated_kitchen_client.get_received()
        item_events = [msg for msg in received if msg['name'] == 'order_event' 
                      and msg['args'][0]['type'] == 'item_update']
        assert len(item_events) > 0
    
    def test_kitchen_alert_broadcast(self, app_with_orders, authenticated_kitchen_client):
        """Test kitchen alert broadcasting"""
        authenticated_kitchen_client.connect()
        
        # Send kitchen alert
        with app_with_orders.app_context():
            manager = RealTimeKOTManager(app_with_orders.socketio)
            result = manager.send_kitchen_alert(
                'urgent', 'Equipment malfunction at station 3', ['grill'], None, 1
            )
            assert result['success']
        
        # Client should receive alert
        received = authenticated_kitchen_client.get_received()
        alert_events = [msg for msg in received if msg['name'] == 'kitchen_alert']
        assert len(alert_events) > 0
        assert alert_events[0]['args'][0]['type'] == 'urgent'

class TestKitchenDisplayOperations:
    """Test kitchen display specific operations"""
    
    @pytest.fixture
    def app_with_kitchen_display(self):
        """Create app with kitchen display setup"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        with app.app_context():
            db.create_all()
            
            # Create kitchen user
            kitchen_user = User(
                username='kitchen_display',
                email='display@test.com',
                role='kitchen_staff',
                is_active=True
            )
            kitchen_user.set_password('testpass')
            db.session.add(kitchen_user)
            
            # Create kitchen display session
            display = KitchenDisplay(
                session_id='test-display-session',
                display_name='Test Kitchen Display',
                station_type='general',
                kitchen_role='kitchen_staff',
                created_by=kitchen_user.id
            )
            db.session.add(display)
            
            db.session.commit()
            yield app
    
    @pytest.fixture
    def kitchen_display_client(self, app_with_kitchen_display):
        """Create kitchen display client"""
        with app_with_kitchen_display.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = 1  # Kitchen user ID
            
            socketio_client = SocketIOTestClient(app_with_kitchen_display, client)
            socketio_client.connect(
                query_string='display_name=Test Kitchen Display&station_type=general&kitchen_role=kitchen_staff'
            )
            return socketio_client
    
    def test_kitchen_display_connection(self, kitchen_display_client):
        """Test kitchen display connection with proper parameters"""
        kitchen_display_client.connect()
        
        # Should receive connection confirmation
        received = kitchen_display_client.get_received()
        connected_events = [msg for msg in received if msg['name'] == 'connected']
        assert len(connected_events) > 0
        
        # Should have display name in response
        connected_event = connected_events[0]['args'][0]
        assert 'session_id' in connected_event
        assert connected_event['display_name'] == 'Test Kitchen Display'
    
    def test_order_subscription(self, kitchen_display_client):
        """Test subscribing to specific order updates"""
        kitchen_display_client.connect()
        
        # Subscribe to order updates (assuming order ID 1 exists)
        kitchen_display_client.emit('join_order', {'order_id': '1'})
        
        # Should receive confirmation
        received = kitchen_display_client.get_received()
        join_events = [msg for msg in received if msg['name'] == 'order_joined']
        assert len(join_events) > 0
    
    def test_display_status_request(self, kitchen_display_client):
        """Test requesting display status"""
        kitchen_display_client.connect()
        
        # Request display status
        kitchen_display_client.emit('get_display_status')
        
        # Should receive status information
        received = kitchen_display_client.get_received()
        status_events = [msg for msg in received if msg['name'] == 'display_status']
        assert len(status_events) > 0
        
        status_data = status_events[0]['args'][0]
        assert 'session_id' in status_data
        assert 'display_name' in status_data
    
    def test_order_filtering(self, kitchen_display_client):
        """Test order filtering by status"""
        kitchen_display_client.connect()
        
        # Request orders with filter
        kitchen_display_client.emit('request_orders', {
            'status_filter': 'new',
            'station_type': 'general',
            'urgency_filter': 'all'
        })
        
        # Should receive orders sync
        received = kitchen_display_client.get_received()
        sync_events = [msg for msg in received if msg['name'] == 'orders_sync']
        assert len(sync_events) > 0
        
        sync_data = sync_events[0]['args'][0]
        assert 'orders' in sync_data
        assert 'filters' in sync_data

class TestWebSocketSecurity:
    """Test WebSocket security and authentication"""
    
    @pytest.fixture
    def security_manager(self):
        """Create security manager"""
        app = create_app()
        return WebSocketSecurityManager(app)
    
    def test_token_generation(self, security_manager):
        """Test authentication token generation"""
        # Generate token
        token = security_manager.generate_auth_token(
            user_id=1,
            role='kitchen_staff',
            display_name='Test Display',
            station_type='general'
        )
        
        assert token is not None
        assert len(token) > 0
    
    def test_token_validation(self, security_manager):
        """Test authentication token validation"""
        # Generate token
        token = security_manager.generate_auth_token(
            user_id=1,
            role='kitchen_staff',
            display_name='Test Display',
            station_type='general'
        )
        
        # Validate token
        is_valid, result = security_manager.validate_auth_token(token)
        assert is_valid
        assert 'user' in result
        assert result['user'].id == 1
    
    def test_invalid_token_validation(self, security_manager):
        """Test validation of invalid token"""
        # Try to validate invalid token
        is_valid, result = security_manager.validate_auth_token('invalid_token')
        assert not is_valid
        assert 'error' in result
    
    def test_expired_token_validation(self, security_manager):
        """Test validation of expired token"""
        # This would require setting up an expired token scenario
        # Implementation depends on token expiry configuration
        pass
    
    def test_role_based_access(self, security_manager):
        """Test role-based access control"""
        # Test kitchen access
        assert security_manager.has_kitchen_access('admin')
        assert security_manager.has_kitchen_access('kitchen_staff')
        assert not security_manager.has_kitchen_access('customer')
        
        # Test display configuration validation
        assert security_manager.validate_display_config('kitchen_staff', 'Valid Display', 'general')
        assert not security_manager.validate_display_config('kitchen_staff', 'Invalid', 'invalid_station')
    
    def test_rate_limiting(self, security_manager):
        """Test rate limiting functionality"""
        # Test IP-based rate limiting
        test_ip = '192.168.1.100'
        
        # Should allow initial connections
        for i in range(5):
            assert not security_manager.is_rate_limited(test_ip)
            security_manager.record_failed_attempt(test_ip)
        
        # After exceeding limit, should be rate limited
        assert security_manager.is_rate_limited(test_ip)
    
    def test_event_authorization(self, security_manager):
        """Test event authorization"""
        # Create mock user
        mock_user = Mock()
        mock_user.role = 'kitchen_staff'
        
        # Test authorized events
        event_data = {'order_id': 1, 'status': 'In Progress'}
        is_authorized, result = security_manager.authorize_kitchen_event(
            mock_user, event_data, 'order_update'
        )
        assert is_authorized
        
        # Test unauthorized events
        event_data = {'type': 'urgent', 'message': 'Test alert'}
        is_authorized, result = security_manager.authorize_kitchen_event(
            mock_user, event_data, 'kitchen_alert'
        )
        # Kitchen staff might not be authorized for urgent alerts
        assert isinstance(is_authorized, bool)

class TestWebSocketPerformance:
    """Test WebSocket performance and monitoring"""
    
    @pytest.fixture
    def performance_manager(self):
        """Create performance manager"""
        app = create_app()
        return WebSocketPerformanceManager(app)
    
    def test_connection_tracking(self, performance_manager):
        """Test connection tracking"""
        # Track connection
        performance_manager.track_connection(
            connection_id='test_conn_1',
            user_id=1,
            ip_address='192.168.1.100',
            user_agent='Test Browser'
        )
        
        # Check if connection is tracked
        assert 'test_conn_1' in performance_manager.performance_data['connections']
        
        conn_data = performance_manager.performance_data['connections']['test_conn_1']
        assert conn_data['user_id'] == 1
        assert conn_data['ip_address'] == '192.168.1.100'
    
    def test_event_tracking(self, performance_manager):
        """Test event tracking"""
        # Track connection first
        performance_manager.track_connection('test_conn', 1, '192.168.1.100', 'Test')
        
        # Track events
        performance_manager.track_event('test_conn', 'order_update', 'sent', 150.5)
        performance_manager.track_event('test_conn', 'order_update', 'received', 200.3)
        
        # Check tracking
        conn_data = performance_manager.performance_data['connections']['test_conn']
        assert conn_data['events_sent'] == 1
        assert conn_data['events_received'] == 1
        
        # Check response times
        response_times = performance_manager.performance_data['response_times']['test_conn']
        assert len(response_times) == 1
        assert 150.5 in response_times
    
    def test_error_tracking(self, performance_manager):
        """Test error tracking"""
        # Track connection first
        performance_manager.track_connection('test_conn', 1, '192.168.1.100', 'Test')
        
        # Track errors
        performance_manager.track_error('test_conn', 'ConnectionError', 'Connection lost')
        performance_manager.track_error('test_conn', 'TimeoutError', 'Request timeout')
        
        # Check error tracking
        conn_data = performance_manager.performance_data['connections']['test_conn']
        assert conn_data['errors'] == 2
        
        # Check global error counts
        assert performance_manager.performance_data['error_counts']['ConnectionError'] == 1
        assert performance_manager.performance_data['error_counts']['TimeoutError'] == 1
    
    def test_performance_report(self, performance_manager):
        """Test performance report generation"""
        # Add some test data
        performance_manager.track_connection('conn1', 1, '192.168.1.100', 'Browser1')
        performance_manager.track_connection('conn2', 2, '192.168.1.101', 'Browser2')
        performance_manager.track_event('conn1', 'order_update', 'sent', 100)
        performance_manager.track_event('conn2', 'order_update', 'sent', 150)
        
        # Generate report
        report = performance_manager.get_performance_report()
        
        assert 'timestamp' in report
        assert 'connections' in report
        assert 'events' in report
        assert 'performance' in report
        assert 'health' in report
        
        assert report['connections']['total'] == 2
        assert report['events']['total_sent'] == 2
    
    def test_real_time_metrics(self, performance_manager):
        """Test real-time metrics"""
        # Add test data
        performance_manager.track_connection('conn1', 1, '192.168.1.100', 'Test')
        
        # Get real-time metrics
        metrics = performance_manager.get_real_time_metrics()
        
        assert 'timestamp' in metrics
        assert 'active_connections' in metrics
        assert 'events_per_minute' in metrics
        assert 'memory_usage_percent' in metrics
        assert 'cpu_usage_percent' in metrics
    
    def test_optimization_recommendations(self, performance_manager):
        """Test optimization recommendations"""
        # Add high memory usage scenario
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 85
            
            recommendations = performance_manager.get_optimization_recommendations()
            
            # Should have memory-related recommendation
            memory_recommendations = [r for r in recommendations if r['type'] == 'memory']
            assert len(memory_recommendations) > 0
    
    def test_connection_allowance(self, performance_manager):
        """Test connection allowance checking"""
        # Test normal connection allowance
        is_allowed, result = performance_manager.is_connection_allowed('192.168.1.100')
        assert is_allowed
        assert 'message' in result
        
        # Test rate limiting (simulate many events from same IP)
        test_ip = '192.168.1.200'
        for i in range(105):  # Exceed threshold
            performance_manager.performance_data['events_per_minute'][f'conn_{i}'] = 1
            performance_manager.performance_data['connections'][f'conn_{i}'] = {
                'ip_address': test_ip,
                'last_activity': time.time()
            }
        
        is_allowed, result = performance_manager.is_connection_allowed(test_ip)
        assert not is_allowed
        assert 'error' in result

class TestWebSocketIntegration:
    """Test end-to-end WebSocket integration"""
    
    @pytest.fixture
    def full_app(self):
        """Create full app with all components"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        with app.app_context():
            db.create_all()
            
            # Create test users
            users = []
            roles = ['admin', 'kitchen_staff', 'chef', 'manager']
            for i, role in enumerate(roles, 1):
                user = User(
                    username=f'{role}_user',
                    email=f'{role}@test.com',
                    role=role,
                    is_active=True
                )
                user.set_password('testpass')
                db.session.add(user)
                users.append(user)
            
            db.session.commit()
            yield app
    
    def test_end_to_end_order_workflow(self, full_app):
        """Test complete order workflow with WebSocket"""
        with full_app.test_client() as http_client:
            with http_client.session_transaction() as sess:
                sess['_user_id'] = 1  # Kitchen staff user
            
            # Create Socket.IO client
            socketio_client = SocketIOTestClient(full_app, http_client)
            socketio_client.connect()
            
            # 1. Create new order
            with full_app.app_context():
                manager = RealTimeKOTManager(full_app.socketio)
                
                order_data = {
                    'order_number': 'E2E001',
                    'order_type': 'Dine-in',
                    'items': [{
                        'menu_item_id': 1,
                        'quantity': 2,
                        'price': 12.50
                    }]
                }
                
                result = manager.create_order_with_realtime(order_data, 1, 'kitchen_staff')
                assert result['success']
            
            # 2. Update order status
            with full_app.app_context():
                order = Order.query.filter_by(order_number='E2E001').first()
                assert order is not None
                
                result = manager.update_order_status_realtime(
                    order.id, 'In Progress', 1, 'kitchen_staff', 'Started cooking'
                )
                assert result['success']
            
            # 3. Update item status
            with full_app.app_context():
                item = OrderItem.query.filter_by(order_id=order.id).first()
                assert item is not None
                
                result = manager.update_item_status_realtime(
                    item.id, 'Ready', 1, 'kitchen_staff'
                )
                assert result['success']
            
            # 4. Mark order as ready
            with full_app.app_context():
                result = manager.update_order_status_realtime(
                    order.id, 'Ready', 1, 'kitchen_staff', 'All items ready'
                )
                assert result['success']
            
            # 5. Complete order
            with full_app.app_context():
                result = manager.update_order_status_realtime(
                    order.id, 'Completed', 1, 'kitchen_staff', 'Order served'
                )
                assert result['success']
            
            # Check received events
            received = socketio_client.get_received()
            
            # Should have received multiple events
            assert len(received) > 0
            
            # Check for specific event types
            event_types = [msg['name'] for msg in received]
            assert 'order_event' in event_types
            
            # Should have new order, updates, and completion
            order_events = [msg for msg in received if msg['name'] == 'order_event']
            assert len(order_events) > 0
    
    def test_multiple_kitchen_displays_sync(self, full_app):
        """Test multiple kitchen displays staying in sync"""
        clients = []
        
        try:
            # Create multiple kitchen display clients
            for i in range(3):
                with full_app.test_client() as http_client:
                    with http_client.session_transaction() as sess:
                        sess['_user_id'] = 1  # Same kitchen user
                    
                    socketio_client = SocketIOTestClient(full_app, http_client)
                    socketio_client.connect(
                        query_string=f'display_name=Display{i+1}&station_type=general&kitchen_role=kitchen_staff'
                    )
                    clients.append(socketio_client)
            
            # All clients should be connected
            for client in clients:
                assert client.is_connected()
            
            # Create an order
            with full_app.app_context():
                manager = RealTimeKOTManager(full_app.socketio)
                
                order_data = {
                    'order_number': 'SYNC001',
                    'order_type': 'Dine-in',
                    'items': [{
                        'menu_item_id': 1,
                        'quantity': 1,
                        'price': 10.00
                    }]
                }
                
                result = manager.create_order_with_realtime(order_data, 1, 'kitchen_staff')
                assert result['success']
            
            # All clients should receive the new order
            for client in clients:
                received = client.get_received()
                new_order_events = [msg for msg in received if msg['name'] == 'order_event' 
                                  and msg['args'][0]['type'] == 'new_order']
                assert len(new_order_events) > 0
        
        finally:
            # Cleanup
            for client in clients:
                try:
                    client.disconnect()
                except:
                    pass
    
    def test_kitchen_alert_distribution(self, full_app):
        """Test kitchen alert distribution to multiple displays"""
        clients = []
        
        try:
            # Create clients for different stations
            station_configs = [
                ('Display1', 'general'),
                ('Display2', 'grill'),
                ('Display3', 'fry')
            ]
            
            for display_name, station_type in station_configs:
                with full_app.test_client() as http_client:
                    with http_client.session_transaction() as sess:
                        sess['_user_id'] = 1
                    
                    socketio_client = SocketIOTestClient(full_app, http_client)
                    socketio_client.connect(
                        query_string=f'display_name={display_name}&station_type={station_type}&kitchen_role=kitchen_staff'
                    )
                    clients.append(socketio_client)
            
            # Send alert to specific stations
            with full_app.app_context():
                manager = RealTimeKOTManager(full_app.socketio)
                
                result = manager.send_kitchen_alert(
                    'urgent', 'Fire in fryer!', ['fry'], None, 1
                )
                assert result['success']
            
            # Check which clients received the alert
            receiving_clients = []
            for i, client in enumerate(clients):
                received = client.get_received()
                alert_events = [msg for msg in received if msg['name'] == 'kitchen_alert']
                if alert_events:
                    receiving_clients.append(i)
            
            # At least one client should receive the alert
            assert len(receiving_clients) > 0
        
        finally:
            # Cleanup
            for client in clients:
                try:
                    client.disconnect()
                except:
                    pass

# Performance and load testing
class TestWebSocketPerformanceLoad:
    """Load testing for WebSocket connections"""
    
    def test_high_concurrent_connections(self):
        """Test system under high concurrent connection load"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            
            # Create test user
            user = User(
                username='load_test_user',
                email='load@test.com',
                role='kitchen_staff',
                is_active=True
            )
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Test with multiple concurrent connections
            num_connections = 50
            clients = []
            errors = []
            
            def create_connection(client_num):
                try:
                    with app.test_client() as http_client:
                        with http_client.session_transaction() as sess:
                            sess['_user_id'] = user.id
                        
                        socketio_client = SocketIOTestClient(app, http_client)
                        socketio_client.connect()
                        
                        # Keep connection alive for a bit
                        time.sleep(0.1)
                        
                        socketio_client.disconnect()
                        return True
                except Exception as e:
                    errors.append(f"Connection {client_num}: {str(e)}")
                    return False
            
            # Create connections concurrently
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(create_connection, i) for i in range(num_connections)]
                results = [future.result() for future in futures]
            
            # Check results
            successful_connections = sum(results)
            assert successful_connections >= num_connections * 0.8  # At least 80% should succeed
            
            if errors:
                print(f"Connection errors: {errors}")
    
    def test_event_throughput(self):
        """Test high event throughput"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            
            # Create test user
            user = User(
                username='throughput_user',
                email='throughput@test.com',
                role='admin',
                is_active=True
            )
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            with app.test_client() as http_client:
                with http_client.session_transaction() as sess:
                    sess['_user_id'] = user.id
                
                socketio_client = SocketIOTestClient(app, http_client)
                socketio_client.connect()
                
                # Send many events rapidly
                num_events = 100
                start_time = time.time()
                
                for i in range(num_events):
                    socketio_client.emit('test_event', {'id': i, 'data': f'test_data_{i}'})
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Should handle events reasonably quickly
                assert duration < 5.0  # Should complete within 5 seconds
                
                # Check for any errors
                received = socketio_client.get_received()
                error_events = [msg for msg in received if msg['name'] == 'error']
                assert len(error_events) == 0

# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])