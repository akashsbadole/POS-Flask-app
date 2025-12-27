# PostgreSQL Setup Guide for Flask POS Application

This guide explains how to configure and migrate your Flask POS application from SQLite to PostgreSQL.

## Overview

The Flask POS application now supports both SQLite and PostgreSQL databases. The system can automatically detect and configure the appropriate database based on environment variables.

## Configuration

### Environment Variables

Set these environment variables to configure your database:

#### For SQLite (Default)
```bash
# Optional - defaults to 'restaurant_pos.db'
DATABASE_TYPE=sqlite
SQLITE_DATABASE_PATH=restaurant_pos.db
```

#### For PostgreSQL
```bash
# Required - set to 'postgresql'
DATABASE_TYPE=postgresql

# PostgreSQL connection settings
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=restaurant_pos

# Optional SQLite settings (ignored for PostgreSQL)
SQLITE_DATABASE_PATH=restaurant_pos.db
```

### Configuration Priority

1. If `DATABASE_TYPE=postgresql`, PostgreSQL is used
2. If `DATABASE_TYPE=sqlite` or not set, SQLite is used
3. Database URI can also be set directly via `DATABASE_URL` environment variable

## Installation

### 1. Install Dependencies

Install the required PostgreSQL dependencies:

```bash
pip install psycopg2-binary Flask-Migrate
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. PostgreSQL Setup

Ensure PostgreSQL is installed and running on your system. Create the database:

```sql
CREATE DATABASE restaurant_pos;
CREATE USER pos_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE restaurant_pos TO pos_user;
```

### 3. Set Environment Variables

Create a `.env` file in your project root:

```bash
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=pos_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=restaurant_pos
```

## Usage

### Initialize Database with PostgreSQL

```bash
# Set environment variables
export DATABASE_TYPE=postgresql
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=pos_user
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=restaurant_pos

# Initialize database
python init_db.py
```

### Validate Database Configuration

Run the database validator to check your configuration:

```bash
python scripts/database_validator.py
```

This script will:
- Validate environment variables
- Test database connectivity
- Check table structure
- Test basic database operations

### Migrate from SQLite to PostgreSQL

If you have existing data in SQLite and want to migrate to PostgreSQL:

```bash
# 1. Set PostgreSQL environment variables
export DATABASE_TYPE=postgresql
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=pos_user
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=restaurant_pos

# 2. Run migration script
python migrations/postgresql_setup.py
```

The migration script will:
1. Backup your SQLite database
2. Create PostgreSQL extensions (uuid-ossp, pgcrypto)
3. Migrate all data to PostgreSQL
4. Validate the migration
5. Display results

## Features

### Automatic Database Detection

The application automatically detects the database type and configures itself accordingly:

```python
from config import Config
print(Config().SQLALCHEMY_DATABASE_URI)
# Output: postgresql://user:pass@localhost:5432/restaurant_pos
# OR
# Output: sqlite:///restaurant_pos.db
```

### Database Information

Get database information at runtime:

```python
from models import get_database_info
info = get_database_info()
print(f"Database: {info['type']}")
print(f"Version: {info['version']}")
```

### Validation

Validate database configuration:

```python
from models import validate_database_config
from app import create_app

app = create_app()
if validate_database_config(app):
    print("Database is properly configured")
else:
    print("Database configuration error")
```

## Migration Scripts

### PostgreSQL Setup Migration

Location: `migrations/postgresql_setup.py`

Usage:
```bash
python migrations/postgresql_setup.py
```

Features:
- Automatic SQLite backup
- PostgreSQL extension creation
- Data migration with error handling
- Migration validation

### Database Validator

Location: `scripts/database_validator.py`

Usage:
```bash
python scripts/database_validator.py
```

Features:
- Environment variable validation
- Connection testing
- Table and data verification
- Operation testing (SELECT, INSERT, UPDATE, DELETE)

## Backward Compatibility

The system maintains full backward compatibility:

- SQLite is still the default database
- Existing code continues to work unchanged
- Environment variables are optional (fallbacks provided)
- Database initialization works with both types

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Error**
   - Check PostgreSQL is running
   - Verify connection parameters
   - Ensure database exists

2. **Import Error**
   - Install dependencies: `pip install psycopg2-binary`
   - Check Python path configuration

3. **Permission Error**
   - Ensure PostgreSQL user has database privileges
   - Check file permissions for SQLite

### Debug Mode

Enable debug mode to see SQL queries:

```python
app.config['SQLALCHEMY_ECHO'] = True
```

### Logs

Check application logs for detailed error information.

## Production Deployment

For production deployment with PostgreSQL:

1. Use environment variables for all database settings
2. Enable SSL connections if required
3. Configure connection pooling
4. Set appropriate PostgreSQL configurations
5. Use secure passwords and restrict access
6. Enable database backups

Example production configuration:

```bash
DATABASE_TYPE=postgresql
POSTGRES_HOST=your-production-host
POSTGRES_PORT=5432
POSTGRES_USER=pos_production
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=restaurant_pos_prod
POSTGRES_SSL_MODE=require
```

## API Reference

### New Functions in models/__init__.py

- `init_db(app)` - Initialize database with Flask app
- `validate_database_config(app)` - Validate database configuration
- `get_database_info()` - Get database information and version

### Updated init_db.py

- Database type detection
- PostgreSQL extension setup
- Enhanced error handling
- Configuration validation

## File Changes Summary

Modified files:
- `config.py` - Added PostgreSQL configuration
- `models/__init__.py` - Enhanced database utilities
- `init_db.py` - PostgreSQL support and validation
- `requirements.txt` - Added PostgreSQL dependencies

New files:
- `migrations/postgresql_setup.py` - Migration script
- `scripts/database_validator.py` - Configuration validator
- `POSTGRESQL_SETUP_GUIDE.md` - This documentation

## Support

For issues or questions:
1. Check this documentation
2. Run the database validator
3. Review application logs
4. Check PostgreSQL logs for database-specific issues