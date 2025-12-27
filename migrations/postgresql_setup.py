#!/usr/bin/env python3
"""
PostgreSQL Setup Migration Script for Flask POS Application
Migrates data from SQLite to PostgreSQL and sets up the database
"""

import os
import sys
import shutil
from datetime import datetime

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, validate_database_config, get_database_info
from sqlalchemy import text, create_engine
from sqlalchemy.dialects.postgresql import insert

def backup_sqlite_database():
    """Create backup of SQLite database"""
    sqlite_path = 'instance/restaurant_pos.db'
    if os.path.exists(sqlite_path):
        backup_path = f'instance/restaurant_pos_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy2(sqlite_path, backup_path)
        print(f"SQLite database backed up to: {backup_path}")
        return backup_path
    else:
        print("No SQLite database found to backup")
        return None

def migrate_data_to_postgresql():
    """Migrate data from SQLite to PostgreSQL"""
    print("Starting data migration from SQLite to PostgreSQL...")
    
    # Create source engine for SQLite
    sqlite_engine = create_engine('sqlite:///instance/restaurant_pos.db')
    
    try:
        # Get all table names from source database
        with sqlite_engine.connect() as source_conn:
            source_tables = source_conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)).fetchall()
        
        source_table_names = [table[0] for table in source_tables]
        print(f"Found tables to migrate: {source_table_names}")
        
        # Connect to PostgreSQL destination
        with db.engine.connect() as dest_conn:
            for table_name in source_table_names:
                print(f"Migrating table: {table_name}")
                
                # Get data from SQLite
                with sqlite_engine.connect() as source_conn:
                    result = source_conn.execute(text(f"SELECT * FROM {table_name}"))
                    rows = result.fetchall()
                    columns = result.keys()
                
                if rows:
                    # Insert into PostgreSQL using bulk insert
                    data = [dict(zip(columns, row)) for row in rows]
                    
                    # Convert datetime objects to strings for PostgreSQL
                    for record in data:
                        for key, value in record.items():
                            if isinstance(value, datetime):
                                record[key] = value.isoformat()
                    
                    # Bulk insert using PostgreSQL-specific insert
                    insert_stmt = insert(db.metadata.tables[table_name]).values(data)
                    upsert_stmt = insert_stmt.on_conflict_do_nothing()
                    
                    dest_conn.execute(upsert_stmt)
                    dest_conn.commit()
                    print(f"Migrated {len(data)} records from {table_name}")
                else:
                    print(f"No data to migrate for table: {table_name}")
        
        print("Data migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False

def setup_postgresql_database():
    """Set up PostgreSQL database with proper extensions and configuration"""
    print("Setting up PostgreSQL database...")
    
    app = create_app()
    with app.app_context():
        try:
            # Create extensions
            with db.engine.connect() as connection:
                # Enable UUID extension
                connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                connection.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
                
                # Set timezone
                connection.execute(text("SET timezone = 'UTC'"))
                
                # Configure connection settings for better performance
                connection.execute(text("SET default_with_oids = false"))
                connection.execute(text("SET default_statistics_target = 100"))
                connection.execute(text("SET random_page_cost = 1.1"))
                
                connection.commit()
            
            print("PostgreSQL extensions and configuration applied successfully")
            return True
            
        except Exception as e:
            print(f"Error setting up PostgreSQL: {str(e)}")
            return False

def validate_migration():
    """Validate that migration was successful"""
    print("Validating migration...")
    
    app = create_app()
    with app.app_context():
        try:
            # Check table counts
            with db.engine.connect() as connection:
                tables = [
                    'user', 'category', 'menu_item', 'table', 
                    'order', 'order_item', 'payment', 'settings',
                    'print_history', 'audit_log'
                ]
                
                for table in tables:
                    try:
                        result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.fetchone()[0]
                        print(f"Table {table}: {count} records")
                    except Exception as e:
                        print(f"Warning: Could not count records in {table}: {str(e)}")
            
            print("Migration validation completed")
            return True
            
        except Exception as e:
            print(f"Error during validation: {str(e)}")
            return False

def main():
    """Main migration function"""
    print("=" * 60)
    print("PostgreSQL Migration Tool for Flask POS Application")
    print("=" * 60)
    
    # Check if running with PostgreSQL configuration
    database_type = os.environ.get('DATABASE_TYPE', 'sqlite').lower()
    if database_type != 'postgresql':
        print("ERROR: Please set DATABASE_TYPE=postgresql to run this migration")
        return 1
    
    # Validate PostgreSQL configuration
    app = create_app()
    with app.app_context():
        if not validate_database_config(app):
            print("ERROR: PostgreSQL configuration is invalid!")
            print("Please check your POSTGRES_* environment variables")
            return 1
    
    # Show current database info
    db_info = get_database_info()
    print(f"Current database: {db_info['type']}")
    print(f"Version: {db_info['version']}")
    
    # Confirm migration
    print("\nThis script will:")
    print("1. Backup your SQLite database")
    print("2. Migrate all data to PostgreSQL")
    print("3. Set up PostgreSQL extensions")
    print("4. Validate the migration")
    
    response = input("\nDo you want to proceed? (yes/no): ").lower()
    if response not in ['yes', 'y']:
        print("Migration cancelled")
        return 0
    
    # Step 1: Backup SQLite database
    backup_path = backup_sqlite_database()
    
    # Step 2: Setup PostgreSQL
    if not setup_postgresql_database():
        print("ERROR: Failed to setup PostgreSQL database")
        return 1
    
    # Step 3: Migrate data
    if not migrate_data_to_postgresql():
        print("ERROR: Data migration failed")
        print(f"You can restore from backup: {backup_path}")
        return 1
    
    # Step 4: Validate migration
    if not validate_migration():
        print("WARNING: Migration validation failed")
        print("Please check your data manually")
    
    print("\n" + "=" * 60)
    print("PostgreSQL migration completed successfully!")
    print("Your Flask POS application is now using PostgreSQL")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)