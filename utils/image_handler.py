"""
Image handling utilities for Flask POS system
Provides image validation, resizing, and processing functionality
"""

import os
import io
from PIL import Image, ImageOps
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

class ImageHandler:
    """Utility class for handling image operations"""
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    
    # Maximum file size (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # Image dimensions for different purposes
    THUMBNAIL_SIZE = (150, 150)
    MEDIUM_SIZE = (400, 400)
    LARGE_SIZE = (800, 800)
    
    @staticmethod
    def is_allowed_file(filename):
        """Check if file has allowed extension"""
        if not filename:
            return False
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ImageHandler.ALLOWED_EXTENSIONS
    
    @staticmethod
    def validate_image(file_path):
        """
        Validate image file
        Returns: (is_valid, error_message)
        """
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > ImageHandler.MAX_FILE_SIZE:
            return False, f"File size exceeds maximum allowed size of {ImageHandler.MAX_FILE_SIZE // (1024*1024)}MB"
        
        try:
            # Try to open the image with PIL
            with Image.open(file_path) as img:
                img.verify()
            return True, "Valid image"
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
    
    @staticmethod
    def resize_image(image_path, output_path, size=MEDIUM_SIZE, quality=85):
        """
        Resize image to specified dimensions while maintaining aspect ratio
        Returns: (success, output_path_or_error_message)
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Resize with high-quality resampling
                img = ImageOps.exif_transpose(img)  # Handle EXIF rotation
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Create output directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Save the resized image
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                
            return True, output_path
        except Exception as e:
            return False, f"Error resizing image: {str(e)}"
    
    @staticmethod
    def create_thumbnail(image_path, thumbnail_path=None):
        """
        Create a thumbnail version of the image
        Returns: (success, thumbnail_path_or_error_message)
        """
        if thumbnail_path is None:
            base_name = os.path.splitext(image_path)[0]
            thumbnail_path = f"{base_name}_thumb.jpg"
        
        return ImageHandler.resize_image(image_path, thumbnail_path, ImageHandler.THUMBNAIL_SIZE, quality=75)
    
    @staticmethod
    def generate_unique_filename(original_filename, prefix="menu_item"):
        """
        Generate a unique filename for uploaded images
        Format: prefix_YYYYMMDD_UUID.ext
        """
        if not original_filename:
            return None
        
        # Get file extension
        ext = os.path.splitext(original_filename)[1].lower()
        if not ext:
            ext = '.jpg'  # Default extension
        
        # Generate unique filename
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{prefix}_{date_str}_{unique_id}{ext}"
        
        return filename
    
    @staticmethod
    def process_uploaded_image(file_storage, upload_folder, prefix="menu_item"):
        """
        Process an uploaded image file
        Returns: (success, result_dict_or_error_message)
        
        result_dict contains:
        - original_path: path to original uploaded image
        - thumbnail_path: path to thumbnail version
        - filename: generated filename
        - file_size: size of uploaded file
        """
        if not file_storage or not file_storage.filename:
            return False, "No file provided"
        
        if not ImageHandler.is_allowed_file(file_storage.filename):
            return False, f"File type not allowed. Allowed types: {', '.join(ImageHandler.ALLOWED_EXTENSIONS)}"
        
        try:
            # Generate unique filename
            filename = ImageHandler.generate_unique_filename(file_storage.filename, prefix)
            
            # Create upload directory if it doesn't exist
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save original file
            original_path = os.path.join(upload_folder, filename)
            file_storage.save(original_path)
            
            # Validate the saved image
            is_valid, error_msg = ImageHandler.validate_image(original_path)
            if not is_valid:
                # Remove invalid file
                if os.path.exists(original_path):
                    os.remove(original_path)
                return False, error_msg
            
            # Create thumbnail
            thumbnail_name = f"thumb_{filename}"
            thumbnail_path = os.path.join(upload_folder, thumbnail_name)
            thumb_success, thumb_result = ImageHandler.create_thumbnail(original_path, thumbnail_path)
            
            if not thumb_success:
                # If thumbnail creation fails, continue without thumbnail
                thumbnail_path = None
            
            # Get file size
            file_size = os.path.getsize(original_path)
            
            result = {
                'original_path': original_path,
                'thumbnail_path': thumbnail_path,
                'filename': filename,
                'file_size': file_size
            }
            
            return True, result
            
        except Exception as e:
            return False, f"Error processing uploaded image: {str(e)}"
    
    @staticmethod
    def delete_image_files(image_path, thumbnail_path=None):
        """
        Delete image files from disk
        Returns: (success, error_message_if_any)
        """
        try:
            # Delete main image
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
            
            # Delete thumbnail
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            
            return True, None
        except Exception as e:
            return False, f"Error deleting image files: {str(e)}"
    
    @staticmethod
    def get_image_info(image_path):
        """
        Get information about an image file
        Returns: (success, info_dict_or_error_message)
        """
        try:
            if not os.path.exists(image_path):
                return False, "Image file does not exist"
            
            with Image.open(image_path) as img:
                info = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'file_size': os.path.getsize(image_path)
                }
            
            return True, info
        except Exception as e:
            return False, f"Error getting image info: {str(e)}"


class FlaskImageHandler(ImageHandler):
    """Image handler with Flask-specific functionality"""
    
    @staticmethod
    def handle_upload(request_files, field_name='image', upload_folder='static/uploads/menu_items'):
        """
        Handle image upload from Flask request
        Returns: (success, result_dict_or_error_message)
        """
        if field_name not in request_files:
            return False, "No image file provided"
        
        file_storage = request_files[field_name]
        return ImageHandler.process_uploaded_image(file_storage, upload_folder)
    
    @staticmethod
    def get_relative_path(full_path, base_path='static/uploads'):
        """
        Convert full file path to relative path for database storage
        """
        if not full_path:
            return None
        
        # Normalize paths
        full_path = os.path.normpath(full_path)
        base_path = os.path.normpath(base_path)
        
        # Get relative path
        if full_path.startswith(base_path):
            return os.path.relpath(full_path, base_path)
        else:
            return full_path
    
    @staticmethod
    def get_full_path(relative_path, base_path='static/uploads'):
        """
        Convert relative path from database to full file path
        """
        if not relative_path:
            return None
        
        return os.path.join(base_path, relative_path)
    
    @staticmethod
    def get_url_path(relative_path, static_url='/static/uploads'):
        """
        Convert relative path to URL for serving images
        """
        if not relative_path:
            return None
        
        return f"{static_url}/{relative_path}"
    
    @staticmethod
    def handle_image_upload_in_route(request, upload_folder='static/uploads/menu_items', prefix='menu_item'):
        """
        Complete image handling for Flask routes
        Returns: (success, relative_path_or_error_message)
        """
        if 'image' not in request.files:
            return False, "No image file provided"
        
        file = request.files['image']
        
        if file.filename == '':
            return False, "No image file selected"
        
        # Process the upload
        success, result = FlaskImageHandler.handle_upload(
            request.files, 'image', upload_folder
        )
        
        if not success:
            return False, result
        
        # Convert to relative path for database storage
        relative_path = FlaskImageHandler.get_relative_path(
            result['original_path'], upload_folder
        )
        
        return True, relative_path

class WhiteLabelImageHandler(ImageHandler):
    """Image handler with white label specific functionality"""
    
    # White label logo size specifications
    LOGO_SIZES = {
        'main': {'width': 200, 'height': 80, 'quality': 90},
        'header': {'width': 150, 'height': 60, 'quality': 90},
        'footer': {'width': 120, 'height': 48, 'quality': 85},
        'favicon': {'width': 32, 'height': 32, 'quality': 80},
        'invoice': {'width': 180, 'height': 72, 'quality': 90},
        'email': {'width': 200, 'height': 80, 'quality': 90},
        'login': {'width': 200, 'height': 80, 'quality': 90}
    }
    
    # Allowed logo formats for white labeling
    LOGO_FORMATS = {'png', 'jpg', 'jpeg', 'svg', 'webp'}
    
    @staticmethod
    def validate_logo_format(filename, allowed_formats=None):
        """Validate logo file format for white label uploads"""
        if allowed_formats is None:
            allowed_formats = WhiteLabelImageHandler.LOGO_FORMATS
        
        if not filename:
            return False, "No filename provided"
        
        if '.' not in filename:
            return False, "File must have an extension"
        
        ext = filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_formats:
            return False, f"Invalid format. Allowed: {', '.join(allowed_formats)}"
        
        return True, "Valid logo format"
    
    @staticmethod
    def validate_logo_size(file_path, max_size_kb=2048):
        """Validate logo file size for white label uploads"""
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        file_size_kb = os.path.getsize(file_path) / 1024
        if file_size_kb > max_size_kb:
            return False, f"File size ({file_size_kb:.1f}KB) exceeds maximum ({max_size_kb}KB)"
        
        return True, "Valid logo size"
    
    @staticmethod
    def resize_logo_for_context(image_path, output_path, context='main'):
        """Resize logo for specific white label context"""
        if context not in WhiteLabelImageHandler.LOGO_SIZES:
            context = 'main'  # Default fallback
        
        size_config = WhiteLabelImageHandler.LOGO_SIZES[context]
        target_size = (size_config['width'], size_config['height'])
        quality = size_config['quality']
        
        return WhiteLabelImageHandler.resize_image(
            image_path, output_path, target_size, quality
        )
    
    @staticmethod
    def process_white_label_logo_upload(file_storage, logo_type='main', upload_folder='static/images/branding'):
        """Process logo upload for white label purposes"""
        if not file_storage or not file_storage.filename:
            return False, "No file provided"
        
        # Validate format
        is_valid_format, format_msg = WhiteLabelImageHandler.validate_logo_format(file_storage.filename)
        if not is_valid_format:
            return False, format_msg
        
        try:
            # Generate unique filename with type prefix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            ext = os.path.splitext(file_storage.filename)[1].lower()
            
            # Create directory structure
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save original file temporarily
            temp_filename = f"temp_{timestamp}_{unique_id}{ext}"
            temp_path = os.path.join(upload_folder, temp_filename)
            file_storage.save(temp_path)
            
            # Validate file size
            max_size_kb = int(Settings.get('logo_upload_max_size', 2048))
            is_valid_size, size_msg = WhiteLabelImageHandler.validate_logo_size(temp_path, max_size_kb)
            if not is_valid_size:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False, size_msg
            
            # Validate image integrity
            is_valid_image, image_msg = WhiteLabelImageHandler.validate_image(temp_path)
            if not is_valid_image:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False, image_msg
            
            # Generate final filename
            final_filename = f"{logo_type}_logo_{timestamp}_{unique_id}{ext}"
            final_path = os.path.join(upload_folder, final_filename)
            
            # Move and resize if needed
            if ext.lower() == 'svg':
                # For SVG files, just move without resizing
                os.rename(temp_path, final_path)
                return True, {
                    'original_path': final_path,
                    'filename': final_filename,
                    'file_size': os.path.getsize(final_path),
                    'format': 'svg'
                }
            else:
                # Resize for context
                success, result = WhiteLabelImageHandler.resize_logo_for_context(
                    temp_path, final_path, logo_type
                )
                
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                if not success:
                    return False, result
                
                return True, {
                    'original_path': final_path,
                    'filename': final_filename,
                    'file_size': os.path.getsize(final_path),
                    'format': 'image'
                }
            
        except Exception as e:
            return False, f"Error processing logo upload: {str(e)}"
    
    @staticmethod
    def delete_white_label_logo(logo_path):
        """Delete white label logo files"""
        if not logo_path:
            return True, None
        
        try:
            if os.path.exists(logo_path):
                os.remove(logo_path)
            return True, None
        except Exception as e:
            return False, f"Error deleting logo: {str(e)}"
    
    @staticmethod
    def get_white_label_logo_info(logo_path):
        """Get information about white label logo"""
        if not logo_path or not os.path.exists(logo_path):
            return False, "Logo file does not exist"
        
        try:
            with Image.open(logo_path) as img:
                info = {
                    'path': logo_path,
                    'filename': os.path.basename(logo_path),
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'file_size': os.path.getsize(logo_path),
                    'recommended_contexts': WhiteLabelImageHandler.get_recommended_contexts(img.width, img.height)
                }
            
            return True, info
        except Exception as e:
            return False, f"Error getting logo info: {str(e)}"
    
    @staticmethod
    def get_recommended_contexts(width, height):
        """Get recommended usage contexts based on logo dimensions"""
        recommendations = []
        
        # Aspect ratio analysis
        aspect_ratio = width / height if height > 0 else 1
        
        # Size-based recommendations
        if width >= 200 and height >= 80:
            recommendations.extend(['main', 'email', 'login'])
        
        if width >= 150 and height >= 60:
            recommendations.append('header')
        
        if width >= 120 and height >= 48:
            recommendations.append('footer')
        
        if width >= 180 and height >= 72:
            recommendations.append('invoice')
        
        # Favicon recommendation (square-ish logos)
        if 0.8 <= aspect_ratio <= 1.2 and width >= 32 and height >= 32:
            recommendations.append('favicon')
        
        return recommendations
    
    @staticmethod
    def optimize_logo_for_web(logo_path, output_path=None):
        """Optimize logo for web usage"""
        if output_path is None:
            base, ext = os.path.splitext(logo_path)
            output_path = f"{base}_optimized{ext}"
        
        try:
            with Image.open(logo_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Optimize and save
                img.save(output_path, 'JPEG', quality=85, optimize=True)
                
            return True, output_path
        except Exception as e:
            return False, f"Error optimizing logo: {str(e)}"