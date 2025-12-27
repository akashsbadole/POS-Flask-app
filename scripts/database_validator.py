#!/usr/bin/env python3
"""
Database Configuration Validator for Flask POS Application
Validates database configuration and connectivity
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import validate_database_config, get_database_info
import sqlalchemy
from sqlalchemy import create_engine, text

def validate_environment_variables():
    """Validate required environment variables"""
    print("Validating environment variables...")
    
    database_type = os.environ.get('DATABASE_TYPE', 'sqlite').lower()
    print(f"Database Type: {database_type}")
    
    validation_results = []
    
    if database_type == 'postgresql':
        required_vars = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB']
        for var in required_vars:
            value = os.environ.get(var)
            if not value:
                validation_results.append(f"ERROR: {var} is not set")
            else:
                validation_results.append(f"✓ {var}: {'*' * len(value)}")
    
    elif database_type == 'sqlite':
        sqlite_path = os.environ.get('SQLITE_DATABASE_PATH', 'restaurant_pos.db')
        validation_results.append(f"✓ SQLite path: {sqlite_path}")
        
        # Check if SQLite file exists
        if not os.path.exists(f"instance/{sqlite_path}"):
            validation_results.append(f"WARNING: SQLite database file not found at instance/{sqlite_path}")
        else:
            validation_results.append(f"✓ SQLite database file exists")
    
    else:
        validation_results.append(f"ERROR: Unknown database type: {database_type}")
    
    return validation_results

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        app = create_app()
        with app.app_context():
            if validate_database_config(app):
                print("✓ Database connection successful")
                return True
            else:
                print("✗ Database connection failed")
                return False
    except Exception as e:
        print(f"✗ Database connection error: {str(e)}")
        return False

def get_database_metadata():
    """Get database metadata and tables"""
    print("\nGetting database metadata...")
    
    try:
        app = create_app()
        with app.app_context():
            # Get database info
            db_info = get_database_info()
            print(f"Database Type: {db_info['type']}")
            print(f"Version: {db_info['version']}")
            print(f"Connection URI: {db_info['uri']}")
            
            # Get table list
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\nDatabase tables ({len(tables)}):")
            for table in tables:
                try:
                    # Get row count for each table
                    result = db.engine.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"  - {table}: {count} rows")
                except Exception as e:
                    print(f"  - {table}: (error counting rows: {str(e)})")
            
            return True
            
    except Exception as e:
        print(f"✗ Error getting metadata: {str(e)}")
        return False

def test_database_operations():
    """Test basic database operations"""
    print("\nTesting database operations...")
    
    try:
        app = create_app()
        with app.app_context():
            from models.user import User
            
            # Test SELECT operation
            user_count = User.query.count()
            print(f"✓ SELECT operation successful: {user_count} users found")
            
            # Test INSERT operation (create test record)
            test_user = User(
                username='test_validation',
                email='test@validation.com',
                first_name='Test',
                last_name='Validation',
                role='test',
                is_active=True
            )
            test_user.set_password('test123')
            
            db.session.add(test_user)
            db.session.commit()
            print("✓ INSERT operation successful")
            
            # Test UPDATE operation
            test_user.first_name = 'Updated Test'
            db.session.commit()
            print("✓ UPDATE operation successful")
            
            # Test DELETE operation
            db.session.delete(test_user)
            db.session.commit()
            print("✓ DELETE operation successful")
            
            print("All database operations completed successfully!")
            return True
            
    except Exception as e:
        print(f"✗ Database operation error: {str(e)}")
        return False

def generate_configuration_report():
    """Generate a comprehensive configuration report"""
    print("\n" + "=" * 60)
    print("DATABASE CONFIGURATION REPORT")
    print("=" * 60)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Environment variables validation
    env_results = validate_environment_variables()
    print("ENVIRONMENT VARIABLES:")
    for result in env_results:
        print(f"  {result}")
    print()
    
    # Connection test
    connection_ok = test_database_connection()
    print()
    
    # Metadata
    if connection_ok:
        get_database_metadata()
        print()
        
        # Operations test
        test_database_operations()
    
    print("\n" + "=" * 60)
    
    if connection_ok:
        print("✓ DATABASE CONFIGURATION IS VALID")
        return 0
    else:
        print("✗ DATABASE CONFIGURATION HAS ISSUES")
        return 1

def main():
    """Main validation function"""
    return generate_configuration_report()

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)