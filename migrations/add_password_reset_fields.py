"""
Migration to add password reset functionality fields to users table
"""

import sqlite3
import os
from datetime import datetime, timedelta
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User
from models import db

def migrate():
    """Add password reset fields to users table"""
    try:
        # Check if migration already applied
        db_path = os.path.join('instance', 'restaurant_pos.db')
        if not os.path.exists(db_path):
            print("Database not found. Please run init_db.py first.")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add password_reset_token column
        if 'password_reset_token' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(255)")
            print("[+] Added password_reset_token column")
        else:
            print("[+] password_reset_token column already exists")
        
        # Add password_reset_expires column
        if 'password_reset_expires' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_reset_expires DATETIME")
            print("[+] Added password_reset_expires column")
        else:
            print("[+] password_reset_expires column already exists")
        
        # Add password_reset_attempts column
        if 'password_reset_attempts' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_reset_attempts INTEGER DEFAULT 0")
            print("[+] Added password_reset_attempts column")
        else:
            print("[+] password_reset_attempts column already exists")
        
        # Add password_reset_last_request column
        if 'password_reset_last_request' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_reset_last_request DATETIME")
            print("[+] Added password_reset_last_request column")
        else:
            print("[+] password_reset_last_request column already exists")
        
        conn.commit()
        conn.close()
        
        print("[+] Password reset migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"[!] Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    migrate()