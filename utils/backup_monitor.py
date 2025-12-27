"""
Backup Monitor - Monitoring and alerting for backup system
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import current_app
from sqlalchemy import desc, and_

from models.backup import (
    BackupJob, BackupRun, RestoreOperation, BackupAlert, BackupConfiguration,
    BackupStatus, RestoreStatus
)
from models import db
from utils.email_notifier import EmailNotifier

class BackupMonitor:
    """Backup system monitoring and alerting"""
    
    def __init__(self, app=None):
        self.app = app
        self.email_notifier = EmailNotifier()
        self.logger = logging.getLogger(__name__)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
    
    def monitor_backup_system(self):
        """Run comprehensive backup system monitoring"""
        try:
            with self.app.app_context():
                self._check_failed_backups()
                self._check_storage_usage()
                self._check_backup_health()
                self._check_restore_operations()
                self._check_job_schedules()
                self._send_monitoring_report()
                
        except Exception as e:
            self.logger.error(f"Error in backup monitoring: {str(e)}")
    
    def _check_failed_backups(self):
        """Check for failed backup operations"""
        try:
            # Get recent failed backups
            failed_backups = BackupRun.query.filter(
                and_(
                    BackupRun.status == BackupStatus.FAILED,
                    BackupRun.created_at >= datetime.utcnow() - timedelta(hours=24)
                )
            ).order_by(desc(BackupRun.created_at)).all()
            
            if failed_backups:
                # Group by job
                failed_by_job = {}
                for backup in failed_backups:
                    job_name = backup.job.name if backup.job else 'Unknown'
                    if job_name not in failed_by_job:
                        failed_by_job[job_name] = []
                    failed_by_job[job_name].append(backup)
                
                # Create alerts for jobs with multiple failures
                for job_name, backups in failed_by_job.items():
                    if len(backups) >= 3:  # Threshold
                        self._create_alert(
                            alert_type='multiple_failures',
                            severity='high',
                            title='Multiple Backup Failures',
                            message=f'Job "{job_name}" has failed {len(backups)} times in the last 24 hours',
                            backup_job_id=backups[0].job_id,
                            backup_run_id=backups[0].id
                        )
                        
                        # Send immediate notification for critical failures
                        if len(backups) >= 5:
                            self._send_urgent_notification(
                                f'Critical: Backup job "{job_name}" has failed {len(backups)} times',
                                f'The backup job "{job_name}" has failed {len(backups)} times in the last 24 hours. '
                                f'Please check the system immediately.'
                            )
                
                # Create alert for recent single failures
                recent_failures = [b for b in failed_backups if b.created_at >= datetime.utcnow() - timedelta(hours=1)]
                if recent_failures:
                    self._create_alert(
                        alert_type='recent_failure',
                        severity='medium',
                        title='Recent Backup Failure',
                        message=f'{len(recent_failures)} backup(s) failed in the last hour',
                        backup_run_id=recent_failures[0].id
                    )
        
        except Exception as e:
            self.logger.error(f"Error checking failed backups: {str(e)}")
    
    def _check_storage_usage(self):
        """Check backup storage usage"""
        try:
            # Calculate storage usage
            total_size = 0
            backup_path = current_app.config.get('BACKUP_LOCATION', 'backups')
            
            if os.path.exists(backup_path):
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                        except OSError:
                            continue
            
            # Convert to GB
            total_size_gb = total_size / (1024**3)
            
            # Get max storage from config
            config = BackupConfiguration.query.filter_by(key='max_backup_size_gb').first()
            max_storage_gb = float(config.value) if config else 10.0
            
            # Calculate usage percentage
            usage_percentage = (total_size_gb / max_storage_gb) * 100
            
            # Check thresholds
            if usage_percentage >= 95:
                self._create_alert(
                    alert_type='storage_critical',
                    severity='critical',
                    title='Backup Storage Critical',
                    message=f'Backup storage usage is at {usage_percentage:.1f}% (Max: {max_storage_gb}GB)',
                )
                
                self._send_urgent_notification(
                    'CRITICAL: Backup Storage Full',
                    f'Backup storage usage has reached {usage_percentage:.1f}% of capacity ({total_size_gb:.1f}GB / {max_storage_gb}GB). '
                    f'Immediate action required to prevent backup failures.'
                )
                
            elif usage_percentage >= 85:
                self._create_alert(
                    alert_type='storage_warning',
                    severity='high',
                    title='Backup Storage High',
                    message=f'Backup storage usage is at {usage_percentage:.1f}% (Max: {max_storage_gb}GB)',
                )
            
            # Store current usage in config
            self._update_config('current_storage_usage_gb', str(total_size_gb))
            
        except Exception as e:
            self.logger.error(f"Error checking storage usage: {str(e)}")
    
    def _check_backup_health(self):
        """Check overall backup system health"""
        try:
            # Check for successful backups in last 24 hours
            successful_backups_24h = BackupRun.query.filter(
                and_(
                    BackupRun.status == BackupStatus.COMPLETED,
                    BackupRun.created_at >= datetime.utcnow() - timedelta(hours=24)
                )
            ).count()
            
            # Check enabled jobs
            enabled_jobs = BackupJob.query.filter_by(enabled=True).count()
            
            # Alert if no successful backups in 24 hours and jobs are enabled
            if enabled_jobs > 0 and successful_backups_24h == 0:
                self._create_alert(
                    alert_type='no_recent_backups',
                    severity='high',
                    title='No Recent Successful Backups',
                    message=f'No successful backups in the last 24 hours. {enabled_jobs} job(s) are enabled.',
                )
            
            # Check backup integrity
            recent_backups = BackupRun.query.filter(
                and_(
                    BackupRun.status == BackupStatus.COMPLETED,
                    BackupRun.created_at >= datetime.utcnow() - timedelta(hours=24)
                )
            ).limit(5).all()
            
            integrity_failures = 0
            for backup in recent_backups:
                if backup.file_hash:
                    # Verify integrity (simplified check)
                    if not os.path.exists(backup.file_path):
                        integrity_failures += 1
            
            if integrity_failures > 0:
                self._create_alert(
                    alert_type='integrity_issues',
                    severity='medium',
                    title='Backup Integrity Issues',
                    message=f'{integrity_failures} backup(s) failed integrity check',
                )
        
        except Exception as e:
            self.logger.error(f"Error checking backup health: {str(e)}")
    
    def _check_restore_operations(self):
        """Check restore operation status"""
        try:
            # Check for failed restores in last 24 hours
            failed_restores = RestoreOperation.query.filter(
                and_(
                    RestoreOperation.status == RestoreStatus.FAILED,
                    RestoreOperation.created_at >= datetime.utcnow() - timedelta(hours=24)
                )
            ).count()
            
            if failed_restores >= 2:
                self._create_alert(
                    alert_type='restore_failures',
                    severity='high',
                    title='Multiple Restore Failures',
                    message=f'{failed_restores} restore operation(s) failed in the last 24 hours',
                )
            
            # Check for long-running restores
            long_running = RestoreOperation.query.filter(
                and_(
                    RestoreOperation.status.in_([RestoreStatus.IN_PROGRESS, RestoreStatus.VALIDATING]),
                    RestoreOperation.start_time <= datetime.utcnow() - timedelta(hours=2)
                )
            ).all()
            
            for restore in long_running:
                self._create_alert(
                    alert_type='long_running_restore',
                    severity='medium',
                    title='Long Running Restore',
                    message=f'Restore operation {restore.id} has been running for over 2 hours',
                    restore_operation_id=restore.id
                )
        
        except Exception as e:
            self.logger.error(f"Error checking restore operations: {str(e)}")
    
    def _check_job_schedules(self):
        """Check backup job schedules"""
        try:
            # Check for jobs that haven't run recently
            jobs = BackupJob.query.filter_by(enabled=True).all()
            
            for job in jobs:
                if job.schedule_cron and job.last_run:
                    days_since_last_run = (datetime.utcnow() - job.last_run).days
                    
                    # Alert if job hasn't run in 2x its expected interval
                    if '@daily' in job.schedule_cron and days_since_last_run > 2:
                        self._create_alert(
                            alert_type='missed_scheduled_backup',
                            severity='medium',
                            title='Missed Scheduled Backup',
                            message=f'Job "{job.name}" has not run for {days_since_last_run} days',
                            backup_job_id=job.id
                        )
                    elif '@weekly' in job.schedule_cron and days_since_last_run > 14:
                        self._create_alert(
                            alert_type='missed_scheduled_backup',
                            severity='medium',
                            title='Missed Scheduled Backup',
                            message=f'Job "{job.name}" has not run for {days_since_last_run} days',
                            backup_job_id=job.id
                        )
        
        except Exception as e:
            self.logger.error(f"Error checking job schedules: {str(e)}")
    
    def _create_alert(self, alert_type: str, severity: str, title: str, message: str, 
                     backup_run_id: int = None, backup_job_id: int = None, 
                     restore_operation_id: int = None):
        """Create backup alert"""
        try:
            # Check if similar alert already exists recently
            recent_alert = BackupAlert.query.filter(
                and_(
                    BackupAlert.alert_type == alert_type,
                    BackupAlert.created_at >= datetime.utcnow() - timedelta(hours=1)
                )
            ).first()
            
            if recent_alert:
                return  # Don't create duplicate alerts
            
            alert = BackupAlert(
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                backup_run_id=backup_run_id,
                backup_job_id=backup_job_id,
                restore_operation_id=restore_operation_id
            )
            
            db.session.add(alert)
            db.session.commit()
            
            self.logger.info(f"Created alert: {title}")
            
        except Exception as e:
            self.logger.error(f"Error creating alert: {str(e)}")
    
    def _send_urgent_notification(self, subject: str, message: str):
        """Send urgent email notification"""
        try:
            config = BackupConfiguration.query.filter_by(key='email_notifications_enabled').first()
            if not config or config.value.lower() != 'true':
                return
            
            # Send email notification
            self.email_notifier.send_email(
                to_email=current_app.config.get('MAIL_USERNAME'),
                subject=f"Backup System Alert: {subject}",
                body=message
            )
            
        except Exception as e:
            self.logger.error(f"Error sending urgent notification: {str(e)}")
    
    def _send_monitoring_report(self):
        """Send daily monitoring report"""
        try:
            # Only send daily at 6 AM
            now = datetime.utcnow()
            if now.hour != 6 or now.minute > 10:
                return
            
            # Check if report already sent today
            config_key = f"monitoring_report_sent_{now.strftime('%Y%m%d')}"
            config = BackupConfiguration.query.filter_by(key=config_key).first()
            if config:
                return  # Report already sent today
            
            # Get system statistics
            backup_stats = self._get_daily_stats()
            
            # Generate report
            report = self._generate_monitoring_report(backup_stats)
            
            # Send email
            config = BackupConfiguration.query.filter_by(key='email_notifications_enabled').first()
            if config and config.value.lower() == 'true':
                self.email_notifier.send_email(
                    to_email=current_app.config.get('MAIL_USERNAME'),
                    subject=f"Daily Backup System Report - {now.strftime('%Y-%m-%d')}",
                    body=report
                )
            
            # Mark report as sent
            self._update_config(config_key, 'true')
            
        except Exception as e:
            self.logger.error(f"Error sending monitoring report: {str(e)}")
    
    def _get_daily_stats(self) -> Dict[str, Any]:
        """Get daily backup statistics"""
        try:
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            
            # Backup stats
            total_backups_today = BackupRun.query.filter(
                BackupRun.created_at >= today
            ).count()
            
            successful_backups_today = BackupRun.query.filter(
                and_(
                    BackupRun.status == BackupStatus.COMPLETED,
                    BackupRun.created_at >= today
                )
            ).count()
            
            failed_backups_today = BackupRun.query.filter(
                and_(
                    BackupRun.status == BackupStatus.FAILED,
                    BackupRun.created_at >= today
                )
            ).count()
            
            # Restore stats
            total_restores_today = RestoreOperation.query.filter(
                RestoreOperation.created_at >= today
            ).count()
            
            successful_restores_today = RestoreOperation.query.filter(
                and_(
                    RestoreOperation.status == RestoreStatus.COMPLETED,
                    RestoreOperation.created_at >= today
                )
            ).count()
            
            # Alert stats
            new_alerts_today = BackupAlert.query.filter(
                BackupAlert.created_at >= today
            ).count()
            
            unacknowledged_alerts = BackupAlert.query.filter_by(acknowledged=False).count()
            
            # Storage usage
            total_size = 0
            backup_path = current_app.config.get('BACKUP_LOCATION', 'backups')
            if os.path.exists(backup_path):
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                        except OSError:
                            continue
            
            return {
                'date': today.strftime('%Y-%m-%d'),
                'backups': {
                    'total': total_backups_today,
                    'successful': successful_backups_today,
                    'failed': failed_backups_today,
                    'success_rate': (successful_backups_today / total_backups_today * 100) if total_backups_today > 0 else 0
                },
                'restores': {
                    'total': total_restores_today,
                    'successful': successful_restores_today
                },
                'alerts': {
                    'new_today': new_alerts_today,
                    'unacknowledged': unacknowledged_alerts
                },
                'storage': {
                    'total_size_gb': round(total_size / (1024**3), 2)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting daily stats: {str(e)}")
            return {}
    
    def _generate_monitoring_report(self, stats: Dict[str, Any]) -> str:
        """Generate monitoring report email body"""
        if not stats:
            return "Error generating backup system report."
        
        report = f"""
Backup System Daily Report - {stats['date']}

=== BACKUP SUMMARY ===
Total Backups: {stats['backups']['total']}
Successful: {stats['backups']['successful']}
Failed: {stats['backups']['failed']}
Success Rate: {stats['backups']['success_rate']:.1f}%

=== RESTORE SUMMARY ===
Total Restores: {stats['restores']['total']}
Successful: {stats['restores']['successful']}

=== ALERTS SUMMARY ===
New Alerts Today: {stats['alerts']['new_today']}
Unacknowledged Alerts: {stats['alerts']['unacknowledged']}

=== STORAGE ===
Total Backup Storage: {stats['storage']['total_size_gb']} GB

=== SYSTEM STATUS ===
"""
        
        # Add system status
        if stats['backups']['failed'] > 0:
            report += "⚠️  ATTENTION: Some backups failed today\n"
        
        if stats['alerts']['unacknowledged'] > 0:
            report += f"⚠️  ATTENTION: {stats['alerts']['unacknowledged']} unacknowledged alert(s)\n"
        
        if stats['backups']['success_rate'] < 80:
            report += "⚠️  ATTENTION: Backup success rate is below 80%\n"
        
        report += "\nReport generated automatically by the Backup System."
        
        return report
    
    def _update_config(self, key: str, value: str):
        """Update configuration setting"""
        try:
            config = BackupConfiguration.query.filter_by(key=key).first()
            if config:
                config.value = value
            else:
                config = BackupConfiguration(key=key, value=value)
                db.session.add(config)
            db.session.commit()
        except Exception as e:
            self.logger.error(f"Error updating config {key}: {str(e)}")
    
    def acknowledge_all_alerts(self, user_id: str = None):
        """Acknowledge all unacknowledged alerts"""
        try:
            alerts = BackupAlert.query.filter_by(acknowledged=False).all()
            for alert in alerts:
                alert.acknowledged = True
                alert.acknowledged_by = user_id
                alert.acknowledged_at = datetime.utcnow()
            
            db.session.commit()
            return len(alerts)
        except Exception as e:
            self.logger.error(f"Error acknowledging alerts: {str(e)}")
            return 0
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            # Recent backup status
            recent_backups = BackupRun.query.filter(
                BackupRun.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).all()
            
            if not recent_backups:
                health_status = 'no_data'
                health_message = 'No backups in the last 24 hours'
            else:
                successful = len([b for b in recent_backups if b.status == BackupStatus.COMPLETED])
                total = len(recent_backups)
                success_rate = (successful / total) * 100
                
                if success_rate >= 95:
                    health_status = 'healthy'
                    health_message = f'System is healthy ({success_rate:.1f}% success rate)'
                elif success_rate >= 80:
                    health_status = 'warning'
                    health_message = f'System has issues ({success_rate:.1f}% success rate)'
                else:
                    health_status = 'critical'
                    health_message = f'System is critical ({success_rate:.1f}% success rate)'
            
            # Storage health
            storage_usage = self._calculate_storage_usage()
            if storage_usage >= 95:
                storage_status = 'critical'
            elif storage_usage >= 85:
                storage_status = 'warning'
            else:
                storage_status = 'healthy'
            
            # Alert status
            unacknowledged_alerts = BackupAlert.query.filter_by(acknowledged=False).count()
            critical_alerts = BackupAlert.query.filter(
                and_(
                    BackupAlert.acknowledged == False,
                    BackupAlert.severity == 'critical'
                )
            ).count()
            
            return {
                'overall_status': health_status,
                'overall_message': health_message,
                'backup_success_rate': success_rate if recent_backups else 0,
                'storage_status': storage_status,
                'storage_usage_percent': storage_usage,
                'unacknowledged_alerts': unacknowledged_alerts,
                'critical_alerts': critical_alerts,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system health: {str(e)}")
            return {
                'overall_status': 'error',
                'overall_message': f'Error checking system health: {str(e)}',
                'last_check': datetime.utcnow().isoformat()
            }
    
    def _calculate_storage_usage(self) -> float:
        """Calculate storage usage percentage"""
        try:
            total_size = 0
            backup_path = current_app.config.get('BACKUP_LOCATION', 'backups')
            
            if os.path.exists(backup_path):
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                        except OSError:
                            continue
            
            max_storage = 10 * 1024 * 1024 * 1024  # 10GB default
            return (total_size / max_storage) * 100
            
        except Exception:
            return 0

def get_backup_monitor(app=None) -> BackupMonitor:
    """Get backup monitor instance"""
    if not hasattr(g, 'backup_monitor'):
        g.backup_monitor = BackupMonitor(app)
    return g.backup_monitor