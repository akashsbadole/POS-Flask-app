"""
Backup Manager - Core backup functionality for the POS system
"""
import os
import json
import sqlite3
import shutil
import tarfile
import gzip
import hashlib
import subprocess
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from flask import current_app
from sqlalchemy import text
import tempfile
import zipfile

from models.backup import BackupJob, BackupRun, BackupStatus, BackupType, BackupAlert
from models import db
from utils.encryption import EncryptionManager

class BackupManager:
    """Core backup management functionality"""
    
    def __init__(self, app=None):
        self.app = app
        self.encryption_manager = EncryptionManager()
        self.backup_base_path = Path('backups')
        self.backup_base_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.backup_base_path / 'database').mkdir(exist_ok=True)
        (self.backup_base_path / 'configuration').mkdir(exist_ok=True)
        (self.backup_base_path / 'user_data').mkdir(exist_ok=True)
        (self.backup_base_path / 'logs').mkdir(exist_ok=True)
        (self.backup_base_path / 'temp').mkdir(exist_ok=True)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
    
    def create_backup(self, job: BackupJob, user_id: str = None) -> BackupRun:
        """Create a backup based on job configuration"""
        backup_run = BackupRun(
            job_id=job.id,
            backup_type=job.backup_type,
            status=BackupStatus.IN_PROGRESS,
            start_time=datetime.utcnow()
        )
        
        try:
            db.session.add(backup_run)
            db.session.commit()
            
            # Prepare backup components
            components = self._prepare_backup_components(job)
            backup_run.components_backed_up = json.dumps(components)
            
            # Create backup archive
            backup_file_path = self._create_backup_archive(backup_run, job, components)
            
            # Update backup run with results
            backup_run.file_path = str(backup_file_path)
            backup_run.file_size = backup_file_path.stat().st_size
            
            # Calculate file hash for integrity verification
            backup_run.file_hash = self._calculate_file_hash(backup_file_path)
            
            # Update job's last run time
            job.last_run = datetime.utcnow()
            job.next_run = self._calculate_next_run(job.schedule_cron)
            
            backup_run.status = BackupStatus.COMPLETED
            backup_run.end_time = datetime.utcnow()
            backup_run.duration_seconds = int((backup_run.end_time - backup_run.start_time).total_seconds())
            
            # Create success alert
            self._create_alert('success', 'low', 'Backup Completed', 
                             f'Backup job "{job.name}" completed successfully', backup_run_id=backup_run.id)
            
        except Exception as e:
            backup_run.status = BackupStatus.FAILED
            backup_run.error_message = str(e)
            backup_run.end_time = datetime.utcnow()
            backup_run.duration_seconds = int((backup_run.end_time - backup_run.start_time).total_seconds())
            
            # Create failure alert
            self._create_alert('failure', 'high', 'Backup Failed', 
                             f'Backup job "{job.name}" failed: {str(e)}', backup_run_id=backup_run.id)
            
            raise
        
        finally:
            db.session.commit()
        
        return backup_run
    
    def _prepare_backup_components(self, job: BackupJob) -> List[str]:
        """Prepare components to be backed up"""
        components = []
        
        # Database backup
        if job.backup_type in [BackupType.FULL, BackupType.DATABASE]:
            components.append('database')
        
        # Configuration files
        if job.include_config and job.backup_type in [BackupType.FULL, BackupType.CONFIGURATION]:
            components.append('configuration')
        
        # User data
        if job.include_user_data and job.backup_type in [BackupType.FULL, BackupType.USER_DATA]:
            components.append('user_data')
        
        # Log files
        if job.include_logs and job.backup_type in [BackupType.FULL, BackupType.LOGS]:
            components.append('logs')
        
        return components
    
    def _create_backup_archive(self, backup_run: BackupRun, job: BackupJob, components: List[str]) -> Path:
        """Create the actual backup archive"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        archive_name = f"backup_{backup_run.id}_{timestamp}"
        
        if job.compression_enabled:
            archive_path = self.backup_base_path / f"{archive_name}.tar.gz"
            archive_mode = 'w:gz'
        else:
            archive_path = self.backup_base_path / f"{archive_name}.tar"
            archive_mode = 'w'
        
        with tarfile.open(archive_path, archive_mode) as tar:
            for component in components:
                if component == 'database':
                    self._backup_database_to_archive(tar, job)
                elif component == 'configuration':
                    self._backup_configuration_to_archive(tar, job)
                elif component == 'user_data':
                    self._backup_user_data_to_archive(tar, job)
                elif component == 'logs':
                    self._backup_logs_to_archive(tar, job)
        
        # Encrypt if enabled
        if job.encryption_enabled:
            encrypted_path = self._encrypt_backup(archive_path, job)
            archive_path.unlink()  # Remove unencrypted version
            return encrypted_path
        
        return archive_path
    
    def _backup_database_to_archive(self, tar: tarfile.TarFile, job: BackupJob):
        """Backup database to archive"""
        with self.app.app_context():
            from models import get_database_info
            
            db_info = get_database_info()
            
            if db_info['type'] == 'SQLite':
                self._backup_sqlite_database(tar, db_info)
            elif db_info['type'] == 'PostgreSQL':
                self._backup_postgresql_database(tar, db_info)
            else:
                raise Exception(f"Unsupported database type: {db_info['type']}")
    
    def _backup_sqlite_database(self, tar: tarfile.TarFile, db_info: Dict):
        """Backup SQLite database"""
        db_path = db_info['uri'].replace('sqlite:///', '')
        
        # Create temporary backup to ensure consistency
        with tempfile.NamedTemporaryFile(delete=False) as temp_db:
            shutil.copy2(db_path, temp_db.name)
            tar.add(temp_db.name, arcname='database/restaurant_pos.db')
            os.unlink(temp_db.name)
        
        # Add database metadata
        metadata = {
            'type': 'SQLite',
            'backup_timestamp': datetime.utcnow().isoformat(),
            'original_path': db_path,
            'file_size': os.path.getsize(db_path)
        }
        
        tar.addfile('database/metadata.json', json.dumps(metadata))
    
    def _backup_postgresql_database(self, tar: tarfile.TarFile, db_info: Dict):
        """Backup PostgreSQL database using pg_dump"""
        try:
            # Parse database connection info
            uri = db_info['uri']
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
            else:
                raise Exception("Could not parse PostgreSQL connection string")
            
            # Set environment variables for pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Create temporary file for SQL dump
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_sql:
                temp_sql_path = temp_sql.name
            
            # Run pg_dump
            cmd = [
                'pg_dump',
                '-h', host,
                '-U', user,
                '-d', database,
                '-f', temp_sql_path,
                '--verbose',
                '--clean',
                '--if-exists'
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Add SQL dump to archive
            tar.add(temp_sql_path, arcname='database/backup.sql')
            os.unlink(temp_sql_path)
            
            # Add database metadata
            metadata = {
                'type': 'PostgreSQL',
                'backup_timestamp': datetime.utcnow().isoformat(),
                'connection_string': db_info['uri'],
                'pg_dump_version': result.stdout.split('\n')[0] if result.stdout else 'Unknown',
                'file_size': os.path.getsize(temp_sql_path) if os.path.exists(temp_sql_path) else 0
            }
            
            tar.addfile('database/metadata.json', json.dumps(metadata))
            
        except Exception as e:
            # Fallback: try to backup configuration files only
            raise Exception(f"PostgreSQL backup failed: {str(e)}")
    
    def _backup_configuration_to_archive(self, tar: tarfile.TarFile, job: BackupJob):
        """Backup configuration files"""
        config_dirs = [
            'config/',
            'backups/settings/',
            'instance/',
            'email_config.json',
            'config/encryption.key'
        ]
        
        for config_path in config_dirs:
            full_path = Path(config_path)
            if full_path.exists():
                if full_path.is_file():
                    tar.add(str(full_path), arcname=f'configuration/{config_path}')
                elif full_path.is_dir():
                    for file_path in full_path.rglob('*'):
                        if file_path.is_file():
                            arcname = f'configuration/{file_path}'
                            tar.add(str(file_path), arcname=arcname)
        
        # Add configuration metadata
        metadata = {
            'backup_timestamp': datetime.utcnow().isoformat(),
            'configuration_files': [item.name for item in Path('config').glob('*') if item.is_file()],
            'encryption_key_exists': os.path.exists('config/encryption.key')
        }
        
        tar.addfile('configuration/metadata.json', json.dumps(metadata))
    
    def _backup_user_data_to_archive(self, tar: tarfile.TarFile, job: BackupJob):
        """Backup user data and application files"""
        user_data_paths = [
            'static/uploads/',
            'cache/cache_metadata.db',
            'migrations/',
            'scripts/'
        ]
        
        for data_path in user_data_paths:
            full_path = Path(data_path)
            if full_path.exists():
                if full_path.is_file():
                    tar.add(str(full_path), arcname=f'user_data/{data_path}')
                elif full_path.is_dir():
                    for file_path in full_path.rglob('*'):
                        if file_path.is_file():
                            arcname = f'user_data/{file_path}'
                            tar.add(str(file_path), arcname=arcname)
        
        # Add user data metadata
        metadata = {
            'backup_timestamp': datetime.utcnow().isoformat(),
            'user_data_paths': user_data_paths,
            'total_files': len(list(Path('static/uploads').rglob('*'))) if Path('static/uploads').exists() else 0
        }
        
        tar.addfile('user_data/metadata.json', json.dumps(metadata))
    
    def _backup_logs_to_archive(self, tar: tarfile.TarFile, job: BackupJob):
        """Backup log files"""
        logs_path = Path('logs')
        if logs_path.exists():
            for log_file in logs_path.rglob('*.log'):
                if log_file.is_file():
                    # Compress large log files
                    if log_file.stat().st_size > 1024 * 1024:  # 1MB
                        compressed_path = self._compress_file(log_file)
                        tar.add(str(compressed_path), arcname=f'logs/{log_file.name}.gz')
                        compressed_path.unlink()
                    else:
                        tar.add(str(log_file), arcname=f'logs/{log_file.name}')
        
        # Add logs metadata
        metadata = {
            'backup_timestamp': datetime.utcnow().isoformat(),
            'log_files': [str(log_file) for log_file in logs_path.rglob('*.log')] if logs_path.exists() else []
        }
        
        tar.addfile('logs/metadata.json', json.dumps(metadata))
    
    def _compress_file(self, file_path: Path) -> Path:
        """Compress a single file"""
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return compressed_path
    
    def _encrypt_backup(self, backup_path: Path, job: BackupJob) -> Path:
        """Encrypt backup file"""
        encrypted_path = backup_path.with_suffix(backup_path.suffix + '.encrypted')
        
        # Generate encryption key
        encryption_key = self.encryption_manager.generate_key()
        
        # Encrypt the file
        with open(backup_path, 'rb') as f_in:
            with open(encrypted_path, 'wb') as f_out:
                encrypted_data = self.encryption_manager.encrypt_data(f_in.read(), encryption_key)
                f_out.write(encrypted_data)
        
        # Store encryption key securely (you might want to store this in a secure location)
        key_path = encrypted_path.with_suffix('.key')
        with open(key_path, 'wb') as f:
            f.write(encryption_key)
        
        return encrypted_path
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _calculate_next_run(self, cron_expression: str) -> Optional[datetime]:
        """Calculate next run time based on cron expression"""
        # Simple implementation - you might want to use a proper cron library
        # For now, return daily backup as default
        if cron_expression:
            return datetime.utcnow() + timedelta(days=1)
        return None
    
    def _create_alert(self, alert_type: str, severity: str, title: str, message: str, 
                     backup_run_id: int = None, backup_job_id: int = None):
        """Create backup alert"""
        alert = BackupAlert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            backup_run_id=backup_run_id,
            backup_job_id=backup_job_id
        )
        db.session.add(alert)
    
    def verify_backup_integrity(self, backup_run: BackupRun) -> bool:
        """Verify backup integrity using hash comparison"""
        try:
            backup_path = Path(backup_run.file_path)
            if not backup_path.exists():
                return False
            
            current_hash = self._calculate_file_hash(backup_path)
            return current_hash == backup_run.file_hash
        except Exception:
            return False
    
    def cleanup_old_backups(self, retention_days: int = 30):
        """Clean up old backup files"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Clean up old backup runs from database
        old_runs = BackupRun.query.filter(
            BackupRun.created_at < cutoff_date,
            BackupRun.status == BackupStatus.COMPLETED
        ).all()
        
        for run in old_runs:
            # Remove backup file
            if run.file_path and Path(run.file_path).exists():
                try:
                    Path(run.file_path).unlink()
                except Exception:
                    pass  # Continue cleanup even if file removal fails
            
            # Remove associated files (encryption keys, etc.)
            backup_path = Path(run.file_path)
            if backup_path.exists():
                key_path = backup_path.with_suffix('.key')
                if key_path.exists():
                    try:
                        key_path.unlink()
                    except Exception:
                        pass
        
        # Remove old records from database
        db.session.query(BackupRun).filter(
            BackupRun.created_at < cutoff_date
        ).delete()
        
        db.session.commit()
        
        return len(old_runs)
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup system statistics"""
        total_backups = BackupRun.query.count()
        successful_backups = BackupRun.query.filter_by(status=BackupStatus.COMPLETED).count()
        failed_backups = BackupRun.query.filter_by(status=BackupStatus.FAILED).count()
        
        recent_backups = BackupRun.query.filter(
            BackupRun.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        total_size = db.session.query(db.func.sum(BackupRun.file_size)).filter(
            BackupRun.status == BackupStatus.COMPLETED
        ).scalar() or 0
        
        return {
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'success_rate': (successful_backups / total_backups * 100) if total_backups > 0 else 0,
            'recent_backups_7_days': recent_backups,
            'total_backup_size_bytes': total_size,
            'total_backup_size_gb': round(total_size / (1024**3), 2)
        }

def get_backup_manager(app=None) -> BackupManager:
    """Get backup manager instance"""
    if not hasattr(g, 'backup_manager'):
        g.backup_manager = BackupManager(app)
    return g.backup_manager