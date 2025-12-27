"""
Database Migration: Add Registration Fields
Adds self-registration support fields to the users table
"""

import sqlite3
import os
from datetime import datetime

def run_migration():
    """Run the registration fields migration"""
    try:
        # Database path
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'restaurant_pos.db')
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add registration fields to users table
        registration_fields = [
            "registration_status VARCHAR(20) DEFAULT 'pending'",
            "registration_timestamp DATETIME",
            "email_verified BOOLEAN DEFAULT 0",
            "email_verification_token VARCHAR(255)",
            "email_verification_expires DATETIME",
            "email_verification_attempts INTEGER DEFAULT 0",
            "registration_ip_address VARCHAR(45)",
            "registration_user_agent TEXT",
            "approved_by INTEGER",
            "approved_at DATETIME",
            "rejection_reason TEXT",
            "registration_attempts INTEGER DEFAULT 0",
            "last_registration_attempt DATETIME"
        ]
        
        # Check if fields already exist
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        fields_to_add = []
        for field in registration_fields:
            field_name = field.split()[0]
            if field_name not in existing_columns:
                fields_to_add.append(field)
        
        if fields_to_add:
            print(f"Adding {len(fields_to_add)} new fields to users table...")
            
            # Add each field
            for field in fields_to_add:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {field}")
                    print(f"Added {field}")
                except sqlite3.Error as e:
                    print(f"Error adding {field}: {e}")
            
            # Add foreign key constraint for approved_by (if it doesn't exist)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN approved_by INTEGER REFERENCES users(id)")
                print("Added approved_by foreign key constraint")
            except sqlite3.Error as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"Note: {e}")
            
            # Commit changes
            conn.commit()
            print("Migration completed successfully!")
            
        else:
            print("All registration fields already exist. No migration needed.")
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(users)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        
        expected_fields = [
            'registration_status', 'registration_timestamp', 'email_verified',
            'email_verification_token', 'email_verification_expires', 'email_verification_attempts',
            'registration_ip_address', 'registration_user_agent', 'approved_by',
            'approved_at', 'rejection_reason', 'registration_attempts', 'last_registration_attempt'
        ]
        
        missing_fields = [field for field in expected_fields if field not in updated_columns]
        if missing_fields:
            print(f"Warning: Missing fields: {missing_fields}")
        else:
            print("All registration fields verified successfully!")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
    
    return True

if __name__ == "__main__":
    print("Starting registration fields migration...")
    success = run_migration()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        exit(1)