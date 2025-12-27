"""
Backup Management Routes
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import desc
import json
import os
from pathlib import Path

from models.backup import (
    BackupJob, BackupRun, RestoreOperation, BackupAlert, BackupConfiguration,
    BackupType, BackupStatus, RestoreStatus
)
from models import db
from utils.backup_manager import BackupManager, get_backup_manager
from utils.restore_manager import RestoreManager, get_restore_manager
from utils.backup_scheduler import get_backup_scheduler

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

@backup_bp.route('/')
@login_required
def index():
    """Backup dashboard"""
    backup_manager = get_backup_manager(current_app)
    restore_manager = get_restore_manager(current_app)
    scheduler = get_backup_scheduler()
    
    # Get statistics
    backup_stats = backup_manager.get_backup_statistics()
    restore_stats = restore_manager.get_restore_statistics()
    scheduler_status = scheduler.get_scheduler_status()
    
    # Get recent backups
    recent_backups = BackupRun.query.order_by(desc(BackupRun.created_at)).limit(10).all()
    
    # Get recent restores
    recent_restores = RestoreOperation.query.order_by(desc(RestoreOperation.created_at)).limit(10).all()
    
    # Get active alerts
    active_alerts = BackupAlert.query.filter_by(acknowledged=False).order_by(desc(BackupAlert.created_at)).limit(10).all()
    
    # Get backup jobs
    backup_jobs = BackupJob.query.order_by(BackupJob.name).all()
    
    return render_template('backup/index.html',
                         backup_stats=backup_stats,
                         restore_stats=restore_stats,
                         scheduler_status=scheduler_status,
                         recent_backups=recent_backups,
                         recent_restores=recent_restores,
                         active_alerts=active_alerts,
                         backup_jobs=backup_jobs)

@backup_bp.route('/jobs')
@login_required
def jobs():
    """Backup jobs management"""
    backup_jobs = BackupJob.query.order_by(BackupJob.name).all()
    return render_template('backup/jobs.html', backup_jobs=backup_jobs)

@backup_bp.route('/jobs/create', methods=['GET', 'POST'])
@login_required
def create_job():
    """Create new backup job"""
    if request.method == 'POST':
        try:
            job = BackupJob(
                name=request.form.get('name'),
                description=request.form.get('description'),
                backup_type=BackupType(request.form.get('backup_type')),
                schedule_cron=request.form.get('schedule_cron'),
                retention_days=int(request.form.get('retention_days', 30)),
                compression_enabled=bool(request.form.get('compression_enabled')),
                encryption_enabled=bool(request.form.get('encryption_enabled')),
                include_logs=bool(request.form.get('include_logs')),
                include_user_data=bool(request.form.get('include_user_data')),
                include_config=bool(request.form.get('include_config'))
            )
            
            db.session.add(job)
            db.session.commit()
            
            # Schedule the job if it has a cron expression
            if job.schedule_cron:
                scheduler = get_backup_scheduler()
                scheduler.schedule_job(job)
            
            flash('Backup job created successfully', 'success')
            return redirect(url_for('backup.jobs'))
            
        except Exception as e:
            flash(f'Error creating backup job: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('backup/create_job.html')

@backup_bp.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    """Edit backup job"""
    job = BackupJob.query.get_or_404(job_id)
    
    if request.method == 'POST':
        try:
            job.name = request.form.get('name')
            job.description = request.form.get('description')
            job.backup_type = BackupType(request.form.get('backup_type'))
            job.schedule_cron = request.form.get('schedule_cron')
            job.retention_days = int(request.form.get('retention_days', 30))
            job.compression_enabled = bool(request.form.get('compression_enabled'))
            job.encryption_enabled = bool(request.form.get('encryption_enabled'))
            job.include_logs = bool(request.form.get('include_logs'))
            job.include_user_data = bool(request.form.get('include_user_data'))
            job.include_config = bool(request.form.get('include_config'))
            job.enabled = bool(request.form.get('enabled'))
            
            db.session.commit()
            
            # Update scheduler
            scheduler = get_backup_scheduler()
            scheduler.unschedule_job(job)
            if job.enabled and job.schedule_cron:
                scheduler.schedule_job(job)
            
            flash('Backup job updated successfully', 'success')
            return redirect(url_for('backup.jobs'))
            
        except Exception as e:
            flash(f'Error updating backup job: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('backup/edit_job.html', job=job)

@backup_bp.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    """Delete backup job"""
    job = BackupJob.query.get_or_404(job_id)
    
    try:
        # Unschedule job
        scheduler = get_backup_scheduler()
        scheduler.unschedule_job(job)
        
        # Delete job
        db.session.delete(job)
        db.session.commit()
        
        flash('Backup job deleted successfully', 'success')
        
    except Exception as e:
        flash(f'Error deleting backup job: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('backup.jobs'))

@backup_bp.route('/jobs/<int:job_id>/run', methods=['POST'])
@login_required
def run_job(job_id):
    """Run backup job manually"""
    try:
        scheduler = get_backup_scheduler()
        backup_run = scheduler.run_manual_backup(job_id, current_user.id)
        
        if backup_run:
            flash(f'Backup job started successfully. Backup ID: {backup_run.id}', 'success')
        else:
            flash('Failed to start backup job', 'error')
            
    except Exception as e:
        flash(f'Error running backup job: {str(e)}', 'error')
    
    return redirect(url_for('backup.jobs'))

@backup_bp.route('/runs')
@login_required
def runs():
    """Backup runs history"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    backup_runs = BackupRun.query.order_by(desc(BackupRun.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('backup/runs.html', backup_runs=backup_runs)

@backup_bp.route('/runs/<int:run_id>')
@login_required
def run_details(run_id):
    """Backup run details"""
    backup_run = BackupRun.query.get_or_404(run_id)
    
    return render_template('backup/run_details.html', backup_run=backup_run)

@backup_bp.route('/runs/<int:run_id>/download')
@login_required
def download_backup(run_id):
    """Download backup file"""
    backup_run = BackupRun.query.get_or_404(run_id)
    
    if not backup_run.file_path or not os.path.exists(backup_run.file_path):
        flash('Backup file not found', 'error')
        return redirect(url_for('backup.runs'))
    
    # Return file for download
    return send_file(backup_run.file_path, as_attachment=True)

@backup_bp.route('/restore')
@login_required
def restore():
    """Restore backup interface"""
    # Get available backups for restore
    completed_backups = BackupRun.query.filter_by(
        status=BackupStatus.COMPLETED
    ).order_by(desc(BackupRun.created_at)).limit(50).all()
    
    return render_template('backup/restore.html', backups=completed_backups)

@backup_bp.route('/restore/<int:run_id>', methods=['GET', 'POST'])
@login_required
def restore_backup(run_id):
    """Restore backup"""
    backup_run = BackupRun.query.get_or_404(run_id)
    
    if request.method == 'POST':
        try:
            restore_options = {
                'backup_before_restore': bool(request.form.get('backup_before_restore')),
                'restore_logs': bool(request.form.get('restore_logs')),
                'backup_existing_files': bool(request.form.get('backup_existing_files')),
                'create_rollback_backup': bool(request.form.get('create_rollback_backup'))
            }
            
            restore_manager = get_restore_manager(current_app)
            restore_operation = restore_manager.restore_backup(
                backup_run, restore_options, current_user.id
            )
            
            flash(f'Restore operation started. Operation ID: {restore_operation.id}', 'success')
            return redirect(url_for('backup.restore_operations'))
            
        except Exception as e:
            flash(f'Error starting restore operation: {str(e)}', 'error')
    
    return render_template('backup/restore_confirm.html', backup_run=backup_run)

@backup_bp.route('/restore/emergency/<int:run_id>', methods=['POST'])
@login_required
def emergency_restore(run_id):
    """Emergency restore"""
    backup_run = BackupRun.query.get_or_404(run_id)
    
    try:
        restore_manager = get_restore_manager(current_app)
        restore_operation = restore_manager.emergency_restore(backup_run, current_user.id)
        
        flash(f'Emergency restore started. Operation ID: {restore_operation.id}', 'warning')
        return redirect(url_for('backup.restore_operations'))
        
    except Exception as e:
        flash(f'Error starting emergency restore: {str(e)}', 'error')
    
    return redirect(url_for('backup.restore'))

@backup_bp.route('/restore/operations')
@login_required
def restore_operations():
    """Restore operations history"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    restore_operations = RestoreOperation.query.order_by(desc(RestoreOperation.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('backup/restore_operations.html', restore_operations=restore_operations)

@backup_bp.route('/restore/operations/<int:operation_id>')
@login_required
def restore_operation_details(operation_id):
    """Restore operation details"""
    restore_operation = RestoreOperation.query.get_or_404(operation_id)
    
    return render_template('backup/restore_operation_details.html', restore_operation=restore_operation)

@backup_bp.route('/alerts')
@login_required
def alerts():
    """Backup alerts"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    alerts = BackupAlert.query.order_by(desc(BackupAlert.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('backup/alerts.html', alerts=alerts)

@backup_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    """Acknowledge backup alert"""
    alert = BackupAlert.query.get_or_404(alert_id)
    
    try:
        alert.acknowledged = True
        alert.acknowledged_by = current_user.id
        alert.acknowledged_at = datetime.utcnow()
        
        db.session.commit()
        flash('Alert acknowledged', 'success')
        
    except Exception as e:
        flash(f'Error acknowledging alert: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('backup.alerts'))

@backup_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Backup system settings"""
    if request.method == 'POST':
        try:
            # Update configuration settings
            configs = {
                'backup_location': request.form.get('backup_location'),
                'max_backup_size_gb': request.form.get('max_backup_size_gb'),
                'compression_level': request.form.get('compression_level'),
                'encryption_algorithm': request.form.get('encryption_algorithm'),
                'auto_cleanup_enabled': bool(request.form.get('auto_cleanup_enabled')),
                'email_notifications_enabled': bool(request.form.get('email_notifications_enabled')),
                'cloud_storage_enabled': bool(request.form.get('cloud_storage_enabled')),
                'backup_validation_enabled': bool(request.form.get('backup_validation_enabled')),
                'restore_validation_enabled': bool(request.form.get('restore_validation_enabled'))
            }
            
            alert_thresholds = {
                'failed_backups': int(request.form.get('failed_backups_threshold', 3)),
                'storage_usage': int(request.form.get('storage_usage_threshold', 85))
            }
            
            # Update configurations
            for key, value in configs.items():
                config = BackupConfiguration.query.filter_by(key=key).first()
                if config:
                    config.value = str(value)
                else:
                    config = BackupConfiguration(key=key, value=str(value))
                    db.session.add(config)
            
            # Update alert thresholds
            alert_config = BackupConfiguration.query.filter_by(key='alert_thresholds').first()
            if alert_config:
                alert_config.value = json.dumps(alert_thresholds)
            else:
                alert_config = BackupConfiguration(
                    key='alert_thresholds',
                    value=json.dumps(alert_thresholds),
                    data_type='json'
                )
                db.session.add(alert_config)
            
            db.session.commit()
            flash('Backup settings updated successfully', 'success')
            
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'error')
            db.session.rollback()
    
    # Get current settings
    configs = {config.key: config.value for config in BackupConfiguration.query.all()}
    
    return render_template('backup/settings.html', configs=configs)

@backup_bp.route('/scheduler/status')
@login_required
def scheduler_status():
    """Get scheduler status"""
    scheduler = get_backup_scheduler()
    status = scheduler.get_scheduler_status()
    return jsonify(status)

@backup_bp.route('/scheduler/start', methods=['POST'])
@login_required
def start_scheduler():
    """Start backup scheduler"""
    try:
        scheduler = get_backup_scheduler()
        scheduler.start_scheduler()
        scheduler.reschedule_all_jobs()
        flash('Backup scheduler started', 'success')
    except Exception as e:
        flash(f'Error starting scheduler: {str(e)}', 'error')
    
    return redirect(url_for('backup.index'))

@backup_bp.route('/scheduler/stop', methods=['POST'])
@login_required
def stop_scheduler():
    """Stop backup scheduler"""
    try:
        scheduler = get_backup_scheduler()
        scheduler.stop_scheduler()
        flash('Backup scheduler stopped', 'success')
    except Exception as e:
        flash(f'Error stopping scheduler: {str(e)}', 'error')
    
    return redirect(url_for('backup.index'))

@backup_bp.route('/cleanup', methods=['POST'])
@login_required
def cleanup():
    """Clean up old backups"""
    try:
        backup_manager = get_backup_manager(current_app)
        retention_days = int(request.form.get('retention_days', 30))
        
        cleaned_count = backup_manager.cleanup_old_backups(retention_days)
        flash(f'Cleaned up {cleaned_count} old backup records', 'success')
        
    except Exception as e:
        flash(f'Error during cleanup: {str(e)}', 'error')
    
    return redirect(url_for('backup.index'))

@backup_bp.route('/api/stats')
@login_required
def api_stats():
    """Get backup statistics API"""
    backup_manager = get_backup_manager(current_app)
    restore_manager = get_restore_manager(current_app)
    
    stats = {
        'backup': backup_manager.get_backup_statistics(),
        'restore': restore_manager.get_restore_statistics()
    }
    
    return jsonify(stats)

@backup_bp.route('/api/verify/<int:run_id>')
@login_required
def verify_backup(run_id):
    """Verify backup integrity"""
    backup_run = BackupRun.query.get_or_404(run_id)
    
    try:
        backup_manager = get_backup_manager(current_app)
        is_valid = backup_manager.verify_backup_integrity(backup_run)
        
        return jsonify({
            'valid': is_valid,
            'message': 'Backup integrity verified' if is_valid else 'Backup integrity check failed'
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'message': f'Error verifying backup: {str(e)}'
        }), 500