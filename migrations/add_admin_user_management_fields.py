"""
Migration: Add Admin User Management Fields
Adds new fields for enhanced admin user management capabilities
"""

import sqlite3
import os

def upgrade():
    """Add new admin management fields to users table"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'restaurant_pos.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add new columns
        cursor.execute("""
            ALTER TABLE users ADD COLUMN account_status VARCHAR(20) DEFAULT 'active'
        """)
        
        cursor.execute("""
            ALTER TABLE users ADD COLUMN admin_notes TEXT
        """)
        
        cursor.execute("""
            ALTER TABLE users ADD COLUMN last_activity DATETIME
        """)
        
        cursor.execute("""
            ALTER TABLE users ADD COLUMN activity_count INTEGER DEFAULT 0
        """)
        
        cursor.execute("""
            ALTER TABLE users ADD COLUMN password_expiry_date DATETIME
        """)
        
        cursor.execute("""
            ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0
        """)
        
        # Update existing users to have proper account_status
        cursor.execute("""
            UPDATE users SET account_status = CASE 
                WHEN is_active = 1 THEN 'active'
                ELSE 'inactive'
            END
        """)
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_account_status ON users(account_status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_activity_count ON users(activity_count)
        """)
        
        conn.commit()
        print("Admin user management fields migration completed successfully!")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Columns already exist, migration skipped.")
        else:
            raise e
    finally:
        conn.close()

def downgrade():
    """Remove the added columns"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'restaurant_pos.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Drop indexes
        cursor.execute("DROP INDEX IF EXISTS idx_users_activity_count")
        cursor.execute("DROP INDEX IF EXISTS idx_users_last_activity")
        cursor.execute("DROP INDEX IF EXISTS idx_users_account_status")
        
        # Drop columns
        cursor.execute("ALTER TABLE users DROP COLUMN must_change_password")
        cursor.execute("ALTER TABLE users DROP COLUMN password_expiry_date")
        cursor.execute("ALTER TABLE users DROP COLUMN activity_count")
        cursor.execute("ALTER TABLE users DROP COLUMN last_activity")
        cursor.execute("ALTER TABLE users DROP COLUMN admin_notes")
        cursor.execute("ALTER TABLE users DROP COLUMN account_status")
        
        conn.commit()
        print("Admin user management fields migration rolled back successfully!")
        
    finally:
        conn.close()

if __name__ == '__main__':
    # Run the migration
    upgrade()