"""
Add Remaining User Fields
Adds the remaining fields that are still missing
"""

import sqlite3
import os

def upgrade():
    """Add remaining missing fields"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'restaurant_pos.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns: {existing_columns}")
        
        # Add the remaining fields
        remaining_fields = [
            ('last_password_change', 'DATETIME'),
            ('profile_updated_at', 'DATETIME')
        ]
        
        for field_name, field_type in remaining_fields:
            if field_name not in existing_columns:
                try:
                    # For datetime fields with default, we'll add them without default first
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}")
                    print(f"Added column: {field_name}")
                except sqlite3.OperationalError as e:
                    print(f"Error adding {field_name}: {e}")
            else:
                print(f"Column already exists: {field_name}")
        
        # Update existing records to have current timestamp for these fields
        cursor.execute("""
            UPDATE users SET 
                last_password_change = COALESCE(last_password_change, datetime('now')),
                profile_updated_at = COALESCE(profile_updated_at, datetime('now'))
            WHERE last_password_change IS NULL OR profile_updated_at IS NULL
        """)
        
        conn.commit()
        print("Remaining fields migration completed!")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    upgrade()