"""
Import/Export Manager for Restaurant POS System
Handles bulk import/export of menu items and categories
"""

import csv
import json
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from decimal import Decimal
from flask import current_app
from werkzeug.utils import secure_filename
from models import db, MenuItem, Category, User
from utils.permissions import has_permission

class ImportExportError(Exception):
    """Custom exception for import/export operations"""
    pass

class ImportExportManager:
    """Core import/export functionality for menu items and categories"""
    
    # Supported file formats
    SUPPORTED_FORMATS = {
        'csv': ['.csv'],
        'excel': ['.xlsx', '.xls']
    }
    
    # Required columns for import
    REQUIRED_COLUMNS = [
        'name', 'price', 'category'
    ]
    
    # Optional columns
    OPTIONAL_COLUMNS = [
        'description', 'stock_quantity', 'min_stock_level', 'image_path',
        'spice_level', 'is_vegetarian', 'is_vegan', 'is_gluten_free',
        'cooking_time', 'difficulty', 'popularity_rating', 'calories',
        'protein', 'carbs', 'fat', 'category_description'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.import_log = []
        
    def validate_file_format(self, filename: str) -> bool:
        """Validate if file format is supported"""
        _, ext = os.path.splitext(filename.lower())
        return any(ext in formats for formats in self.SUPPORTED_FORMATS.values())
    
    def get_file_format(self, filename: str) -> str:
        """Get file format from filename"""
        _, ext = os.path.splitext(filename.lower())
        if ext in self.SUPPORTED_FORMATS['csv']:
            return 'csv'
        elif ext in self.SUPPORTED_FORMATS['excel']:
            return 'excel'
        return 'unknown'
    
    def validate_import_data(self, data: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate import data for required columns and data types"""
        errors = []
        
        if not data:
            errors.append("No data found in file")
            return False, errors
        
        # Check required columns
        for row_idx, row in enumerate(data, 1):
            missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in row or not row[col]]
            if missing_cols:
                errors.append(f"Row {row_idx}: Missing required columns: {', '.join(missing_cols)}")
            
            # Validate data types
            try:
                if 'price' in row and row['price']:
                    float(row['price'])
            except (ValueError, TypeError):
                errors.append(f"Row {row_idx}: Invalid price value: {row['price']}")
            
            # Validate boolean fields
            bool_fields = ['is_vegetarian', 'is_vegan', 'is_gluten_free']
            for field in bool_fields:
                if field in row and row[field]:
                    if str(row[field]).lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                        errors.append(f"Row {row_idx}: Invalid boolean value for {field}: {row[field]}")
        
        return len(errors) == 0, errors
    
    def create_categories_from_import(self, data: List[Dict]) -> Dict[str, Category]:
        """Create categories from import data"""
        category_dict = {}
        categories_created = 0
        
        for row in data:
            category_name = row.get('category', '').strip()
            category_desc = row.get('category_description', '').strip()
            
            if category_name and category_name not in category_dict:
                # Check if category already exists
                existing = Category.query.filter_by(name=category_name).first()
                if not existing:
                    category = Category.create_category(
                        name=category_name,
                        description=category_desc or f"Category for {category_name}"
                    )
                    if category:
                        category_dict[category_name] = category
                        categories_created += 1
                        self.import_log.append(f"Created category: {category_name}")
                    else:
                        self.errors.append(f"Failed to create category: {category_name}")
                else:
                    category_dict[category_name] = existing
        
        return category_dict
    
    def import_menu_items(self, data: List[Dict], user_id: int, update_existing: bool = False) -> Dict[str, int]:
        """Import menu items from data"""
        results = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Create categories first
        category_dict = self.create_categories_from_import(data)
        
        for row_idx, row in enumerate(data, 1):
            try:
                # Skip if required fields are missing
                if not all(row.get(col) for col in self.REQUIRED_COLUMNS):
                    self.errors.append(f"Row {row_idx}: Missing required data")
                    results['errors'] += 1
                    continue
                
                category_name = row['category'].strip()
                category = category_dict.get(category_name)
                if not category:
                    self.errors.append(f"Row {row_idx}: Category not found or created: {category_name}")
                    results['errors'] += 1
                    continue
                
                # Check if item already exists
                existing_item = MenuItem.query.filter_by(name=row['name'].strip()).first()
                
                if existing_item and not update_existing:
                    self.warnings.append(f"Row {row_idx}: Item already exists: {row['name']}")
                    results['skipped'] += 1
                    continue
                
                # Prepare item data
                item_data = {
                    'name': row['name'].strip(),
                    'price': Decimal(str(row['price'])),
                    'category_id': category.id,
                    'description': row.get('description', '').strip() or None,
                    'stock_quantity': int(row.get('stock_quantity', 0)),
                    'min_stock_level': int(row.get('min_stock_level', 10)),
                    'image_path': row.get('image_path', '').strip() or None,
                }
                
                # Add extended attributes if they exist
                extended_attrs = ['spice_level', 'cooking_time', 'difficulty', 'popularity_rating', 
                                'calories', 'protein', 'carbs', 'fat']
                for attr in extended_attrs:
                    if attr in row and row[attr]:
                        try:
                            if attr in ['cooking_time', 'popularity_rating', 'calories', 'protein', 'carbs', 'fat']:
                                item_data[attr] = int(row[attr])
                            else:
                                item_data[attr] = str(row[attr]).strip()
                        except (ValueError, TypeError):
                            pass
                
                # Handle boolean fields
                bool_fields = ['is_vegetarian', 'is_vegan', 'is_gluten_free']
                for field in bool_fields:
                    if field in row and row[field]:
                        value = str(row[field]).lower()
                        item_data[field] = value in ['true', '1', 'yes']
                
                if existing_item and update_existing:
                    # Update existing item
                    success = existing_item.update(**item_data)
                    if success:
                        results['updated'] += 1
                        self.import_log.append(f"Updated item: {existing_item.name}")
                    else:
                        self.errors.append(f"Row {row_idx}: Failed to update item: {row['name']}")
                        results['errors'] += 1
                else:
                    # Create new item
                    new_item = MenuItem.create_menu_item(**item_data)
                    if new_item:
                        results['created'] += 1
                        self.import_log.append(f"Created item: {new_item.name}")
                    else:
                        self.errors.append(f"Row {row_idx}: Failed to create item: {row['name']}")
                        results['errors'] += 1
                        
            except Exception as e:
                self.errors.append(f"Row {row_idx}: Unexpected error: {str(e)}")
                results['errors'] += 1
        
        return results
    
    def export_menu_items(self, format_type: str = 'csv', category_filter: str = None) -> Dict[str, Any]:
        """Export menu items to file"""
        try:
            # Build query
            query = MenuItem.query.filter_by(is_active=True)
            
            if category_filter:
                category = Category.query.filter_by(name=category_filter).first()
                if category:
                    query = query.filter_by(category_id=category.id)
            
            menu_items = query.order_by(Category.name, MenuItem.name).all()
            
            if not menu_items:
                raise ImportExportError("No menu items found to export")
            
            # Prepare data
            export_data = []
            for item in menu_items:
                row = {
                    'id': item.id,
                    'name': item.name,
                    'description': item.description or '',
                    'price': float(item.price),
                    'category': item.category.name if item.category else '',
                    'category_description': item.category.description if item.category else '',
                    'stock_quantity': item.stock_quantity,
                    'min_stock_level': item.min_stock_level,
                    'image_path': item.image_path or '',
                    'is_active': item.is_active,
                    'is_available': item.is_available,
                    'created_at': item.created_at.isoformat() if item.created_at else '',
                    'updated_at': item.updated_at.isoformat() if item.updated_at else '',
                }
                
                # Add extended attributes if they exist
                extended_attrs = ['spice_level', 'is_vegetarian', 'is_vegan', 'is_gluten_free',
                                'cooking_time', 'difficulty', 'popularity_rating', 'calories',
                                'protein', 'carbs', 'fat']
                for attr in extended_attrs:
                    if hasattr(item, attr):
                        value = getattr(item, attr)
                        row[attr] = value if value is not None else ''
                
                export_data.append(row)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"menu_items_export_{timestamp}.{format_type}"
            filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'exports'), filename)
            
            # Ensure export directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Export based on format
            if format_type == 'csv':
                return self._export_to_csv(export_data, filepath)
            elif format_type == 'excel':
                return self._export_to_excel(export_data, filepath)
            else:
                raise ImportExportError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            raise ImportExportError(f"Export failed: {str(e)}")
    
    def _export_to_csv(self, data: List[Dict], filepath: str) -> Dict[str, Any]:
        """Export data to CSV format"""
        if not data:
            raise ImportExportError("No data to export")
        
        fieldnames = data[0].keys()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        return {
            'success': True,
            'filename': os.path.basename(filepath),
            'filepath': filepath,
            'records': len(data),
            'format': 'csv'
        }
    
    def _export_to_excel(self, data: List[Dict], filepath: str) -> Dict[str, Any]:
        """Export data to Excel format"""
        if not data:
            raise ImportExportError("No data to export")
        
        df = pd.DataFrame(data)
        
        # Write to Excel with formatting
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Menu Items', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Menu Items']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return {
            'success': True,
            'filename': os.path.basename(filepath),
            'filepath': filepath,
            'records': len(data),
            'format': 'excel'
        }
    
    def read_import_file(self, file_path: str) -> Tuple[List[Dict], str]:
        """Read import file and return data"""
        format_type = self.get_file_format(file_path)
        
        if format_type == 'csv':
            return self._read_csv_file(file_path)
        elif format_type == 'excel':
            return self._read_excel_file(file_path)
        else:
            raise ImportExportError(f"Unsupported file format: {format_type}")
    
    def _read_csv_file(self, file_path: str) -> Tuple[List[Dict], str]:
        """Read CSV file"""
        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Clean up the data
                    cleaned_row = {k.strip(): v.strip() if isinstance(v, str) else v 
                                 for k, v in row.items() if v}
                    data.append(cleaned_row)
        except Exception as e:
            raise ImportExportError(f"Error reading CSV file: {str(e)}")
        
        return data, 'csv'
    
    def _read_excel_file(self, file_path: str) -> Tuple[List[Dict], str]:
        """Read Excel file"""
        try:
            df = pd.read_excel(file_path)
            # Convert to list of dictionaries
            data = df.fillna('').to_dict('records')
            # Clean up the data
            for row in data:
                for k, v in row.items():
                    if isinstance(v, str):
                        row[k] = v.strip()
        except Exception as e:
            raise ImportExportError(f"Error reading Excel file: {str(e)}")
        
        return data, 'excel'
    
    def generate_import_template(self, format_type: str = 'csv') -> Dict[str, Any]:
        """Generate import template file"""
        # Template data
        template_data = [
            {
                'name': 'Sample Dish Name',
                'description': 'Detailed description of the dish',
                'price': 250.00,
                'category': 'Sample Category',
                'category_description': 'Description for the category',
                'stock_quantity': 50,
                'min_stock_level': 10,
                'image_path': 'static/images/dish.jpg',
                'spice_level': 'Medium',
                'is_vegetarian': 'true',
                'is_vegan': 'false',
                'is_gluten_free': 'false',
                'cooking_time': 25,
                'difficulty': 'Medium',
                'popularity_rating': 8,
                'calories': 300,
                'protein': 15,
                'carbs': 25,
                'fat': 12
            }
        ]
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"menu_import_template_{timestamp}.{format_type}"
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'templates'), filename)
        
        # Ensure template directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Create template based on format
        if format_type == 'csv':
            result = self._export_to_csv(template_data, filepath)
        elif format_type == 'excel':
            result = self._export_to_excel(template_data, filepath)
        else:
            raise ImportExportError(f"Unsupported template format: {format_type}")
        
        return result
    
    def get_import_history(self, user_id: int = None, limit: int = 50) -> List[Dict]:
        """Get import/export history (placeholder - implement with database table)"""
        # This would typically be stored in a database table
        # For now, return empty list
        return []
    
    def save_import_log(self, operation_type: str, results: Dict, user_id: int, filename: str = None):
        """Save import/export operation log"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation_type': operation_type,
            'user_id': user_id,
            'filename': filename,
            'results': results,
            'errors': self.errors,
            'warnings': self.warnings,
            'log': self.import_log
        }
        
        # Save to database (implement a proper logs table)
        # For now, just return the log entry
        return log_entry
    
    def clear_session_data(self):
        """Clear session data (errors, warnings, logs)"""
        self.errors = []
        self.warnings = []
        self.import_log = []

# Utility functions
def validate_file_upload(file_storage, allowed_extensions=None) -> Tuple[bool, str]:
    """Validate uploaded file"""
    if not file_storage or not file_storage.filename:
        return False, "No file selected"
    
    filename = secure_filename(file_storage.filename)
    if not filename:
        return False, "Invalid filename"
    
    if allowed_extensions:
        _, ext = os.path.splitext(filename.lower())
        if ext not in allowed_extensions:
            return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    return True, "File is valid"

def get_import_export_permissions(user) -> Dict[str, bool]:
    """Get import/export permissions for user"""
    if not user:
        return {
            'can_import': False,
            'can_export': False,
            'can_view_history': False
        }
    
    return {
        'can_import': has_permission(user, 'menu', 'create') or has_permission(user, 'menu', 'update'),
        'can_export': has_permission(user, 'menu', 'read'),
        'can_view_history': has_permission(user, 'menu', 'read')
    }