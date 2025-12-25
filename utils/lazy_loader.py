"""
Lazy Loading System for Flask Web POS Application
Implements lazy loading for images, resources, and data
"""

import threading
import time
import hashlib
import os
from typing import Dict, List, Any, Optional, Callable, Union
from urllib.parse import urljoin
from dataclasses import dataclass
from enum import Enum
import logging
from functools import wraps
import requests
from PIL import Image
import io
import base64

from web_cloud.config.performance_config import PerformanceConfig

class ResourceType(Enum):
    """Resource types for lazy loading"""
    IMAGE = "image"
    CSS = "css"
    JS = "js"
    DATA = "data"
    FONT = "font"

@dataclass
class ResourceInfo:
    """Resource information"""
    url: str
    resource_type: ResourceType
    size: int
    mime_type: str
    last_modified: float
    etag: str
    cache_key: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'url': self.url,
            'resource_type': self.resource_type.value,
            'size': self.size,
            'mime_type': self.mime_type,
            'last_modified': self.last_modified,
            'etag': self.etag,
            'cache_key': self.cache_key
        }

class LazyResourceLoader:
    """Lazy resource loader"""
    
    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Resource cache
        self.resource_cache = {}
        self.resource_cache_lock = threading.RLock()
        
        # Loading state
        self.loading_resources = {}
        self.loading_lock = threading.RLock()
        
        # Loading callbacks
        self.load_start_callbacks = []
        self.load_complete_callbacks = []
        self.load_error_callbacks = []
        
        # Resource prioritization
        self.priority_queue = []
        self.priority_lock = threading.RLock()
        
        # Background loading thread
        self.background_thread = None
        self.background_loading = True
        
        # Initialize
        self._initialize_loader()
    
    def _initialize_loader(self):
        """Initialize lazy loader"""
        # Start background loading thread
        self.background_thread = threading.Thread(target=self._background_loading_loop, daemon=True)
        self.background_thread.start()
        
        self.logger.info("Lazy resource loader initialized")
    
    def _background_loading_loop(self):
        """Background loading loop"""
        while self.background_loading:
            try:
                # Get next priority resource
                resource = self._get_next_priority_resource()
                
                if resource:
                    # Load resource
                    self._load_resource_background(resource)
                
                # Sleep briefly
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Background loading error: {e}")
                time.sleep(1)
    
    def _get_next_priority_resource(self) -> Optional[str]:
        """Get next priority resource"""
        with self.priority_lock:
            if self.priority_queue:
                return self.priority_queue.pop(0)
            return None
    
    def _load_resource_background(self, resource_url: str):
        """Load resource in background"""
        try:
            # Load resource
            resource_info = self._load_resource(resource_url)
            
            # Store in cache
            with self.resource_cache_lock:
                self.resource_cache[resource_url] = resource_info
            
            # Trigger callback
            self._trigger_load_complete(resource_url, resource_info)
            
        except Exception as e:
            self.logger.error(f"Background loading failed for {resource_url}: {e}")
            self._trigger_load_error(resource_url, str(e))
    
    def _generate_cache_key(self, url: str, resource_type: ResourceType) -> str:
        """Generate cache key"""
        key = f"{url}_{resource_type.value}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_resource_info(self, url: str) -> Optional[ResourceInfo]:
        """Get resource information from cache"""
        with self.resource_cache_lock:
            return self.resource_cache.get(url)
    
    def _load_resource(self, url: str, resource_type: ResourceType = None) -> ResourceInfo:
        """Load resource"""
        try:
            # Determine resource type if not provided
            if resource_type is None:
                resource_type = self._detect_resource_type(url)
            
            # Check cache first
            cached_info = self._get_resource_info(url)
            if cached_info:
                return cached_info
            
            # Load resource based on type
            if resource_type == ResourceType.IMAGE:
                return self._load_image(url)
            elif resource_type == ResourceType.CSS:
                return self._load_css(url)
            elif resource_type == ResourceType.JS:
                return self._load_js(url)
            elif resource_type == ResourceType.DATA:
                return self._load_data(url)
            elif resource_type == ResourceType.FONT:
                return self._load_font(url)
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to load resource {url}: {e}")
            raise
    
    def _detect_resource_type(self, url: str) -> ResourceType:
        """Detect resource type from URL"""
        url_lower = url.lower()
        
        if url_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
            return ResourceType.IMAGE
        elif url_lower.endswith('.css'):
            return ResourceType.CSS
        elif url_lower.endswith('.js'):
            return ResourceType.JS
        elif url_lower.endswith(('.woff', '.woff2', '.ttf', '.otf')):
            return ResourceType.FONT
        else:
            return ResourceType.DATA
    
    def _load_image(self, url: str) -> ResourceInfo:
        """Load image resource"""
        try:
            # Download image
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Get image info
            image_data = response.content
            size = len(image_data)
            
            # Get image dimensions
            try:
                img = Image.open(io.BytesIO(image_data))
                width, height = img.size
            except:
                width, height = 0, 0
            
            # Create cache key
            cache_key = self._generate_cache_key(url, ResourceType.IMAGE)
            
            # Create resource info
            resource_info = ResourceInfo(
                url=url,
                resource_type=ResourceType.IMAGE,
                size=size,
                mime_type=response.headers.get('content-type', 'image/jpeg'),
                last_modified=time.time(),
                etag=response.headers.get('etag', ''),
                cache_key=cache_key
            )
            
            # Optimize image if configured
            if self.config.enable_image_optimization:
                image_data = self._optimize_image(image_data, resource_info.mime_type)
            
            # Store optimized data
            resource_info.optimized_data = image_data
            resource_info.dimensions = (width, height)
            
            return resource_info
            
        except Exception as e:
            self.logger.error(f"Failed to load image {url}: {e}")
            raise
    
    def _load_css(self, url: str) -> ResourceInfo:
        """Load CSS resource"""
        try:
            # Download CSS
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Minify CSS if configured
            css_content = response.text
            if self.config.enable_css_optimization:
                css_content = self._minify_css(css_content)
            
            # Get size
            size = len(css_content.encode('utf-8'))
            
            # Create cache key
            cache_key = self._generate_cache_key(url, ResourceType.CSS)
            
            # Create resource info
            resource_info = ResourceInfo(
                url=url,
                resource_type=ResourceType.CSS,
                size=size,
                mime_type='text/css',
                last_modified=time.time(),
                etag=response.headers.get('etag', ''),
                cache_key=cache_key
            )
            
            # Store optimized data
            resource_info.optimized_data = css_content
            
            return resource_info
            
        except Exception as e:
            self.logger.error(f"Failed to load CSS {url}: {e}")
            raise
    
    def _load_js(self, url: str) -> ResourceInfo:
        """Load JavaScript resource"""
        try:
            # Download JavaScript
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Minify JS if configured
            js_content = response.text
            if self.config.enable_js_optimization:
                js_content = self._minify_js(js_content)
            
            # Get size
            size = len(js_content.encode('utf-8'))
            
            # Create cache key
            cache_key = self._generate_cache_key(url, ResourceType.JS)
            
            # Create resource info
            resource_info = ResourceInfo(
                url=url,
                resource_type=ResourceType.JS,
                size=size,
                mime_type='application/javascript',
                last_modified=time.time(),
                etag=response.headers.get('etag', ''),
                cache_key=cache_key
            )
            
            # Store optimized data
            resource_info.optimized_data = js_content
            
            return resource_info
            
        except Exception as e:
            self.logger.error(f"Failed to load JavaScript {url}: {e}")
            raise
    
    def _load_data(self, url: str) -> ResourceInfo:
        """Load data resource"""
        try:
            # Download data
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Get size
            size = len(response.content)
            
            # Create cache key
            cache_key = self._generate_cache_key(url, ResourceType.DATA)
            
            # Create resource info
            resource_info = ResourceInfo(
                url=url,
                resource_type=ResourceType.DATA,
                size=size,
                mime_type=response.headers.get('content-type', 'application/json'),
                last_modified=time.time(),
                etag=response.headers.get('etag', ''),
                cache_key=cache_key
            )
            
            # Store data
            resource_info.optimized_data = response.content
            
            return resource_info
            
        except Exception as e:
            self.logger.error(f"Failed to load data {url}: {e}")
            raise
    
    def _load_font(self, url: str) -> ResourceInfo:
        """Load font resource"""
        try:
            # Download font
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Get size
            size = len(response.content)
            
            # Create cache key
            cache_key = self._generate_cache_key(url, ResourceType.FONT)
            
            # Create resource info
            resource_info = ResourceInfo(
                url=url,
                resource_type=ResourceType.FONT,
                size=size,
                mime_type=response.headers.get('content-type', 'font/woff2'),
                last_modified=time.time(),
                etag=response.headers.get('etag', ''),
                cache_key=cache_key
            )
            
            # Store data
            resource_info.optimized_data = response.content
            
            return resource_info
            
        except Exception as e:
            self.logger.error(f"Failed to load font {url}: {e}")
            raise
    
    def _optimize_image(self, image_data: bytes, mime_type: str) -> bytes:
        """Optimize image data"""
        try:
            # Open image
            img = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Calculate quality based on file size
            max_size = 1024 * 1024  # 1MB
            if len(image_data) > max_size:
                quality = 85
            else:
                quality = 95
            
            # Optimize
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Failed to optimize image: {e}")
            return image_data
    
    def _minify_css(self, css_content: str) -> str:
        """Minify CSS content"""
        try:
            # Remove comments
            css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
            
            # Remove whitespace
            css_content = re.sub(r'\s+', ' ', css_content)
            
            # Remove unnecessary spaces around special characters
            css_content = re.sub(r'\s*([{};:,])\s*', r'\1', css_content)
            
            return css_content.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to minify CSS: {e}")
            return css_content
    
    def _minify_js(self, js_content: str) -> str:
        """Minify JavaScript content"""
        try:
            # Remove comments
            js_content = re.sub(r'//.*?$|/\*.*?\*/', '', js_content, flags=re.DOTALL | re.MULTILINE)
            
            # Remove whitespace
            js_content = re.sub(r'\s+', ' ', js_content)
            
            # Remove unnecessary spaces
            js_content = re.sub(r'\s*([{}();,=<>!&|?:.+-])\s*', r'\1', js_content)
            
            return js_content.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to minify JavaScript: {e}")
            return js_content
    
    def load_resource(self, url: str, resource_type: ResourceType = None, priority: int = 0) -> ResourceInfo:
        """Load resource with lazy loading"""
        try:
            # Check cache first
            cached_info = self._get_resource_info(url)
            if cached_info:
                return cached_info
            
            # Add to priority queue if background loading is enabled
            if self.background_loading:
                with self.priority_lock:
                    self.priority_queue.append((priority, url))
                    self.priority_queue.sort(key=lambda x: x[0])  # Sort by priority
                return None
            
            # Load synchronously
            return self._load_resource(url, resource_type)
            
        except Exception as e:
            self.logger.error(f"Failed to load resource {url}: {e}")
            raise
    
    def preload_resource(self, url: str, resource_type: ResourceType = None, priority: int = 0):
        """Preload resource in background"""
        try:
            with self.priority_lock:
                self.priority_queue.append((priority, url))
                self.priority_queue.sort(key=lambda x: x[0])  # Sort by priority
                
        except Exception as e:
            self.logger.error(f"Failed to preload resource {url}: {e}")
    
    def get_resource_url(self, url: str, resource_type: ResourceType = None) -> str:
        """Get resource URL with lazy loading support"""
        try:
            # Check if resource is cached
            cached_info = self._get_resource_info(url)
            
            if cached_info:
                # Return data URL for cached resources
                if hasattr(cached_info, 'optimized_data'):
                    if resource_type == ResourceType.IMAGE:
                        return self._data_url(cached_info.optimized_data, cached_info.mime_type)
                    else:
                        return f"data:{cached_info.mime_type};base64,{base64.b64encode(cached_info.optimized_data).decode()}"
            
            # Return original URL
            return url
            
        except Exception as e:
            self.logger.error(f"Failed to get resource URL for {url}: {e}")
            return url
    
    def _data_url(self, data: bytes, mime_type: str) -> str:
        """Create data URL"""
        return f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
    
    def add_load_start_callback(self, callback: Callable):
        """Add load start callback"""
        self.load_start_callbacks.append(callback)
    
    def add_load_complete_callback(self, callback: Callable):
        """Add load complete callback"""
        self.load_complete_callbacks.append(callback)
    
    def add_load_error_callback(self, callback: Callable):
        """Add load error callback"""
        self.load_error_callbacks.append(callback)
    
    def _trigger_load_start(self, url: str):
        """Trigger load start callbacks"""
        for callback in self.load_start_callbacks:
            try:
                callback(url)
            except Exception as e:
                self.logger.error(f"Load start callback error: {e}")
    
    def _trigger_load_complete(self, url: str, resource_info: ResourceInfo):
        """Trigger load complete callbacks"""
        for callback in self.load_complete_callbacks:
            try:
                callback(url, resource_info)
            except Exception as e:
                self.logger.error(f"Load complete callback error: {e}")
    
    def _trigger_load_error(self, url: str, error: str):
        """Trigger load error callbacks"""
        for callback in self.load_error_callbacks:
            try:
                callback(url, error)
            except Exception as e:
                self.logger.error(f"Load error callback error: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.resource_cache_lock:
            return {
                'cached_resources': len(self.resource_cache),
                'cache_size': sum(info.size for info in self.resource_cache.values()),
                'priority_queue_size': len(self.priority_queue),
                'loading_resources': len(self.loading_resources)
            }
    
    def clear_cache(self):
        """Clear resource cache"""
        with self.resource_cache_lock:
            self.resource_cache.clear()
        
        with self.priority_lock:
            self.priority_queue.clear()
        
        self.logger.info("Resource cache cleared")
    
    def stop_background_loading(self):
        """Stop background loading"""
        self.background_loading = False
        if self.background_thread:
            self.background_thread.join(timeout=5)
        
        self.logger.info("Background loading stopped")

class LazyImageLoader:
    """Lazy image loader for Flask templates"""
    
    def __init__(self, lazy_loader: LazyResourceLoader):
        self.lazy_loader = lazy_loader
        self.logger = logging.getLogger(__name__)
    
    def lazy_image(self, url: str, alt_text: str = "", width: int = None, height: int = None, 
                   loading: str = "lazy", class_name: str = "") -> str:
        """Generate lazy image tag"""
        try:
            # Get lazy URL
            lazy_url = self.lazy_loader.get_resource_url(url, ResourceType.IMAGE)
            
            # Build img tag
            img_attrs = {
                'src': lazy_url,
                'alt': alt_text,
                'loading': loading,
                'class': f"lazy-image {class_name}".strip()
            }
            
            if width:
                img_attrs['width'] = width
            if height:
                img_attrs['height'] = height
            
            # Build tag
            attrs = ' '.join(f'{k}="{v}"' for k, v in img_attrs.items() if v)
            return f'<img {attrs}>'
            
        except Exception as e:
            self.logger.error(f"Failed to generate lazy image tag: {e}")
            return f'<img src="{url}" alt="{alt_text}">'

class LazyResourceHelper:
    """Helper class for lazy loading in Flask"""
    
    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.lazy_loader = LazyResourceLoader(config)
        self.image_loader = LazyImageLoader(self.lazy_loader)
        self.logger = logging.getLogger(__name__)
    
    def get_lazy_image(self, url: str, alt_text: str = "", width: int = None, height: int = None, 
                      loading: str = "lazy", class_name: str = "") -> str:
        """Get lazy image HTML"""
        return self.image_loader.lazy_image(url, alt_text, width, height, loading, class_name)
    
    def preload_resource(self, url: str, resource_type: ResourceType = None, priority: int = 0):
        """Preload resource"""
        self.lazy_loader.preload_resource(url, resource_type, priority)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.lazy_loader.get_cache_stats()

# Global lazy loader instance
_lazy_resource_helper = None

def get_lazy_resource_helper() -> LazyResourceHelper:
    """Get global lazy resource helper instance"""
    global _lazy_resource_helper
    if _lazy_resource_helper is None:
        config = PerformanceConfig()
        _lazy_resource_helper = LazyResourceHelper(config)
    return _lazy_resource_helper