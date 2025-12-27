"""
Complete Migration: Add All Missing User Model Fields
Adds all fields defined in the User model that are missing from the database
"""

import sqlite3
import os

def upgrade():
    """Add all missing user management fields to users table"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'restaurant_pos.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First, let's check what columns already exist
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        # List of all fields we need (based on User model)
        required_fields = [
            ('full_name', 'VARCHAR(120)'),
            ('avatar_path', 'VARCHAR(255)'),
            ('phone', 'VARCHAR(20)'),
            ('address', 'TEXT'),
            ('bio', 'TEXT'),
            ('date_of_birth', 'DATE'),
            ('preferred_language', 'VARCHAR(10) DEFAULT "en"'),
            ('preferred_timezone', 'VARCHAR(50) DEFAULT "UTC"'),
            ('notification_preferences', 'TEXT DEFAULT "{}"'),
            ('failed_login_attempts', 'INTEGER DEFAULT 0'),
            ('locked_until', 'DATETIME'),
            ('last_password_change', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ('profile_updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ('password_reset_token', 'VARCHAR(255)'),
            ('password_reset_expires', 'DATETIME'),
            ('password_reset_attempts', 'INTEGER DEFAULT 0'),
            ('password_reset_last_request', 'DATETIME'),
            ('account_status', 'VARCHAR(20) DEFAULT "active"'),
            ('admin_notes', 'TEXT'),
            ('last_activity', 'DATETIME'),
            ('activity_count', 'INTEGER DEFAULT 0'),
            ('password_expiry_date', 'DATETIME'),
            ('must_change_password', 'BOOLEAN DEFAULT 0')
        ]
        
        # Add missing columns
        added_count = 0
        for field_name, field_type in required_fields:
            if field_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}")
                    print(f"Added column: {field_name}")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        print(f"Error adding {field_name}: {e}")
            else:
                print(f"Column already exists: {field_name}")
        
        # Update existing users to have proper account_status
        cursor.execute("""
            UPDATE users SET account_status = CASE 
                WHEN is_active = 1 THEN 'active'
                ELSE 'inactive'
            END
            WHERE account_status IS NULL
        """)
        
        # Create indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_account_status ON users(account_status)",
            "CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)",
            "CREATE INDEX IF NOT EXISTS idx_users_activity_count ON users(activity_count)",
            "CREATE INDEX IF NOT EXISTS idx_users_password_reset_token ON users(password_reset_token)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"Created index: {index_sql.split(' ')[5]}")
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    print(f"Error creating index: {e}")
        
        conn.commit()
        print(f"Migration completed! Added {added_count} new columns.")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
        raise
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
        indexes_to_drop = [
            "idx_users_password_reset_token",
            "idx_users_activity_count", 
            "idx_users_last_activity",
            "idx_users_account_status"
        ]
        
        for index_name in indexes_to_drop:
            try:
                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
                print(f"Dropped index: {index_name}")
            except sqlite3.OperationalError as e:
                print(f"Error dropping index {index_name}: {e}")
        
        # Drop columns (in reverse order of creation)
        columns_to_drop = [
            'must_change_password',
            'password_expiry_date',
            'activity_count',
            'last_activity',
            'admin_notes',
            'account_status',
            'password_reset_last_request',
            'password_reset_attempts',
            'password_reset_expires',
            'password_reset_token',
            'profile_updated_at',
            'last_password_change',
            'locked_until',
            'failed_login_attempts',
            'notification_preferences',
            'preferred_timezone',
            'preferred_language',
            'date_of_birth',
            'bio',
            'address',
            'phone',
            'avatar_path',
            'full_name'
        ]
        
        for column in columns_to_drop:
            try:
                cursor.execute(f"ALTER TABLE users DROP COLUMN {column}")
                print(f"Dropped column: {column}")
            except sqlite3.OperationalError as e:
                print(f"Error dropping column {column}: {e}")
        
        conn.commit()
        print("Rollback completed successfully!")
        
    except Exception as e:
        print(f"Rollback error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    # Run the migration
    upgrade()