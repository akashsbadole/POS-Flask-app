#!/usr/bin/env python3
"""
Simple migration to add remaining columns to menu_items table
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models.menu_item import MenuItem
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_columns():
    """Add missing columns to menu_items table one by one"""
    
    with app.app_context():
        try:
            logger.info("Adding missing columns to menu_items table...")
            
            # List of columns to add (without the checkmark character that caused issues)
            columns_to_add = [
                ('is_vegan', 'BOOLEAN DEFAULT 0'),
                ('is_gluten_free', 'BOOLEAN DEFAULT 0'),
                ('cooking_time', 'INTEGER DEFAULT 15'),
                ('difficulty', 'VARCHAR(20) DEFAULT \'Medium\''),
                ('popularity_rating', 'INTEGER DEFAULT 3'),
                ('calories', 'INTEGER DEFAULT 0'),
                ('protein', 'INTEGER DEFAULT 0'),
                ('carbs', 'INTEGER DEFAULT 0'),
                ('fat', 'INTEGER DEFAULT 0')
            ]
            
            for column_name, column_def in columns_to_add:
                try:
                    # Check if column exists
                    result = db.session.execute(text("PRAGMA table_info(menu_items)"))
                    columns = [row[1] for row in result.fetchall()]
                    
                    if column_name not in columns:
                        logger.info(f"Adding column: {column_name}")
                        db.session.execute(text(f"ALTER TABLE menu_items ADD COLUMN {column_name} {column_def}"))
                        db.session.commit()
                        logger.info(f"Successfully added column: {column_name}")
                    else:
                        logger.info(f"Column already exists: {column_name}")
                        
                except Exception as e:
                    logger.error(f"Error adding column {column_name}: {e}")
                    db.session.rollback()
                    
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            db.session.rollback()

if __name__ == "__main__":
    add_missing_columns()