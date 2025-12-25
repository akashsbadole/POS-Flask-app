"""
Migration: Add Extended Menu Item Attributes
Adds columns for Indian food specific attributes to menu_items table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from app import create_app
from models import db
from sqlalchemy import text

def add_extended_attributes():
    """Add extended attributes to menu_items table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Define the new columns
            new_columns = [
                "ALTER TABLE menu_items ADD COLUMN spice_level VARCHAR(20)",
                "ALTER TABLE menu_items ADD COLUMN is_vegetarian BOOLEAN DEFAULT 1",
                "ALTER TABLE menu_items ADD COLUMN is_vegan BOOLEAN DEFAULT 0", 
                "ALTER TABLE menu_items ADD COLUMN is_gluten_free BOOLEAN DEFAULT 0",
                "ALTER TABLE menu_items ADD COLUMN cooking_time INTEGER",
                "ALTER TABLE menu_items ADD COLUMN difficulty VARCHAR(20)",
                "ALTER TABLE menu_items ADD COLUMN popularity_rating INTEGER DEFAULT 5",
                "ALTER TABLE menu_items ADD COLUMN calories INTEGER",
                "ALTER TABLE menu_items ADD COLUMN protein INTEGER",
                "ALTER TABLE menu_items ADD COLUMN carbs INTEGER",
                "ALTER TABLE menu_items ADD COLUMN fat INTEGER"
            ]
            
            # Execute migrations
            for sql in new_columns:
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"✓ Executed: {sql}")
                except Exception as e:
                    # Check if column already exists (SQLite specific)
                    if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"WARNING: Column already exists: {sql}")
                        db.session.rollback()
                        continue
                    else:
                        print(f"ERROR: Error executing: {sql}")
                        print(f"  Error: {e}")
                        db.session.rollback()
                        raise
            
            print("SUCCESS: Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"ERROR: Migration failed: {e}")
            db.session.rollback()
            return False

def rollback_migration():
    """Rollback the extended attributes migration"""
    app = create_app()
    
    with app.app_context():
        try:
            # Define the columns to drop
            columns_to_drop = [
                "ALTER TABLE menu_items DROP COLUMN spice_level",
                "ALTER TABLE menu_items DROP COLUMN is_vegetarian",
                "ALTER TABLE menu_items DROP COLUMN is_vegan", 
                "ALTER TABLE menu_items DROP COLUMN is_gluten_free",
                "ALTER TABLE menu_items DROP COLUMN cooking_time",
                "ALTER TABLE menu_items DROP COLUMN difficulty",
                "ALTER TABLE menu_items DROP COLUMN popularity_rating",
                "ALTER TABLE menu_items DROP COLUMN calories",
                "ALTER TABLE menu_items DROP COLUMN protein",
                "ALTER TABLE menu_items DROP COLUMN carbs",
                "ALTER TABLE menu_items DROP COLUMN fat"
            ]
            
            # Execute rollback (SQLite has limitations on DROP COLUMN)
            # We'll need to recreate the table in SQLite
            print("Note: SQLite has limited DROP COLUMN support. Table recreation may be required.")
            
            for sql in columns_to_drop:
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"Executed rollback: {sql}")
                except Exception as e:
                    print(f"WARNING: Could not rollback: {sql}")
                    print(f"  Error: {e}")
                    db.session.rollback()
            
            print("Rollback completed!")
            return True
            
        except Exception as e:
            print(f"✗ Rollback failed: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("Rolling back extended menu attributes migration...")
        rollback_migration()
    else:
        print("Running extended menu attributes migration...")
        success = add_extended_attributes()
        if success:
            print("Migration completed successfully!")
        else:
            print("Migration failed!")
            sys.exit(1)