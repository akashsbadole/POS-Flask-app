"""
Migration to add websocket and real-time fields to orders table
"""
import sqlite3
import os

def migrate():
    """Add websocket fields to orders table"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'restaurant_pos.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add new columns to orders table
        columns_to_add = [
            "realtime_enabled BOOLEAN DEFAULT 1",
            "websocket_broadcast BOOLEAN DEFAULT 1", 
            "priority_level INTEGER DEFAULT 0",
            "estimated_prep_time INTEGER",
            "actual_prep_time INTEGER",
            "kitchen_station VARCHAR(50)",
            "last_websocket_update DATETIME",
            "realtime_subscribers INTEGER DEFAULT 0"
        ]
        
        for column_def in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE orders ADD COLUMN {column_def}")
                print(f"Added column: {column_def}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"Column already exists: {column_def}")
                else:
                    print(f"Error adding column {column_def}: {e}")
        
        conn.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()