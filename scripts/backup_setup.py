"""
Backup System Setup Script
Initialize and configure the backup system
"""
import os
import sys
from datetime import datetime, timedelta
from flask import Flask
from models import db, init_db, BackupJob, BackupConfiguration, BackupType
from utils.backup_manager import BackupManager
from utils.backup_scheduler import init_backup_scheduler
from utils.backup_monitor import BackupMonitor

def create_default_backup_jobs(app):
    """Create default backup jobs"""
    with app.app_context():
        # Check if jobs already exist
        existing_jobs = BackupJob.query.count()
        if existing_jobs > 0:
            print(f"Found {existing_jobs} existing backup jobs. Skipping default job creation.")
            return
        
        # Daily Full Backup Job
        daily_job = BackupJob(
            name="Daily Full Backup",
            description="Automated daily full system backup",
            backup_type=BackupType.FULL,
            schedule_cron="@daily",
            retention_days=30,
            compression_enabled=True,
            encryption_enabled=True,
            include_logs=False,
            include_user_data=True,
            include_config=True,
            enabled=True
        )
        db.session.add(daily_job)
        
        # Weekly Configuration Backup Job
        weekly_job = BackupJob(
            name="Weekly Configuration Backup",
            description="Weekly backup of configuration and settings",
            backup_type=BackupType.CONFIGURATION,
            schedule_cron="@weekly",
            retention_days=90,
            compression_enabled=True,
            encryption_enabled=True,
            include_logs=False,
            include_user_data=False,
            include_config=True,
            enabled=True
        )
        db.session.add(weekly_job)
        
        # Monthly Database Backup Job
        monthly_job = BackupJob(
            name="Monthly Database Backup",
            description="Monthly archive backup of database",
            backup_type=BackupType.DATABASE,
            schedule_cron="@monthly",
            retention_days=365,
            compression_enabled=True,
            encryption_enabled=True,
            include_logs=False,
            include_user_data=False,
            include_config=False,
            enabled=True
        )
        db.session.add(monthly_job)
        
        db.session.commit()
        print("Created default backup jobs:")
        print("- Daily Full Backup (every day at 2:00 AM)")
        print("- Weekly Configuration Backup (Sunday 2:00 AM)")
        print("- Monthly Database Backup (1st of month at 2:00 AM)")

def setup_backup_directories():
    """Create backup directory structure"""
    directories = [
        'backups',
        'backups/database',
        'backups/configuration',
        'backups/user_data',
        'backups/logs',
        'backups/temp'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

def setup_backup_configuration(app):
    """Setup default backup configuration"""
    with app.app_context():
        # Check if configuration already exists
        existing_configs = BackupConfiguration.query.count()
        if existing_configs > 0:
            print(f"Found {existing_configs} existing backup configurations. Skipping default configuration.")
            return
        
        default_configs = [
            ('backup_location', 'backups/', 'Default backup storage location', 'string'),
            ('max_backup_size_gb', '10', 'Maximum backup file size in GB', 'integer'),
            ('compression_level', '6', 'Compression level (1-9)', 'integer'),
            ('encryption_algorithm', 'AES-256', 'Encryption algorithm to use', 'string'),
            ('auto_cleanup_enabled', 'true', 'Enable automatic cleanup of old backups', 'boolean'),
            ('email_notifications_enabled', 'false', 'Enable email notifications for backup events', 'boolean'),
            ('cloud_storage_enabled', 'false', 'Enable cloud storage integration', 'boolean'),
            ('backup_validation_enabled', 'true', 'Enable backup integrity validation', 'boolean'),
            ('restore_validation_enabled', 'true', 'Enable restore validation', 'boolean'),
            ('alert_thresholds', '{"failed_backups": 3, "storage_usage": 85}', 'Alert threshold configuration', 'json'),
            ('monitoring_enabled', 'true', 'Enable backup system monitoring', 'boolean'),
            ('notification_email', '', 'Email address for notifications', 'string')
        ]
        
        for key, value, description, data_type in default_configs:
            config = BackupConfiguration(
                key=key,
                value=value,
                description=description,
                data_type=data_type
            )
            db.session.add(config)
        
        db.session.commit()
        print("Created default backup configurations")

def test_backup_system(app):
    """Test the backup system setup"""
    print("\nTesting backup system...")
    
    try:
        with app.app_context():
            # Test database connection
            from models import get_database_info
            db_info = get_database_info()
            print(f"Database: {db_info['type']} - {db_info['version']}")
            
            # Test backup manager
            backup_manager = BackupManager(app)
            stats = backup_manager.get_backup_statistics()
            print(f"Backup statistics initialized: {stats['total_backups']} total backups")
            
            # Test scheduler
            scheduler = init_backup_scheduler(app)
            scheduler_status = scheduler.get_scheduler_status()
            print(f"Scheduler initialized: {scheduler_status['total_jobs']} jobs configured")
            
            # Test monitor
            monitor = BackupMonitor(app)
            health = monitor.get_system_health()
            print(f"Monitor initialized: System health status = {health['overall_status']}")
            
        print("✅ Backup system test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Backup system test failed: {str(e)}")
        return False

def create_backup_scripts():
    """Create utility scripts for backup management"""
    
    # Create backup validation script
    validation_script = """#!/usr/bin/env python3
\"\"\"
Backup Validation Script
Validate all backups in the system
\"\"\"
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from models import init_db
from utils.backup_manager import BackupManager

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///restaurant_pos.db')

def validate_all_backups():
    with app.app_context():
        init_db(app)
        backup_manager = BackupManager(app)
        
        from models import BackupRun, BackupStatus
        completed_backups = BackupRun.query.filter_by(status=BackupStatus.COMPLETED).all()
        
        print(f"Validating {len(completed_backups)} backups...")
        
        for backup in completed_backups:
            is_valid = backup_manager.verify_backup_integrity(backup)
            status = "✅ VALID" if is_valid else "❌ INVALID"
            print(f"Backup #{backup.id}: {status}")
            
            if not is_valid:
                print(f"  - File path: {backup.file_path}")
                print(f"  - Expected hash: {backup.file_hash}")
        
        print("Backup validation complete.")

if __name__ == '__main__':
    validate_all_backups()
"""
    
    with open('scripts/validate_backups.py', 'w') as f:
        f.write(validation_script)
    
    # Create cleanup script
    cleanup_script = """#!/usr/bin/env python3
\"\"\"
Backup Cleanup Script
Clean up old backup files and records
\"\"\"
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from models import init_db
from utils.backup_manager import BackupManager

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///restaurant_pos.db')

def cleanup_old_backups():
    with app.app_context():
        init_db(app)
        backup_manager = BackupManager(app)
        
        retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
        cleaned_count = backup_manager.cleanup_old_backups(retention_days)
        
        print(f"Cleaned up {cleaned_count} old backup records (older than {retention_days} days)")

if __name__ == '__main__':
    cleanup_old_backups()
"""
    
    with open('scripts/cleanup_backups.py', 'w') as f:
        f.write(cleanup_script)
    
    print("Created utility scripts:")
    print("- scripts/validate_backups.py")
    print("- scripts/cleanup_backups.py")

def main():
    """Main setup function"""
    print("=" * 60)
    print("BACKUP SYSTEM SETUP")
    print("=" * 60)
    
    # Initialize Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///restaurant_pos.db')
    
    try:
        # Initialize database
        print("\n1. Initializing database...")
        init_db(app)
        print("✅ Database initialized")
        
        # Setup directories
        print("\n2. Setting up backup directories...")
        setup_backup_directories()
        print("✅ Directories created")
        
        # Setup configuration
        print("\n3. Setting up backup configuration...")
        setup_backup_configuration(app)
        print("✅ Configuration setup complete")
        
        # Create default jobs
        print("\n4. Creating default backup jobs...")
        create_default_backup_jobs(app)
        print("✅ Default jobs created")
        
        # Create utility scripts
        print("\n5. Creating utility scripts...")
        create_backup_scripts()
        print("✅ Scripts created")
        
        # Test system
        print("\n6. Testing backup system...")
        if test_backup_system(app):
            print("✅ System test passed")
        else:
            print("❌ System test failed")
        
        print("\n" + "=" * 60)
        print("BACKUP SYSTEM SETUP COMPLETE")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Configure email settings in the backup configuration")
        print("2. Start the backup scheduler in your application")
        print("3. Test a manual backup to ensure everything works")
        print("4. Review and customize the default backup jobs as needed")
        print("\nAccess the backup management interface at: /backup")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()