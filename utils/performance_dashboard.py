"""
Performance Monitoring Dashboard for Flask Web POS Application
Real-time performance monitoring and reporting
"""

import threading
import time
import json
import psutil
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from collections import deque
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import os

from web_cloud.config.performance_config import PerformanceConfig
from web_cloud.models.optimized_database import DatabasePerformanceManager

class MetricType(Enum):
    """Performance metric types"""
    CPU = "cpu"
    MEMORY = "memory"
    DATABASE = "database"
    CACHE = "cache"
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    timestamp: float
    metric_type: MetricType
    value: float
    unit: str
    tags: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'metric_type': self.metric_type.value,
            'value': self.value,
            'unit': self.unit,
            'tags': self.tags
        }

@dataclass
class SystemResource:
    """System resource information"""
    cpu_percent: float
    memory_percent: float
    memory_used: float
    memory_total: float
    disk_percent: float
    disk_used: float
    disk_total: float
    network_sent: float
    network_received: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used': self.memory_used,
            'memory_total': self.memory_total,
            'disk_percent': self.disk_percent,
            'disk_used': self.disk_used,
            'disk_total': self.disk_total,
            'network_sent': self.network_sent,
            'network_received': self.network_received,
            'timestamp': self.timestamp
        }

class PerformanceMonitor:
    """Performance monitoring system"""
    
    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Metrics storage
        self.metrics = {
            MetricType.CPU: deque(maxlen=1000),
            MetricType.MEMORY: deque(maxlen=1000),
            MetricType.DATABASE: deque(maxlen=1000),
            MetricType.CACHE: deque(maxlen=1000),
            MetricType.RESPONSE_TIME: deque(maxlen=1000),
            MetricType.THROUGHPUT: deque(maxlen=1000),
            MetricType.ERROR_RATE: deque(maxlen=1000)
        }
        
        # System resources
        self.system_resources = deque(maxlen=100)
        
        # Performance thresholds
        self.thresholds = {
            MetricType.CPU: 80.0,
            MetricType.MEMORY: 85.0,
            MetricType.DATABASE: 100.0,  # ms
            MetricType.RESPONSE_TIME: 500.0,  # ms
            MetricType.ERROR_RATE: 5.0  # percentage
        }
        
        # Alert callbacks
        self.alert_callbacks = []
        
        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_lock = threading.RLock()
        
        # Database performance manager
        self.db_perf_manager = DatabasePerformanceManager()
        
        # Cache performance tracker
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Response time tracker
        self.response_times = deque(maxlen=100)
        
        # Error tracking
        self.error_count = 0
        self.total_requests = 0
        
        # Initialize monitoring
        self._initialize_monitoring()
    
    def _initialize_monitoring(self):
        """Initialize monitoring system"""
        # Start monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Performance monitoring initialized")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Collect database metrics
                self._collect_database_metrics()
                
                # Collect cache metrics
                self._collect_cache_metrics()
                
                # Check thresholds
                self._check_thresholds()
                
                # Sleep for configured interval
                time.sleep(self.config.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Create system resource record
            resource = SystemResource(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used=memory.used,
                memory_total=memory.total,
                disk_percent=disk.percent,
                disk_used=disk.used,
                disk_total=disk.total,
                network_sent=network.bytes_sent,
                network_received=network.bytes_recv,
                timestamp=time.time()
            )
            
            # Add to resources
            self.system_resources.append(resource)
            
            # Add individual metrics
            self.add_metric(MetricType.CPU, cpu_percent, "%", {"source": "system"})
            self.add_metric(MetricType.MEMORY, memory.percent, "%", {"source": "system"})
            
            # Calculate network throughput
            if len(self.system_resources) > 1:
                prev_resource = self.system_resources[-2]
                current_time = resource.timestamp
                prev_time = prev_resource.timestamp
                
                if current_time > prev_time:
                    time_diff = current_time - prev_time
                    network_sent = (resource.network_sent - prev_resource.network_sent) / time_diff
                    network_received = (resource.network_received - prev_resource.network_received) / time_diff
                    
                    self.add_metric(MetricType.THROUGHPUT, network_sent, "bytes/s", {"type": "network_sent"})
                    self.add_metric(MetricType.THROUGHPUT, network_received, "bytes/s", {"type": "network_received"})
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    def _collect_database_metrics(self):
        """Collect database performance metrics"""
        try:
            # Get database metrics from performance manager
            db_stats = self.db_perf_manager.get_performance_stats()
            
            # Add database metrics
            self.add_metric(MetricType.DATABASE, db_stats.get('avg_query_time', 0), "ms", {"source": "database"})
            self.add_metric(MetricType.DATABASE, db_stats.get('connection_pool_size', 0), "connections", {"type": "pool_size"})
            self.add_metric(MetricType.DATABASE, db_stats.get('active_connections', 0), "connections", {"type": "active"})
            
        except Exception as e:
            self.logger.error(f"Error collecting database metrics: {e}")
    
    def _collect_cache_metrics(self):
        """Collect cache performance metrics"""
        try:
            # Calculate cache hit rate
            total_requests = self.cache_hits + self.cache_misses
            if total_requests > 0:
                hit_rate = (self.cache_hits / total_requests) * 100
                self.add_metric(MetricType.CACHE, hit_rate, "%", {"type": "hit_rate"})
            
            # Add cache size metrics
            # This would be implemented based on your cache system
            
        except Exception as e:
            self.logger.error(f"Error collecting cache metrics: {e}")
    
    def _check_thresholds(self):
        """Check performance thresholds and trigger alerts"""
        for metric_type, threshold in self.thresholds.items():
            if metric_type in self.metrics:
                recent_metrics = list(self.metrics[metric_type])[-10:]  # Last 10 measurements
                
                for metric in recent_metrics:
                    if metric.value > threshold:
                        self._trigger_alert(metric_type, metric.value, threshold)
    
    def _trigger_alert(self, metric_type: MetricType, value: float, threshold: float):
        """Trigger performance alert"""
        alert = {
            'metric_type': metric_type.value,
            'value': value,
            'threshold': threshold,
            'timestamp': time.time(),
            'message': f"{metric_type.value} performance threshold exceeded: {value} > {threshold}"
        }
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback error: {e}")
        
        self.logger.warning(f"Performance alert: {alert['message']}")
    
    def add_metric(self, metric_type: MetricType, value: float, unit: str, tags: Dict[str, str] = None):
        """Add performance metric"""
        if tags is None:
            tags = {}
        
        metric = PerformanceMetric(
            timestamp=time.time(),
            metric_type=metric_type,
            value=value,
            unit=unit,
            tags=tags
        )
        
        self.metrics[metric_type].append(metric)
    
    def record_response_time(self, response_time: float):
        """Record response time"""
        self.response_times.append(response_time)
        self.add_metric(MetricType.RESPONSE_TIME, response_time, "ms")
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.cache_misses += 1
    
    def record_error(self):
        """Record error"""
        self.error_count += 1
        self.total_requests += 1
        
        # Calculate error rate
        error_rate = (self.error_count / self.total_requests) * 100
        self.add_metric(MetricType.ERROR_RATE, error_rate, "%")
    
    def record_request(self):
        """Record successful request"""
        self.total_requests += 1
    
    def get_metrics_summary(self, metric_type: MetricType, hours: int = 1) -> Dict[str, Any]:
        """Get metrics summary for specified time period"""
        cutoff_time = time.time() - (hours * 3600)
        
        metrics = [m for m in self.metrics[metric_type] if m.timestamp >= cutoff_time]
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'metric_type': metric_type.value,
            'count': len(metrics),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1],
            'timestamp': time.time()
        }
    
    def get_system_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get system resource summary"""
        cutoff_time = time.time() - (hours * 3600)
        
        resources = [r for r in self.system_resources if r.timestamp >= cutoff_time]
        
        if not resources:
            return {}
        
        return {
            'cpu': {
                'avg': sum(r.cpu_percent for r in resources) / len(resources),
                'max': max(r.cpu_percent for r in resources),
                'min': min(r.cpu_percent for r in resources)
            },
            'memory': {
                'avg': sum(r.memory_percent for r in resources) / len(resources),
                'max': max(r.memory_percent for r in resources),
                'min': min(r.memory_percent for r in resources)
            },
            'disk': {
                'avg': sum(r.disk_percent for r in resources) / len(resources),
                'max': max(r.disk_percent for r in resources),
                'min': min(r.disk_percent for r in resources)
            },
            'timestamp': time.time()
        }
    
    def get_database_summary(self) -> Dict[str, Any]:
        """Get database performance summary"""
        return self.db_perf_manager.get_performance_stats()
    
    def get_cache_summary(self) -> Dict[str, Any]:
        """Get cache performance summary"""
        total_requests = self.cache_hits + self.cache_misses
        
        return {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_rate': (self.cache_hits / total_requests * 100) if total_requests > 0 else 0,
            'total_requests': total_requests,
            'timestamp': time.time()
        }
    
    def get_response_time_summary(self) -> Dict[str, Any]:
        """Get response time summary"""
        if not self.response_times:
            return {}
        
        return {
            'count': len(self.response_times),
            'min': min(self.response_times),
            'max': max(self.response_times),
            'avg': sum(self.response_times) / len(self.response_times),
            'latest': self.response_times[-1],
            'timestamp': time.time()
        }
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary"""
        if self.total_requests == 0:
            return {}
        
        return {
            'total_errors': self.error_count,
            'total_requests': self.total_requests,
            'error_rate': (self.error_count / self.total_requests) * 100,
            'timestamp': time.time()
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        return {
            'timestamp': time.time(),
            'system': self.get_system_summary(),
            'database': self.get_database_summary(),
            'cache': self.get_cache_summary(),
            'response_time': self.get_response_time_summary(),
            'errors': self.get_error_summary(),
            'metrics': {
                'cpu': self.get_metrics_summary(MetricType.CPU),
                'memory': self.get_metrics_summary(MetricType.MEMORY),
                'database': self.get_metrics_summary(MetricType.DATABASE),
                'cache': self.get_metrics_summary(MetricType.CACHE),
                'response_time': self.get_metrics_summary(MetricType.RESPONSE_TIME),
                'throughput': self.get_metrics_summary(MetricType.THROUGHPUT),
                'error_rate': self.get_metrics_summary(MetricType.ERROR_RATE)
            }
        }
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback"""
        self.alert_callbacks.append(callback)
    
    def export_metrics(self, filename: str, hours: int = 24):
        """Export metrics to file"""
        try:
            data = {
                'export_timestamp': time.time(),
                'time_range_hours': hours,
                'metrics': {},
                'system_resources': []
            }
            
            # Export metrics
            for metric_type in MetricType:
                data['metrics'][metric_type.value] = [
                    metric.to_dict() for metric in self.metrics[metric_type]
                    if metric.timestamp >= (time.time() - (hours * 3600))
                ]
            
            # Export system resources
            data['system_resources'] = [
                resource.to_dict() for resource in self.system_resources
                if resource.timestamp >= (time.time() - (hours * 3600))
            ]
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Metrics exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error exporting metrics: {e}")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("Performance monitoring stopped")

class PerformanceDashboard:
    """Performance dashboard web interface"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.logger = logging.getLogger(__name__)
        
        # Dashboard state
        self.dashboard_data = {}
        self.last_update = 0
        self.update_interval = 5  # seconds
        
        # Web routes
        self.routes = {
            '/dashboard': self.dashboard_view,
            '/dashboard/api/metrics': self.api_metrics,
            '/dashboard/api/system': self.api_system,
            '/dashboard/api/database': self.api_database,
            '/dashboard/api/cache': self.api_cache,
            '/dashboard/api/export': self.api_export
        }
    
    def dashboard_view(self):
        """Render dashboard view"""
        return self.render_dashboard_template()
    
    def api_metrics(self):
        """Get metrics API endpoint"""
        return self._json_response(self.monitor.get_dashboard_data())
    
    def api_system(self):
        """Get system metrics API endpoint"""
        return self._json_response(self.monitor.get_system_summary())
    
    def api_database(self):
        """Get database metrics API endpoint"""
        return self._json_response(self.monitor.get_database_summary())
    
    def api_cache(self):
        """Get cache metrics API endpoint"""
        return self._json_response(self.monitor.get_cache_summary())
    
    def api_export(self):
        """Export metrics API endpoint"""
        hours = int(self.monitor.config.monitoring_interval * 24)  # Default to 24 hours
        filename = f"performance_export_{int(time.time())}.json"
        
        self.monitor.export_metrics(filename, hours)
        
        return self._json_response({
            'status': 'success',
            'filename': filename,
            'timestamp': time.time()
        })
    
    def render_dashboard_template(self):
        """Render dashboard template"""
        # This would render an actual HTML template in a real implementation
        # For now, we'll return JSON data
        return self._json_response(self.monitor.get_dashboard_data())
    
    def _json_response(self, data: Dict[str, Any]):
        """Create JSON response"""
        return {
            'headers': {'Content-Type': 'application/json'},
            'data': data
        }
    
    def register_routes(self, app):
        """Register dashboard routes with Flask app"""
        for route, handler in self.routes.items():
            app.add_url_rule(route, view_func=handler)

# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        config = PerformanceConfig()
        _performance_monitor = PerformanceMonitor(config)
    return _performance_monitor