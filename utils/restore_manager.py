"""
Restore Manager - Restore functionality with validation and safety checks
"""
import os
import json
import shutil
import tarfile
import gzip
import tempfile
import sqlite3
import psycopg2
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from flask import current_app
import subprocess
import re

from models.backup import BackupRun, RestoreOperation, RestoreStatus, BackupType, BackupAlert
from models import db
from utils.encryption import EncryptionManager

class RestoreManager:
    """Restore management functionality with validation"""
    
    def __init__(self, app=None):
        self.app = app
        self.encryption_manager = EncryptionManager()
        self.restore_base_path = Path('restore_temp')
        self.restore_base_path.mkdir(exist_ok=True)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
    
    def restore_backup(self, backup_run: BackupRun, restore_options: Dict[str, Any] = None, 
                      initiated_by: str = None) -> RestoreOperation:
        """Restore a backup with validation and safety checks"""
        restore_operation = RestoreOperation(
            backup_run_id=backup_run.id,
            restore_type=backup_run.backup_type,
            status=RestoreStatus.PENDING,
            restore_options=json.dumps(restore_options or {}),
            initiated_by=initiated_by or 'system',
            total_steps=self._calculate_total_steps(backup_run)
        )
        
        try:
            db.session.add(restore_operation)
            db.session.commit()
            
            # Start restore process
            restore_operation.status = RestoreStatus.IN_PROGRESS
            restore_operation.start_time = datetime.utcnow()
            restore_operation.current_step = "Initializing restore process"
            db.session.commit()
            
            # Create rollback backup if enabled
            if restore_options and restore_options.get('create_rollback_backup', True):
                rollback_backup_id = self._create_rollback_backup(backup_run)
                restore_operation.rollback_backup_id = rollback_backup_id
            
            # Decrypt backup if encrypted
            backup_path = Path(backup_run.file_path)
            if backup_path.suffix == '.encrypted':
                decrypted_path = self._decrypt_backup(backup_path, backup_run)
                backup_path = decrypted_path
            
            # Validate backup integrity
            restore_operation.current_step = "Validating backup integrity"
            restore_operation.completed_steps = 1
            db.session.commit()
            
            if not self._validate_backup_integrity(backup_path, backup_run):
                raise Exception("Backup integrity validation failed")
            
            # Extract backup archive
            restore_operation.current_step = "Extracting backup archive"
            restore_operation.completed_steps = 2
            db.session.commit()
            
            extracted_path = self._extract_backup_archive(backup_path)
            
            # Validate backup contents
            restore_operation.current_step = "Validating backup contents"
            restore_operation.completed_steps = 3
            db.session.commit()
            
            if not self._validate_backup_contents(extracted_path):
                raise Exception("Backup content validation failed")
            
            # Perform restore operations
            restore_operation.current_step = "Performing restore operations"
            restore_operation.completed_steps = 4
            db.session.commit()
            
            self._perform_restore_operations(extracted_path, restore_operation, restore_options)
            
            # Validate restore
            restore_operation.current_step = "Validating restore"
            restore_operation.status = RestoreStatus.VALIDATING
            restore_operation.completed_steps = restore_operation.total_steps - 1
            db.session.commit()
            
            if not self._validate_restore_success(extracted_path):
                raise Exception("Restore validation failed")
            
            # Complete restore
            restore_operation.status = RestoreStatus.COMPLETED
            restore_operation.completed_steps = restore_operation.total_steps
            restore_operation.end_time = datetime.utcnow()
            restore_operation.duration_seconds = int((restore_operation.end_time - restore_operation.start_time).total_seconds())
            restore_operation.success_message = "Restore completed successfully"
            
            # Update backup run restore count
            backup_run.restore_count += 1
            backup_run.last_restored_at = datetime.utcnow()
            
            # Create success alert
            self._create_alert('success', 'medium', 'Restore Completed', 
                             f'Restore operation {restore_operation.id} completed successfully')
            
        except Exception as e:
            restore_operation.status = RestoreStatus.FAILED
            restore_operation.end_time = datetime.utcnow()
            restore_operation.duration_seconds = int((datetime.utcnow() - restore_operation.start_time).total_seconds())
            restore_operation.error_message = str(e)
            restore_operation.current_step = "Restore failed"
            
            # Create failure alert
            self._create_alert('failure', 'critical', 'Restore Failed', 
                             f'Restore operation {restore_operation.id} failed: {str(e)}')
            
            raise
        
        finally:
            # Cleanup temporary files
            self._cleanup_restore_files()
            db.session.commit()
        
        return restore_operation
    
    def _calculate_total_steps(self, backup_run: BackupRun) -> int:
        """Calculate total steps for restore process"""
        # Base steps: initialization, integrity validation, content validation, validation
        base_steps = 4
        
        # Add steps based on components in backup
        if backup_run.components_backed_up:
            components = json.loads(backup_run.components_backed_up)
            base_steps += len(components)
        
        return base_steps
    
    def _create_rollback_backup(self, backup_run: BackupRun) -> Optional[int]:
        """Create a rollback backup before restore"""
        try:
            from utils.backup_manager import BackupManager
            
            backup_manager = BackupManager(self.app)
            
            # Create a simple rollback backup job
            rollback_job = BackupJob(
                name=f"Rollback backup for restore {backup_run.id}",
                description=f"Automatic rollback backup created before restore operation",
                backup_type=BackupType.FULL,
                enabled=False,  # Don't schedule rollback backups
                include_logs=False,  # Skip logs for rollback
                include_user_data=True,
                include_config=True
            )
            
            db.session.add(rollback_job)
            db.session.commit()
            
            # Create the actual rollback backup
            rollback_backup_run = backup_manager.create_backup(rollback_job, 'system')
            
            return rollback_backup_run.id
            
        except Exception:
            # If rollback backup fails, continue without it
            return None
    
    def _decrypt_backup(self, encrypted_path: Path, backup_run: BackupRun) -> Path:
        """Decrypt encrypted backup file"""
        key_path = encrypted_path.with_suffix('.key')
        
        if not key_path.exists():
            raise Exception("Encryption key file not found")
        
        # Read encryption key
        with open(key_path, 'rb') as f:
            encryption_key = f.read()
        
        # Decrypt the backup file
        decrypted_path = self.restore_base_path / f"decrypted_backup_{backup_run.id}.tar"
        
        with open(encrypted_path, 'rb') as f_in:
            with open(decrypted_path, 'wb') as f_out:
                decrypted_data = self.encryption_manager.decrypt_data(f_in.read(), encryption_key)
                f_out.write(decrypted_data)
        
        return decrypted_path
    
    def _validate_backup_integrity(self, backup_path: Path, backup_run: BackupRun) -> bool:
        """Validate backup file integrity using hash"""
        try:
            if not backup_path.exists():
                return False
            
            # Calculate current hash
            sha256_hash = hashlib.sha256()
            with open(backup_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            current_hash = sha256_hash.hexdigest()
            
            return current_hash == backup_run.file_hash
        except Exception:
            return False
    
    def _extract_backup_archive(self, backup_path: Path) -> Path:
        """Extract backup archive to temporary location"""
        extract_path = self.restore_base_path / f"extracted_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        extract_path.mkdir(exist_ok=True)
        
        try:
            if backup_path.suffix == '.gz':
                with tarfile.open(backup_path, 'r:gz') as tar:
                    tar.extractall(extract_path)
            elif backup_path.suffix == '.tar':
                with tarfile.open(backup_path, 'r') as tar:
                    tar.extractall(extract_path)
            else:
                raise Exception(f"Unsupported archive format: {backup_path.suffix}")
        except Exception as e:
            shutil.rmtree(extract_path, ignore_errors=True)
            raise Exception(f"Failed to extract backup archive: {str(e)}")
        
        return extract_path
    
    def _validate_backup_contents(self, extract_path: Path) -> bool:
        """Validate that backup contains expected components"""
        required_components = ['database', 'configuration']
        optional_components = ['user_data', 'logs']
        
        # Check for required components
        for component in required_components:
            component_path = extract_path / component
            if not component_path.exists():
                raise Exception(f"Required component '{component}' not found in backup")
        
        # Validate database backup
        database_path = extract_path / 'database'
        if (database_path / 'restaurant_pos.db').exists() or (database_path / 'backup.sql').exists():
            # Database file present
            pass
        else:
            raise Exception("No database backup found in backup archive")
        
        # Validate configuration backup
        config_path = extract_path / 'configuration'
        if not any(config_path.glob('*.json')) and not any(config_path.glob('*.key')):
            # Allow backups without configuration files if they don't exist in original
            pass
        
        return True
    
    def _perform_restore_operations(self, extract_path: Path, restore_operation: RestoreOperation, 
                                  restore_options: Dict[str, Any]):
        """Perform the actual restore operations"""
        components = json.loads(restore_operation.backup_run.components_backed_up) if restore_operation.backup_run.components_backed_up else []
        
        step_counter = 5  # Starting step after validation
        
        for component in components:
            restore_operation.current_step = f"Restoring {component}"
            restore_operation.completed_steps = step_counter
            db.session.commit()
            
            try:
                if component == 'database':
                    self._restore_database(extract_path / 'database', restore_options)
                elif component == 'configuration':
                    self._restore_configuration(extract_path / 'configuration', restore_options)
                elif component == 'user_data':
                    self._restore_user_data(extract_path / 'user_data', restore_options)
                elif component == 'logs':
                    self._restore_logs(extract_path / 'logs', restore_options)
                
                step_counter += 1
                
            except Exception as e:
                restore_operation.warning_message = f"Warning during {component} restore: {str(e)}"
                # Continue with other components even if one fails
    
    def _restore_database(self, database_path: Path, restore_options: Dict[str, Any]):
        """Restore database from backup"""
        with self.app.app_context():
            from models import get_database_info
            
            db_info = get_database_info()
            
            # Check if database should be backed up before restore
            if restore_options and restore_options.get('backup_before_restore', True):
                self._backup_current_database()
            
            if db_info['type'] == 'SQLite':
                self._restore_sqlite_database(database_path, restore_options)
            elif db_info['type'] == 'PostgreSQL':
                self._restore_postgresql_database(database_path, restore_options)
            else:
                raise Exception(f"Unsupported database type: {db_info['type']}")
    
    def _backup_current_database(self):
        """Backup current database before restore"""
        try:
            with self.app.app_context():
                from models import get_database_info
                
                db_info = get_database_info()
                backup_name = f"pre_restore_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                
                if db_info['type'] == 'SQLite':
                    db_path = db_info['uri'].replace('sqlite:///', '')
                    backup_path = Path(f"backups/{backup_name}.db")
                    shutil.copy2(db_path, backup_path)
                elif db_info['type'] == 'PostgreSQL':
                    # For PostgreSQL, create a backup using pg_dump
                    self._create_postgresql_backup(backup_name)
                    
        except Exception as e:
            # Log warning but continue with restore
            print(f"Warning: Could not create pre-restore backup: {str(e)}")
    
    def _restore_sqlite_database(self, database_path: Path, restore_options: Dict[str, Any]):
        """Restore SQLite database"""
        db_file = database_path / 'restaurant_pos.db'
        if not db_file.exists():
            raise Exception("SQLite database file not found in backup")
        
        with self.app.app_context():
            from models import get_database_info
            db_info = get_database_info()
            current_db_path = db_info['uri'].replace('sqlite:///', '')
            
            # Close database connections
            db.engine.dispose()
            
            # Restore the database
            shutil.copy2(str(db_file), current_db_path)
    
    def _restore_postgresql_database(self, database_path: Path, restore_options: Dict[str, Any]):
        """Restore PostgreSQL database"""
        sql_file = database_path / 'backup.sql'
        if not sql_file.exists():
            raise Exception("PostgreSQL backup file not found in backup")
        
        # Parse connection info from metadata or config
        # This is a simplified implementation - you might want to store connection info in backup
        uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        
        if uri.startswith('postgresql://'):
            # Extract connection parameters
            parts = uri.replace('postgresql://', '').split('@')
            auth_part = parts[0]
            host_part = parts[1] if len(parts) > 1 else 'localhost'
            
            if ':' in auth_part:
                user_pass = auth_part.split(':')
                user = user_pass[0]
                password = user_pass[1] if len(user_pass) > 1 else ''
            else:
                user = auth_part
                password = ''
            
            if '/' in host_part:
                host_db = host_part.split('/')
                host = host_db[0]
                database = host_db[1]
                if ':' in host:
                    host = host.split(':')[0]
            else:
                host = host_part
                database = 'postgres'
            
            # Set environment variables for psql
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Restore using psql
            cmd = [
                'psql',
                '-h', host,
                '-U', user,
                '-d', database,
                '-f', str(sql_file),
                '--quiet'
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"psql restore failed: {result.stderr}")
    
    def _create_postgresql_backup(self, backup_name: str):
        """Create PostgreSQL backup"""
        uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        
        if uri.startswith('postgresql://'):
            # Extract connection parameters (similar to above)
            parts = uri.replace('postgresql://', '').split('@')
            auth_part = parts[0]
            host_part = parts[1] if len(parts) > 1 else 'localhost'
            
            if ':' in auth_part:
                user_pass = auth_part.split(':')
                user = user_pass[0]
                password = user_pass[1] if len(user_pass) > 1 else ''
            else:
                user = auth_part
                password = ''
            
            if '/' in host_part:
                host_db = host_part.split('/')
                host = host_db[0]
                database = host_db[1]
                if ':' in host:
                    host = host.split(':')[0]
            else:
                host = host_part
                database = 'postgres'
            
            # Set environment variables for pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            backup_path = Path(f"backups/{backup_name}.sql")
            
            cmd = [
                'pg_dump',
                '-h', host,
                '-U', user,
                '-d', database,
                '-f', str(backup_path),
                '--verbose'
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
    
    def _restore_configuration(self, config_path: Path, restore_options: Dict[str, Any]):
        """Restore configuration files"""
        if not config_path.exists():
            return
        
        # Restore configuration files
        for file_path in config_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(config_path)
                target_path = Path(relative_path)
                
                # Create directory if needed
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Check if file should be restored (avoid overwriting critical files)
                if self._should_restore_config_file(str(target_path), restore_options):
                    shutil.copy2(str(file_path), str(target_path))
    
    def _should_restore_config_file(self, file_path: str, restore_options: Dict[str, Any]) -> bool:
        """Check if a configuration file should be restored"""
        # Never restore critical system files
        critical_files = ['app.py', 'config.py', 'requirements.txt']
        if any(critical in file_path for critical in critical_files):
            return False
        
        # Allow restoration of application config files
        config_patterns = ['config/', 'backups/settings/', 'instance/', 'email_config.json']
        return any(pattern in file_path for pattern in config_patterns)
    
    def _restore_user_data(self, user_data_path: Path, restore_options: Dict[str, Any]):
        """Restore user data and application files"""
        if not user_data_path.exists():
            return
        
        for file_path in user_data_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(user_data_path)
                target_path = Path(relative_path)
                
                # Create directory if needed
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Backup existing file if it exists
                if target_path.exists() and restore_options and restore_options.get('backup_existing_files', True):
                    backup_path = target_path.with_suffix(target_path.suffix + '.backup')
                    shutil.copy2(str(target_path), str(backup_path))
                
                shutil.copy2(str(file_path), str(target_path))
    
    def _restore_logs(self, logs_path: Path, restore_options: Dict[str, Any]):
        """Restore log files (optional - usually not recommended)"""
        if not logs_path.exists():
            return
        
        # Logs are typically not restored in production environments
        # This is mainly for development/testing purposes
        if restore_options and restore_options.get('restore_logs', False):
            for file_path in logs_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(logs_path)
                    target_path = Path('logs') / relative_path
                    
                    # Create directory if needed
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Append logs to existing files or create new ones
                    if target_path.exists():
                        # Append to existing log file
                        with open(file_path, 'r') as f_source:
                            with open(target_path, 'a') as f_target:
                                f_target.write('\n--- RESTORED LOG START ---\n')
                                f_target.write(f_source.read())
                                f_target.write('\n--- RESTORED LOG END ---\n')
                    else:
                        shutil.copy2(str(file_path), str(target_path))
    
    def _validate_restore_success(self, extract_path: Path) -> bool:
        """Validate that restore was successful"""
        try:
            # Check database connectivity
            with self.app.app_context():
                from sqlalchemy import text
                with db.engine.connect() as connection:
                    result = connection.execute(text('SELECT 1'))
                    return result.fetchone()[0] == 1
        except Exception:
            return False
    
    def _cleanup_restore_files(self):
        """Clean up temporary restore files"""
        try:
            shutil.rmtree(self.restore_base_path, ignore_errors=True)
            self.restore_base_path.mkdir(exist_ok=True)
        except Exception:
            pass
    
    def _create_alert(self, alert_type: str, severity: str, title: str, message: str, 
                     restore_operation_id: int = None):
        """Create restore alert"""
        alert = BackupAlert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            restore_operation_id=restore_operation_id,
            backup_run_id=self.backup_run_id if hasattr(self, 'backup_run_id') else None
        )
        db.session.add(alert)
    
    def get_restore_statistics(self) -> Dict[str, Any]:
        """Get restore system statistics"""
        total_restores = RestoreOperation.query.count()
        successful_restores = RestoreOperation.query.filter_by(status=RestoreStatus.COMPLETED).count()
        failed_restores = RestoreOperation.query.filter_by(status=RestoreStatus.FAILED).count()
        
        recent_restores = RestoreOperation.query.filter(
            RestoreOperation.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        return {
            'total_restores': total_restores,
            'successful_restores': successful_restores,
            'failed_restores': failed_restores,
            'success_rate': (successful_restores / total_restores * 100) if total_restores > 0 else 0,
            'recent_restores_7_days': recent_restores
        }
    
    def emergency_restore(self, backup_run: BackupRun, initiated_by: str = None) -> RestoreOperation:
        """Emergency restore with minimal validation"""
        restore_options = {
            'backup_before_restore': False,
            'restore_logs': False,
            'validation_level': 'minimal'
        }
        
        return self.restore_backup(backup_run, restore_options, initiated_by)

def get_restore_manager(app=None) -> RestoreManager:
    """Get restore manager instance"""
    if not hasattr(g, 'restore_manager'):
        g.restore_manager = RestoreManager(app)
    return g.restore_manager