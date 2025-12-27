"""
Backup Scheduler - Automated backup scheduling and execution
"""
import os
import schedule
import time
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import current_app
import logging

from models.backup import BackupJob, BackupRun, BackupStatus, BackupType
from models import db
from utils.backup_manager import BackupManager

class BackupScheduler:
    """Automated backup scheduling system"""
    
    def __init__(self, app=None):
        self.app = app
        self.backup_manager = BackupManager(app)
        self.scheduler_thread = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
    
    def start_scheduler(self):
        """Start the backup scheduler"""
        if self.is_running:
            self.logger.warning("Backup scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("Backup scheduler started")
    
    def stop_scheduler(self):
        """Stop the backup scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Backup scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in backup scheduler loop: {str(e)}")
                time.sleep(60)
    
    def schedule_job(self, job: BackupJob) -> bool:
        """Schedule a backup job"""
        try:
            if not job.enabled or not job.schedule_cron:
                return False
            
            # Parse cron expression and create schedule
            # Simple cron parser - you might want to use a proper cron library
            schedule_func = self._parse_cron_expression(job.schedule_cron)
            if schedule_func:
                schedule_func(lambda: self._execute_backup_job(job))
                self.logger.info(f"Scheduled backup job: {job.name}")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to schedule job {job.name}: {str(e)}")
        
        return False
    
    def unschedule_job(self, job: BackupJob):
        """Unschedule a backup job"""
        try:
            # Clear existing schedules for this job
            schedule.clear(f"job_{job.id}")
            self.logger.info(f"Unscheduled backup job: {job.name}")
        except Exception as e:
            self.logger.error(f"Failed to unschedule job {job.name}: {str(e)}")
    
    def reschedule_all_jobs(self):
        """Reschedule all enabled backup jobs"""
        # Clear all existing schedules
        schedule.clear()
        
        # Get all enabled backup jobs
        jobs = BackupJob.query.filter_by(enabled=True).all()
        
        for job in jobs:
            self.schedule_job(job)
        
        self.logger.info(f"Rescheduled {len(jobs)} backup jobs")
    
    def _parse_cron_expression(self, cron_expression: str):
        """Parse cron expression and return appropriate schedule function"""
        # Simple cron parser - for production, consider using python-crontab or similar
        try:
            parts = cron_expression.strip().split()
            if len(parts) != 5:
                return None
            
            minute, hour, day, month, weekday = parts
            
            # Handle different cron formats
            if cron_expression == "@daily":
                return schedule.every().day.at("02:00")
            elif cron_expression == "@weekly":
                return schedule.every().sunday.at("02:00")
            elif cron_expression == "@monthly":
                return schedule.every().month.do
            
            # Parse standard cron format
            if minute == "0" and hour == "2" and day == "*" and month == "*" and weekday == "*":
                # Daily at 2 AM
                return schedule.every().day.at("02:00")
            elif minute == "0" and hour == "2" and day == "1" and month == "*" and weekday == "*":
                # Monthly on 1st at 2 AM
                return schedule.every().month.do
            elif minute == "0" and hour == "2" and day == "0" and month == "*" and weekday == "0":
                # Weekly on Sunday at 2 AM
                return schedule.every().sunday.at("02:00")
            else:
                # For complex cron expressions, you might want to use a proper library
                # For now, default to daily
                return schedule.every().day.at("02:00")
        
        except Exception as e:
            self.logger.error(f"Failed to parse cron expression '{cron_expression}': {str(e)}")
            return schedule.every().day.at("02:00")  # Default to daily
    
    def _execute_backup_job(self, job: BackupJob):
        """Execute a backup job"""
        try:
            with self.app.app_context():
                self.logger.info(f"Starting scheduled backup job: {job.name}")
                backup_run = self.backup_manager.create_backup(job, 'scheduler')
                self.logger.info(f"Completed backup job: {job.name}, backup_id: {backup_run.id}")
                
                # Check for alerts/thresholds
                self._check_alert_conditions(job, backup_run)
                
        except Exception as e:
            self.logger.error(f"Error executing backup job {job.name}: {str(e)}")
    
    def _check_alert_conditions(self, job: BackupJob, backup_run: BackupRun):
        """Check alert conditions and create alerts if needed"""
        try:
            from models.backup import BackupAlert
            
            # Check for failed backups
            recent_failed = BackupRun.query.filter(
                BackupRun.job_id == job.id,
                BackupRun.status == BackupStatus.FAILED,
                BackupRun.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            # Alert thresholds from configuration
            alert_config = self._get_alert_configuration()
            failed_backup_threshold = alert_config.get('failed_backups', 3)
            
            if recent_failed >= failed_backup_threshold:
                alert = BackupAlert(
                    alert_type='threshold_breach',
                    severity='high',
                    title='Backup Failure Threshold Exceeded',
                    message=f'Job "{job.name}" has failed {recent_failed} times in the last 24 hours',
                    backup_job_id=job.id,
                    backup_run_id=backup_run.id
                )
                db.session.add(alert)
            
            # Check storage usage
            storage_usage = self._calculate_storage_usage()
            storage_threshold = alert_config.get('storage_usage', 85)
            
            if storage_usage >= storage_threshold:
                alert = BackupAlert(
                    alert_type='storage_warning',
                    severity='medium',
                    title='Backup Storage Usage High',
                    message=f'Backup storage usage is at {storage_usage:.1f}%, threshold is {storage_threshold}%',
                    backup_job_id=job.id
                )
                db.session.add(alert)
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error checking alert conditions: {str(e)}")
    
    def _get_alert_configuration(self) -> Dict:
        """Get alert configuration from database"""
        try:
            from models.backup import BackupConfiguration
            
            config = BackupConfiguration.query.filter_by(key='alert_thresholds').first()
            if config and config.value:
                return json.loads(config.value)
            return {'failed_backups': 3, 'storage_usage': 85}
        except Exception:
            return {'failed_backups': 3, 'storage_usage': 85}
    
    def _calculate_storage_usage(self) -> float:
        """Calculate backup storage usage as percentage"""
        try:
            total_size = 0
            backup_path = current_app.config.get('BACKUP_LOCATION', 'backups')
            
            if os.path.exists(backup_path):
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
            
            # Assume 10GB max storage (configurable)
            max_storage = 10 * 1024 * 1024 * 1024  # 10GB in bytes
            return (total_size / max_storage) * 100
            
        except Exception:
            return 0
    
    def run_manual_backup(self, job_id: int, user_id: str = None) -> Optional[BackupRun]:
        """Run a backup job manually"""
        try:
            job = BackupJob.query.get(job_id)
            if not job:
                raise ValueError(f"Backup job {job_id} not found")
            
            with self.app.app_context():
                return self.backup_manager.create_backup(job, user_id)
        
        except Exception as e:
            self.logger.error(f"Manual backup failed for job {job_id}: {str(e)}")
            return None
    
    def get_next_scheduled_backups(self, limit: int = 10) -> List[Dict]:
        """Get list of next scheduled backups"""
        try:
            jobs = BackupJob.query.filter_by(enabled=True).all()
            upcoming = []
            
            for job in jobs:
                if job.schedule_cron:
                    next_run = self._calculate_next_run_time(job.schedule_cron)
                    if next_run:
                        upcoming.append({
                            'job_id': job.id,
                            'job_name': job.name,
                            'backup_type': job.backup_type.value,
                            'next_run': next_run,
                            'schedule': job.schedule_cron
                        })
            
            # Sort by next run time
            upcoming.sort(key=lambda x: x['next_run'])
            return upcoming[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting scheduled backups: {str(e)}")
            return []
    
    def _calculate_next_run_time(self, cron_expression: str) -> Optional[datetime]:
        """Calculate next run time for cron expression"""
        try:
            # Simple implementation - for production use proper cron parsing
            if cron_expression == "@daily":
                return datetime.now().replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=1)
            elif cron_expression == "@weekly":
                days_ahead = 6 - datetime.now().weekday()  # Sunday is 6
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                return datetime.now().replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
            elif cron_expression == "@monthly":
                # Next month
                if datetime.now().month == 12:
                    next_month = datetime.now().replace(year=datetime.now().year + 1, month=1, day=1)
                else:
                    next_month = datetime.now().replace(month=datetime.now().month + 1, day=1)
                return next_month.replace(hour=2, minute=0, second=0, microsecond=0)
            else:
                # Default to daily
                return datetime.now().replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        except Exception:
            return datetime.now() + timedelta(days=1)
    
    def get_scheduler_status(self) -> Dict:
        """Get scheduler status information"""
        return {
            'is_running': self.is_running,
            'total_jobs': BackupJob.query.filter_by(enabled=True).count(),
            'scheduled_jobs': len(schedule.jobs),
            'next_runs': self.get_next_scheduled_backups(5)
        }

# Global scheduler instance
backup_scheduler = None

def init_backup_scheduler(app=None):
    """Initialize the global backup scheduler"""
    global backup_scheduler
    backup_scheduler = BackupScheduler(app)
    return backup_scheduler

def get_backup_scheduler() -> BackupScheduler:
    """Get the global backup scheduler instance"""
    global backup_scheduler
    if backup_scheduler is None:
        raise RuntimeError("Backup scheduler not initialized")
    return backup_scheduler