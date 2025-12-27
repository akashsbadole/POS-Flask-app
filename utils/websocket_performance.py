"""
WebSocket Performance Optimization and Monitoring
Handles performance optimization, monitoring, and scaling for WebSocket connections
"""

import time
import asyncio
from datetime import datetime, timedelta
from collections import deque, defaultdict
from flask import current_app
from models import db, RealTimeMetrics, Order, KitchenDisplay
import threading
import psutil
import gc
import json
from concurrent.futures import ThreadPoolExecutor
import queue

class WebSocketPerformanceManager:
    """Manages WebSocket performance optimization and monitoring"""
    
    def __init__(self, app=None):
        self.app = app
        self.performance_data = {
            'connections': defaultdict(dict),
            'events_per_minute': defaultdict(int),
            'memory_usage': [],
            'cpu_usage': [],
            'event_queue_sizes': defaultdict(int),
            'response_times': defaultdict(list),
            'error_counts': defaultdict(int),
            'throughput_stats': defaultdict(lambda: {'sent': 0, 'received': 0, 'timestamp': time.time()})
        }
        
        # Performance thresholds
        self.thresholds = {
            'max_connections_per_ip': 5,
            'max_events_per_minute': 100,
            'max_memory_usage_mb': 512,
            'max_response_time_ms': 500,
            'max_queue_size': 1000,
            'connection_timeout_minutes': 30
        }
        
        # Monitoring intervals (in seconds)
        self.monitoring_intervals = {
            'performance_check': 30,
            'cleanup_inactive': 60,
            'metrics_update': 30,
            'memory_cleanup': 300,
            'health_check': 15
        }
        
        # Thread pool for background tasks
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Performance optimization settings
        self.optimization_settings = {
            'enable_batching': True,
            'batch_size': 10,
            'batch_timeout_ms': 100,
            'enable_compression': True,
            'enable_caching': True,
            'cache_ttl_seconds': 30,
            'max_concurrent_processing': 10
        }
        
        # Initialize monitoring
        self.running = False
        self.monitor_thread = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
        # Get configuration from app config
        self.load_config()
        
        # Start monitoring
        self.start_monitoring()
    
    def load_config(self):
        """Load performance configuration from app config"""
        if hasattr(self.app, 'config'):
            config = self.app.config.get('WEBSOCKET_PERFORMANCE', {})
            
            # Update thresholds
            self.thresholds.update(config.get('thresholds', {}))
            
            # Update monitoring intervals
            self.monitoring_intervals.update(config.get('monitoring_intervals', {}))
            
            # Update optimization settings
            self.optimization_settings.update(config.get('optimization_settings', {}))
    
    def start_monitoring(self):
        """Start performance monitoring threads"""
        if self.running:
            return
        
        self.running = True
        
        # Start main monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        current_app.logger.info("WebSocket performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.executor.shutdown(wait=False)
        current_app.logger.info("WebSocket performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        last_cleanup = time.time()
        last_metrics_update = time.time()
        last_memory_cleanup = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                
                # Performance checks every 30 seconds
                if current_time - last_cleanup >= self.monitoring_intervals['performance_check']:
                    self._check_performance_health()
                    last_cleanup = current_time
                
                # Cleanup inactive connections every minute
                if current_time - last_cleanup >= self.monitoring_intervals['cleanup_inactive']:
                    self._cleanup_inactive_connections()
                    last_cleanup = current_time
                
                # Update metrics every 30 seconds
                if current_time - last_metrics_update >= self.monitoring_intervals['metrics_update']:
                    self._update_performance_metrics()
                    last_metrics_update = current_time
                
                # Memory cleanup every 5 minutes
                if current_time - last_memory_cleanup >= self.monitoring_intervals['memory_cleanup']:
                    self._perform_memory_cleanup()
                    last_memory_cleanup = current_time
                
                # Sleep for a short interval
                time.sleep(5)
                
            except Exception as e:
                current_app.logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(10)
    
    def _check_performance_health(self):
        """Check overall system health"""
        try:
            # Check memory usage
            memory_info = psutil.virtual_memory()
            memory_usage_mb = memory_info.used / (1024 * 1024)
            
            if memory_usage_mb > self.thresholds['max_memory_usage_mb']:
                self._trigger_memory_cleanup()
                current_app.logger.warning(f"High memory usage detected: {memory_usage_mb:.2f} MB")
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                current_app.logger.warning(f"High CPU usage detected: {cpu_percent}%")
            
            # Check connection count
            total_connections = len(self.performance_data['connections'])
            if total_connections > 100:  # Adjust based on server capacity
                current_app.logger.warning(f"High connection count: {total_connections}")
            
            # Store performance data
            self.performance_data['memory_usage'].append({
                'timestamp': time.time(),
                'usage_mb': memory_usage_mb,
                'usage_percent': memory_info.percent
            })
            
            self.performance_data['cpu_usage'].append({
                'timestamp': time.time(),
                'usage_percent': cpu_percent
            })
            
            # Keep only recent data (last hour)
            cutoff_time = time.time() - 3600
            for key in ['memory_usage', 'cpu_usage']:
                self.performance_data[key] = [
                    item for item in self.performance_data[key]
                    if item['timestamp'] > cutoff_time
                ]
            
        except Exception as e:
            current_app.logger.error(f"Error checking performance health: {str(e)}")
    
    def _cleanup_inactive_connections(self):
        """Clean up inactive WebSocket connections"""
        try:
            current_time = time.time()
            timeout_threshold = self.thresholds['connection_timeout_minutes'] * 60
            inactive_connections = []
            
            for connection_id, conn_data in self.performance_data['connections'].items():
                last_activity = conn_data.get('last_activity', current_time)
                if current_time - last_activity > timeout_threshold:
                    inactive_connections.append(connection_id)
            
            # Remove inactive connections
            for connection_id in inactive_connections:
                del self.performance_data['connections'][connection_id]
                
                # Clean up related data
                for key in ['events_per_minute', 'event_queue_sizes', 'response_times']:
                    if connection_id in self.performance_data[key]:
                        del self.performance_data[key][connection_id]
            
            if inactive_connections:
                current_app.logger.info(f"Cleaned up {len(inactive_connections)} inactive connections")
            
        except Exception as e:
            current_app.logger.error(f"Error cleaning up inactive connections: {str(e)}")
    
    def _update_performance_metrics(self):
        """Update performance metrics in database"""
        try:
            current_time = datetime.utcnow()
            
            # Get current system metrics
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            active_connections = len(self.performance_data['connections'])
            
            # Get order-related metrics
            active_orders = Order.query.filter(
                Order.status.in_(['New', 'In Progress', 'Ready'])
            ).count()
            
            # Calculate average event processing time
            avg_response_times = []
            for response_times in self.performance_data['response_times'].values():
                if response_times:
                    avg_response_times.extend(response_times[-10:])  # Last 10 responses per connection
            
            avg_response_time = sum(avg_response_times) / len(avg_response_times) if avg_response_times else 0
            
            # Store metrics in database
            metrics_data = [
                ('memory_usage_mb', memory_info.used / (1024 * 1024), 'MB'),
                ('memory_usage_percent', memory_info.percent, 'percent'),
                ('cpu_usage_percent', cpu_percent, 'percent'),
                ('active_connections', active_connections, 'count'),
                ('active_orders', active_orders, 'count'),
                ('avg_response_time_ms', avg_response_time, 'milliseconds'),
                ('total_events_per_minute', sum(self.performance_data['events_per_minute'].values()), 'count')
            ]
            
            for metric_name, metric_value, unit in metrics_data:
                metric = RealTimeMetrics(
                    metric_type='websocket_performance',
                    metric_name=metric_name,
                    metric_value=metric_value,
                    metric_unit=unit,
                    calculated_at=current_time,
                    data_source='performance_monitor'
                )
                db.session.add(metric)
            
            db.session.commit()
            
            # Reset event counters for next interval
            self.performance_data['events_per_minute'].clear()
            
        except Exception as e:
            current_app.logger.error(f"Error updating performance metrics: {str(e)}")
            db.session.rollback()
    
    def _perform_memory_cleanup(self):
        """Perform memory cleanup"""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Clear old performance data
            current_time = time.time()
            cutoff_time = current_time - 1800  # 30 minutes
            
            # Clean old response times
            for connection_id in list(self.performance_data['response_times'].keys()):
                response_times = self.performance_data['response_times'][connection_id]
                # Keep only recent response times (last 100 per connection)
                self.performance_data['response_times'][connection_id] = response_times[-100:]
            
            current_app.logger.info(f"Memory cleanup completed: {collected} objects collected")
            
        except Exception as e:
            current_app.logger.error(f"Error during memory cleanup: {str(e)}")
    
    def _trigger_memory_cleanup(self):
        """Trigger emergency memory cleanup"""
        try:
            # Clear non-essential caches
            if hasattr(self, '_response_cache'):
                self._response_cache.clear()
            
            # Force aggressive garbage collection
            collected = gc.collect(2)  # Full collection
            
            current_app.logger.info(f"Emergency memory cleanup completed: {collected} objects collected")
            
        except Exception as e:
            current_app.logger.error(f"Error during emergency memory cleanup: {str(e)}")
    
    def track_connection(self, connection_id, user_id, ip_address, user_agent):
        """Track new WebSocket connection"""
        try:
            self.performance_data['connections'][connection_id] = {
                'user_id': user_id,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'connected_at': time.time(),
                'last_activity': time.time(),
                'events_sent': 0,
                'events_received': 0,
                'errors': 0
            }
            
            current_app.logger.debug(f"Tracking connection: {connection_id}")
            
        except Exception as e:
            current_app.logger.error(f"Error tracking connection: {str(e)}")
    
    def track_event(self, connection_id, event_type, direction='sent', response_time=None):
        """Track WebSocket event for performance monitoring"""
        try:
            current_time = time.time()
            
            # Update connection data
            if connection_id in self.performance_data['connections']:
                conn_data = self.performance_data['connections'][connection_id]
                conn_data['last_activity'] = current_time
                
                if direction == 'sent':
                    conn_data['events_sent'] += 1
                else:
                    conn_data['events_received'] += 1
                
                if response_time:
                    if connection_id not in self.performance_data['response_times']:
                        self.performance_data['response_times'][connection_id] = []
                    self.performance_data['response_times'][connection_id].append(response_time)
                    
                    # Keep only recent response times
                    if len(self.performance_data['response_times'][connection_id]) > 100:
                        self.performance_data['response_times'][connection_id] = \
                            self.performance_data['response_times'][connection_id][-100:]
            
            # Update global event counters
            current_minute = int(current_time / 60)
            self.performance_data['events_per_minute'][connection_id] += 1
            
        except Exception as e:
            current_app.logger.error(f"Error tracking event: {str(e)}")
    
    def track_error(self, connection_id, error_type, error_message):
        """Track WebSocket errors"""
        try:
            if connection_id in self.performance_data['connections']:
                self.performance_data['connections'][connection_id]['errors'] += 1
                self.performance_data['connections'][connection_id]['last_error'] = {
                    'type': error_type,
                    'message': error_message,
                    'timestamp': time.time()
                }
            
            self.performance_data['error_counts'][error_type] += 1
            
        except Exception as e:
            current_app.logger.error(f"Error tracking WebSocket error: {str(e)}")
    
    def is_connection_allowed(self, ip_address):
        """Check if new connection is allowed based on performance metrics"""
        try:
            # Count connections from this IP
            ip_connections = sum(
                1 for conn_data in self.performance_data['connections'].values()
                if conn_data.get('ip_address') == ip_address
            )
            
            if ip_connections >= self.thresholds['max_connections_per_ip']:
                return False, {'error': 'Too many connections from this IP'}
            
            # Check if IP is generating too many events
            ip_events_per_minute = sum(
                self.performance_data['events_per_minute'].get(conn_id, 0)
                for conn_id, conn_data in self.performance_data['connections'].items()
                if conn_data.get('ip_address') == ip_address
            )
            
            if ip_events_per_minute > self.thresholds['max_events_per_minute']:
                return False, {'error': 'Too many events from this IP'}
            
            return True, {'message': 'Connection allowed'}
            
        except Exception as e:
            current_app.logger.error(f"Error checking connection allowance: {str(e)}")
            return True, {'message': 'Connection allowed (error in check)'}
    
    def optimize_event_batching(self, events, connection_id):
        """Optimize event sending with batching"""
        try:
            if not self.optimization_settings['enable_batching']:
                return events
            
            # Group events by type for batching
            batched_events = defaultdict(list)
            current_time = time.time()
            
            for event in events:
                event_type = event.get('type', 'unknown')
                batched_events[event_type].append(event)
            
            # Process batches
            optimized_events = []
            for event_type, event_batch in batched_events.items():
                if len(event_batch) > self.optimization_settings['batch_size']:
                    # Combine multiple events of the same type
                    combined_event = {
                        'type': f'{event_type}_batch',
                        'events': event_batch[:self.optimization_settings['batch_size']],
                        'batch_count': len(event_batch),
                        'timestamp': current_time
                    }
                    optimized_events.append(combined_event)
                    
                    # Add remaining events to next batch
                    remaining = event_batch[self.optimization_settings['batch_size']:]
                    if remaining:
                        optimized_events.extend(remaining)
                else:
                    optimized_events.extend(event_batch)
            
            return optimized_events
            
        except Exception as e:
            current_app.logger.error(f"Error optimizing event batching: {str(e)}")
            return events
    
    def get_performance_report(self):
        """Get comprehensive performance report"""
        try:
            current_time = time.time()
            
            # Calculate metrics
            total_connections = len(self.performance_data['connections'])
            total_events_sent = sum(
                conn_data.get('events_sent', 0) 
                for conn_data in self.performance_data['connections'].values()
            )
            total_events_received = sum(
                conn_data.get('events_received', 0) 
                for conn_data in self.performance_data['connections'].values()
            )
            total_errors = sum(
                conn_data.get('errors', 0) 
                for conn_data in self.performance_data['connections'].values()
            )
            
            # Calculate average response times
            all_response_times = []
            for response_times in self.performance_data['response_times'].values():
                all_response_times.extend(response_times[-10:])  # Last 10 per connection
            
            avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
            
            # Get system metrics
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            # Calculate error rate
            total_events = total_events_sent + total_events_received
            error_rate = (total_errors / total_events * 100) if total_events > 0 else 0
            
            # Get connection duration statistics
            connection_durations = []
            for conn_data in self.performance_data['connections'].values():
                duration = current_time - conn_data.get('connected_at', current_time)
                connection_durations.append(duration)
            
            avg_connection_duration = sum(connection_durations) / len(connection_durations) if connection_durations else 0
            
            return {
                'timestamp': current_time,
                'connections': {
                    'total': total_connections,
                    'active': len([c for c in self.performance_data['connections'].values() 
                                 if current_time - c.get('last_activity', current_time) < 300]),  # 5 minutes
                    'avg_duration_minutes': avg_connection_duration / 60
                },
                'events': {
                    'total_sent': total_events_sent,
                    'total_received': total_events_received,
                    'total': total_events,
                    'error_rate_percent': error_rate
                },
                'performance': {
                    'avg_response_time_ms': avg_response_time,
                    'memory_usage_mb': memory_info.used / (1024 * 1024),
                    'memory_usage_percent': memory_info.percent,
                    'cpu_usage_percent': cpu_percent
                },
                'health': {
                    'memory_status': 'good' if memory_info.percent < 80 else 'warning' if memory_info.percent < 90 else 'critical',
                    'cpu_status': 'good' if cpu_percent < 70 else 'warning' if cpu_percent < 90 else 'critical',
                    'connection_status': 'good' if total_connections < 50 else 'warning' if total_connections < 100 else 'critical',
                    'error_rate_status': 'good' if error_rate < 1 else 'warning' if error_rate < 5 else 'critical'
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error generating performance report: {str(e)}")
            return {'error': str(e)}
    
    def get_connection_stats(self, connection_id):
        """Get statistics for specific connection"""
        try:
            if connection_id not in self.performance_data['connections']:
                return None
            
            conn_data = self.performance_data['connections'][connection_id]
            current_time = time.time()
            
            # Calculate connection duration
            duration = current_time - conn_data.get('connected_at', current_time)
            
            # Get recent response times
            response_times = self.performance_data['response_times'].get(connection_id, [])
            recent_response_times = response_times[-20:]  # Last 20 responses
            avg_response_time = sum(recent_response_times) / len(recent_response_times) if recent_response_times else 0
            
            return {
                'connection_id': connection_id,
                'user_id': conn_data.get('user_id'),
                'ip_address': conn_data.get('ip_address'),
                'connected_at': conn_data.get('connected_at'),
                'last_activity': conn_data.get('last_activity'),
                'duration_minutes': duration / 60,
                'events_sent': conn_data.get('events_sent', 0),
                'events_received': conn_data.get('events_received', 0),
                'errors': conn_data.get('errors', 0),
                'avg_response_time_ms': avg_response_time,
                'recent_response_times': recent_response_times[-10:]  # Last 10 for display
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting connection stats: {str(e)}")
            return None
    
    def get_real_time_metrics(self):
        """Get real-time performance metrics"""
        try:
            current_time = time.time()
            
            # Current active connections
            active_connections = len([c for c in self.performance_data['connections'].values() 
                                    if current_time - c.get('last_activity', current_time) < 300])
            
            # Events in last minute
            events_last_minute = sum(self.performance_data['events_per_minute'].values())
            
            # Current system load
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            # Recent error rate
            recent_errors = sum(self.performance_data['error_counts'].values())
            
            return {
                'timestamp': current_time,
                'active_connections': active_connections,
                'events_per_minute': events_last_minute,
                'memory_usage_percent': memory_info.percent,
                'cpu_usage_percent': cpu_percent,
                'recent_errors': recent_errors,
                'system_status': 'healthy' if cpu_percent < 70 and memory_info.percent < 80 else 'stressed'
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting real-time metrics: {str(e)}")
            return {'error': str(e)}
    
    def cleanup_connection(self, connection_id):
        """Clean up connection data"""
        try:
            # Remove from performance tracking
            if connection_id in self.performance_data['connections']:
                del self.performance_data['connections'][connection_id]
            
            # Clean up related data
            for key in ['events_per_minute', 'event_queue_sizes', 'response_times']:
                if connection_id in self.performance_data[key]:
                    del self.performance_data[key][connection_id]
            
            current_app.logger.debug(f"Cleaned up connection data: {connection_id}")
            
        except Exception as e:
            current_app.logger.error(f"Error cleaning up connection: {str(e)}")
    
    def get_optimization_recommendations(self):
        """Get performance optimization recommendations"""
        try:
            recommendations = []
            current_time = time.time()
            
            # Memory usage recommendations
            memory_info = psutil.virtual_memory()
            if memory_info.percent > 80:
                recommendations.append({
                    'type': 'memory',
                    'severity': 'high',
                    'message': 'High memory usage detected. Consider enabling aggressive caching or increasing server memory.',
                    'action': 'enable_memory_optimization'
                })
            
            # CPU usage recommendations
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 70:
                recommendations.append({
                    'type': 'cpu',
                    'severity': 'medium',
                    'message': 'High CPU usage detected. Consider optimizing event processing or scaling horizontally.',
                    'action': 'enable_cpu_optimization'
                })
            
            # Connection count recommendations
            total_connections = len(self.performance_data['connections'])
            if total_connections > 50:
                recommendations.append({
                    'type': 'connections',
                    'severity': 'medium',
                    'message': 'High number of active connections. Consider connection pooling or load balancing.',
                    'action': 'enable_connection_optimization'
                })
            
            # Response time recommendations
            all_response_times = []
            for response_times in self.performance_data['response_times'].values():
                all_response_times.extend(response_times[-10:])
            
            avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
            if avg_response_time > 200:  # 200ms threshold
                recommendations.append({
                    'type': 'response_time',
                    'severity': 'medium',
                    'message': f'Slow response times detected (avg: {avg_response_time:.1f}ms). Consider event batching or caching.',
                    'action': 'enable_response_time_optimization'
                })
            
            # Event rate recommendations
            events_per_minute = sum(self.performance_data['events_per_minute'].values())
            if events_per_minute > 1000:
                recommendations.append({
                    'type': 'throughput',
                    'severity': 'low',
                    'message': 'High event throughput. Consider implementing event prioritization.',
                    'action': 'enable_throughput_optimization'
                })
            
            return recommendations
            
        except Exception as e:
            current_app.logger.error(f"Error getting optimization recommendations: {str(e)}")
            return []

# Global performance manager instance
websocket_performance = WebSocketPerformanceManager()

def get_websocket_performance():
    """Get the global WebSocket performance manager"""
    return websocket_performance

# Performance monitoring decorators
def monitor_websocket_event(event_type_param='event_type'):
    """Decorator to monitor WebSocket event performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            connection_id = kwargs.get('connection_id', 'unknown')
            
            try:
                result = func(*args, **kwargs)
                
                # Track successful event
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                performance_manager = get_websocket_performance()
                performance_manager.track_event(connection_id, event_type_param, 'processed', response_time)
                
                return result
                
            except Exception as e:
                # Track error
                performance_manager = get_websocket_performance()
                performance_manager.track_error(connection_id, type(e).__name__, str(e))
                raise
                
        return wrapper
    return decorator

# Utility functions for performance optimization
def optimize_websocket_config(app):
    """Optimize WebSocket configuration for production"""
    # Set optimal Socket.IO settings
    app.config['SOCKETIO_ASYNC_MODE'] = 'eventlet'
    app.config['SOCKETIO_PING_TIMEOUT'] = 60
    app.config['SOCKETIO_PING_INTERVAL'] = 25
    app.config['SOCKETIO_MESSAGE_QUEUE'] = None  # Use direct connection for better performance
    app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'] = "*"
    
    # Enable compression for Socket.IO
    app.config['SOCKETIO_COMPRESSION'] = 'deflate'
    
    return app

def get_performance_dashboard_data():
    """Get data for performance dashboard"""
    performance_manager = get_websocket_performance()
    
    return {
        'real_time_metrics': performance_manager.get_real_time_metrics(),
        'performance_report': performance_manager.get_performance_report(),
        'optimization_recommendations': performance_manager.get_optimization_recommendations(),
        'system_health': performance_manager._check_performance_health()
    }