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