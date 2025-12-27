"""
Backup and Restore models for the POS system
"""
from datetime import datetime
from enum import Enum
import json
from flask_sqlalchemy import SQLAlchemy
from . import db

class BackupType(Enum):
    """Types of backup operations"""
    FULL = "full"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    USER_DATA = "user_data"
    LOGS = "logs"
    INCREMENTAL = "incremental"

class BackupStatus(Enum):
    """Backup operation statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RestoreStatus(Enum):
    """Restore operation statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    VALIDATING = "validating"

class BackupJob(db.Model):
    """Model for backup job configuration"""
    __tablename__ = 'backup_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    backup_type = db.Column(db.Enum(BackupType), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    schedule_cron = db.Column(db.String(255))  # Cron expression for scheduling
    retention_days = db.Column(db.Integer, default=30)
    compression_enabled = db.Column(db.Boolean, default=True)
    encryption_enabled = db.Column(db.Boolean, default=True)
    include_logs = db.Column(db.Boolean, default=False)
    include_user_data = db.Column(db.Boolean, default=True)
    include_config = db.Column(db.Boolean, default=True)
    cloud_storage_config = db.Column(db.Text)  # JSON string for cloud storage settings
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    
    # Relationships
    backup_runs = db.relationship('BackupRun', backref='job', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<BackupJob {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'backup_type': self.backup_type.value if self.backup_type else None,
            'enabled': self.enabled,
            'schedule_cron': self.schedule_cron,
            'retention_days': self.retention_days,
            'compression_enabled': self.compression_enabled,
            'encryption_enabled': self.encryption_enabled,
            'include_logs': self.include_logs,
            'include_user_data': self.include_user_data,
            'include_config': self.include_config,
            'cloud_storage_config': json.loads(self.cloud_storage_config) if self.cloud_storage_config else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None
        }

class BackupRun(db.Model):
    """Model for individual backup runs"""
    __tablename__ = 'backup_runs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('backup_jobs.id'), nullable=False)
    backup_type = db.Column(db.Enum(BackupType), nullable=False)
    status = db.Column(db.Enum(BackupStatus), default=BackupStatus.PENDING)
    
    # File information
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.BigInteger)  # Size in bytes
    file_hash = db.Column(db.String(128))  # SHA-256 hash for integrity verification
    compression_ratio = db.Column(db.Float)  # Compression ratio achieved
    
    # Metadata
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    warning_message = db.Column(db.Text)
    
    # Backup details (JSON)
    backup_details = db.Column(db.Text)  # JSON string with backup specifics
    components_backed_up = db.Column(db.Text)  # JSON string with list of components
    
    # Restore information
    restore_count = db.Column(db.Integer, default=0)
    last_restored_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BackupRun {self.id} - {self.status.value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'backup_type': self.backup_type.value if self.backup_type else None,
            'status': self.status.value if self.status else None,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'compression_ratio': self.compression_ratio,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'warning_message': self.warning_message,
            'backup_details': json.loads(self.backup_details) if self.backup_details else None,
            'components_backed_up': json.loads(self.components_backed_up) if self.components_backed_up else None,
            'restore_count': self.restore_count,
            'last_restored_at': self.last_restored_at.isoformat() if self.last_restored_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class RestoreOperation(db.Model):
    """Model for restore operations"""
    __tablename__ = 'restore_operations'
    
    id = db.Column(db.Integer, primary_key=True)
    backup_run_id = db.Column(db.Integer, db.ForeignKey('backup_runs.id'), nullable=False)
    status = db.Column(db.Enum(RestoreStatus), default=RestoreStatus.PENDING)
    
    # Restore details
    restore_type = db.Column(db.Enum(BackupType), nullable=False)
    target_location = db.Column(db.String(500))  # Where to restore to
    restore_options = db.Column(db.Text)  # JSON string with restore options
    
    # Validation
    validation_passed = db.Column(db.Boolean, default=False)
    validation_details = db.Column(db.Text)  # JSON string with validation results
    
    # Progress tracking
    total_steps = db.Column(db.Integer, default=0)
    completed_steps = db.Column(db.Integer, default=0)
    current_step = db.Column(db.String(255))
    
    # Timing
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    
    # Results
    success_message = db.Column(db.Text)
    error_message = db.Column(db.Text)
    warning_message = db.Column(db.Text)
    
    # Metadata
    initiated_by = db.Column(db.String(255))  # User who initiated the restore
    rollback_available = db.Column(db.Boolean, default=True)
    rollback_backup_id = db.Column(db.Integer, db.ForeignKey('backup_runs.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    backup_run = db.relationship('BackupRun', backref='restore_operations', foreign_keys=[backup_run_id], lazy=True)
    rollback_backup = db.relationship('BackupRun', foreign_keys=[rollback_backup_id], lazy=True)
    
    def __repr__(self):
        return f'<RestoreOperation {self.id} - {self.status.value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'backup_run_id': self.backup_run_id,
            'status': self.status.value if self.status else None,
            'restore_type': self.restore_type.value if self.restore_type else None,
            'target_location': self.target_location,
            'restore_options': json.loads(self.restore_options) if self.restore_options else None,
            'validation_passed': self.validation_passed,
            'validation_details': json.loads(self.validation_details) if self.validation_details else None,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'current_step': self.current_step,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'success_message': self.success_message,
            'error_message': self.error_message,
            'warning_message': self.warning_message,
            'initiated_by': self.initiated_by,
            'rollback_available': self.rollback_available,
            'rollback_backup_id': self.rollback_backup_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class BackupAlert(db.Model):
    """Model for backup-related alerts and notifications"""
    __tablename__ = 'backup_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)  # failure, success, warning, etc.
    severity = db.Column(db.String(20), nullable=False)  # low, medium, high, critical
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Related entities
    backup_run_id = db.Column(db.Integer, db.ForeignKey('backup_runs.id'))
    restore_operation_id = db.Column(db.Integer, db.ForeignKey('restore_operations.id'))
    backup_job_id = db.Column(db.Integer, db.ForeignKey('backup_jobs.id'))
    
    # Status
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.String(255))
    acknowledged_at = db.Column(db.DateTime)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    backup_run = db.relationship('BackupRun', backref='alerts', lazy=True)
    restore_operation = db.relationship('RestoreOperation', backref='alerts', lazy=True)
    backup_job = db.relationship('BackupJob', backref='alerts', lazy=True)
    
    def __repr__(self):
        return f'<BackupAlert {self.id} - {self.alert_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'title': self.title,
            'message': self.message,
            'backup_run_id': self.backup_run_id,
            'restore_operation_id': self.restore_operation_id,
            'backup_job_id': self.backup_job_id,
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class BackupConfiguration(db.Model):
    """Model for system-wide backup configuration"""
    __tablename__ = 'backup_configuration'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, integer, boolean, json
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<BackupConfiguration {self.key}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'data_type': self.data_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

def init_backup_models(app):
    """Initialize backup models with Flask app"""
    with app.app_context():
        # Create backup configuration defaults
        default_configs = [
            ('backup_location', 'backups/', 'Default backup storage location', 'string'),
            ('max_backup_size_gb', '10', 'Maximum backup file size in GB', 'integer'),
            ('compression_level', '6', 'Compression level (1-9)', 'integer'),
            ('encryption_algorithm', 'AES-256', 'Encryption algorithm to use', 'string'),
            ('auto_cleanup_enabled', 'true', 'Enable automatic cleanup of old backups', 'boolean'),
            ('email_notifications_enabled', 'true', 'Enable email notifications for backup events', 'boolean'),
            ('cloud_storage_enabled', 'false', 'Enable cloud storage integration', 'boolean'),
            ('backup_validation_enabled', 'true', 'Enable backup integrity validation', 'boolean'),
            ('restore_validation_enabled', 'true', 'Enable restore validation', 'boolean'),
            ('alert_thresholds', '{"failed_backups": 3, "storage_usage": 85}', 'Alert threshold configuration', 'json')
        ]
        
        for key, value, description, data_type in default_configs:
            existing = BackupConfiguration.query.filter_by(key=key).first()
            if not existing:
                config = BackupConfiguration(
                    key=key,
                    value=value,
                    description=description,
                    data_type=data_type
                )
                db.session.add(config)
        
        db.session.commit()

__all__ = [
    'BackupJob', 'BackupRun', 'RestoreOperation', 'BackupAlert', 
    'BackupConfiguration', 'BackupType', 'BackupStatus', 'RestoreStatus',
    'init_backup_models'
]