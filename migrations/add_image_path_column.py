"""
Database migration script to add image_path column to menu_items table
if it doesn't already exist
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, MenuItem
from config import Config

def add_image_path_column():
    """Add image_path column to menu_items table if it doesn't exist"""
    try:
        # Check if column already exists
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('menu_items')]
        
        if 'image_path' not in columns:
            print("Adding image_path column to menu_items table...")
            
            # Add the column using raw SQL for better control
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    ALTER TABLE menu_items 
                    ADD COLUMN image_path VARCHAR(255)
                """))
                conn.commit()
            
            print("✓ image_path column added successfully")
        else:
            print("✓ image_path column already exists")
        
        # Verify the column was added
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('menu_items')]
        
        if 'image_path' in columns:
            print("✓ Migration completed successfully")
            return True
        else:
            print("✗ Migration failed - column not found after addition")
            return False
            
    except Exception as e:
        print(f"✗ Error during migration: {str(e)}")
        return False

def create_uploads_directory():
    """Create uploads directory structure if it doesn't exist"""
    try:
        # Create main uploads directory
        uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Create menu_items subdirectory
        menu_items_dir = os.path.join(uploads_dir, 'menu_items')
        os.makedirs(menu_items_dir, exist_ok=True)
        
        print(f"✓ Uploads directory created/verified: {menu_items_dir}")
        return True
        
    except Exception as e:
        print(f"✗ Error creating uploads directory: {str(e)}")
        return False

def main():
    """Main migration function"""
    print("=" * 50)
    print("Image Path Column Migration")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize app context
    from app import create_app
    app = create_app()
    
    with app.app_context():
        # Create uploads directory
        create_uploads_directory()
        
        # Add image_path column
        migration_success = add_image_path_column()
        
        print()
        if migration_success:
            print("🎉 Migration completed successfully!")
            print()
            print("Next steps:")
            print("1. Restart your Flask application")
            print("2. Test image upload functionality")
            print("3. Verify images are stored in static/uploads/menu_items/")
        else:
            print("❌ Migration failed!")
            print("Please check the error messages above and fix any issues.")
            return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)