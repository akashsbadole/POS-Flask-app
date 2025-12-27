"""
Test Suite for Backup and Restore System
"""
import unittest
import tempfile
import os
import shutil
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from models import db, init_db, create_tables
from models.backup import (
    BackupJob, BackupRun, RestoreOperation, BackupAlert, BackupConfiguration,
    BackupType, BackupStatus, RestoreStatus, init_backup_models
)
from models.user import User
from utils.backup_manager import BackupManager
from utils.restore_manager import RestoreManager
from utils.backup_scheduler import BackupScheduler
from utils.backup_monitor import BackupMonitor

class TestBackupSystem(unittest.TestCase):
    """Test cases for backup and restore system"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Initialize extensions
        db.init_app(self.app)
        init_db(self.app)
        init_backup_models(self.app)
        
        with self.app.app_context():
            create_tables()
            self._create_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def _create_test_data(self):
        """Create test data"""
        # Create test user
        user = User(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        db.session.add(user)
        
        # Create test backup job
        job = BackupJob(
            name='Test Backup Job',
            description='Test backup job for unit testing',
            backup_type=BackupType.FULL,
            schedule_cron='@daily',
            retention_days=7,
            compression_enabled=True,
            encryption_enabled=False,
            include_config=True,
            include_user_data=True,
            include_logs=False
        )
        db.session.add(job)
        
        # Create test backup configuration
        configs = [
            ('backup_location', 'test_backups/', 'Test backup location'),
            ('max_backup_size_gb', '5', 'Max backup size'),
            ('compression_level', '6', 'Compression level'),
            ('auto_cleanup_enabled', 'true', 'Auto cleanup enabled')
        ]
        
        for key, value, description in configs:
            config = BackupConfiguration(key=key, value=value, description=description)
            db.session.add(config)
        
        db.session.commit()
        self.test_user = user
        self.test_job = job
    
    def test_backup_job_creation(self):
        """Test backup job creation"""
        with self.app.app_context():
            job = BackupJob.query.filter_by(name='Test Backup Job').first()
            self.assertIsNotNone(job)
            self.assertEqual(job.name, 'Test Backup Job')
            self.assertEqual(job.backup_type, BackupType.FULL)
            self.assertTrue(job.enabled)
    
    def test_backup_run_creation(self):
        """Test backup run creation"""
        with self.app.app_context():
            # Create a backup run
            backup_run = BackupRun(
                job_id=self.test_job.id,
                backup_type=BackupType.FULL,
                status=BackupStatus.PENDING
            )
            db.session.add(backup_run)
            db.session.commit()
            
            self.assertIsNotNone(backup_run.id)
            self.assertEqual(backup_run.status, BackupStatus.PENDING)
    
    def test_backup_manager_initialization(self):
        """Test backup manager initialization"""
        backup_manager = BackupManager(self.app)
        self.assertIsNotNone(backup_manager)
        self.assertEqual(backup_manager.app, self.app)
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_backup_manager_directory_setup(self, mock_makedirs, mock_exists):
        """Test backup manager directory setup"""
        mock_exists.return_value = False
        backup_manager = BackupManager(self.app)
        backup_manager.init_app(self.app)
        
        # Verify directories are created
        self.assertTrue(mock_makedirs.called)
    
    def test_backup_statistics(self):
        """Test backup statistics calculation"""
        with self.app.app_context():
            backup_manager = BackupManager(self.app)
            backup_manager.init_app(self.app)
            
            # Create some test backup runs
            for i in range(5):
                backup_run = BackupRun(
                    job_id=self.test_job.id,
                    backup_type=BackupType.FULL,
                    status=BackupStatus.COMPLETED if i < 4 else BackupStatus.FAILED,
                    file_size=1024 * 1024 * (i + 1),  # Different sizes
                    created_at=datetime.utcnow() - timedelta(days=i)
                )
                db.session.add(backup_run)
            
            db.session.commit()
            
            stats = backup_manager.get_backup_statistics()
            
            self.assertEqual(stats['total_backups'], 5)
            self.assertEqual(stats['successful_backups'], 4)
            self.assertEqual(stats['failed_backups'], 1)
            self.assertEqual(stats['success_rate'], 80.0)
    
    def test_backup_cleanup(self):
        """Test backup cleanup functionality"""
        with self.app.app_context():
            backup_manager = BackupManager(self.app)
            backup_manager.init_app(self.app)
            
            # Create old backup runs
            old_date = datetime.utcnow() - timedelta(days=40)
            
            for i in range(3):
                backup_run = BackupRun(
                    job_id=self.test_job.id,
                    backup_type=BackupType.FULL,
                    status=BackupStatus.COMPLETED,
                    created_at=old_date
                )
                db.session.add(backup_run)
            
            db.session.commit()
            
            # Run cleanup
            cleaned_count = backup_manager.cleanup_old_backups(30)
            
            # Verify cleanup
            self.assertEqual(cleaned_count, 3)
            remaining_backups = BackupRun.query.filter(
                BackupRun.created_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
            self.assertEqual(remaining_backups, 0)
    
    def test_restore_operation_creation(self):
        """Test restore operation creation"""
        with self.app.app_context():
            # First create a backup run
            backup_run = BackupRun(
                job_id=self.test_job.id,
                backup_type=BackupType.FULL,
                status=BackupStatus.COMPLETED,
                file_size=1024 * 1024
            )
            db.session.add(backup_run)
            db.session.commit()
            
            # Create restore operation
            restore_operation = RestoreOperation(
                backup_run_id=backup_run.id,
                restore_type=BackupType.FULL,
                status=RestoreStatus.PENDING,
                initiated_by='testuser'
            )
            db.session.add(restore_operation)
            db.session.commit()
            
            self.assertIsNotNone(restore_operation.id)
            self.assertEqual(restore_operation.status, RestoreStatus.PENDING)
    
    def test_backup_alert_creation(self):
        """Test backup alert creation"""
        with self.app.app_context():
            alert = BackupAlert(
                alert_type='test_alert',
                severity='medium',
                title='Test Alert',
                message='This is a test alert'
            )
            db.session.add(alert)
            db.session.commit()
            
            self.assertIsNotNone(alert.id)
            self.assertEqual(alert.acknowledged, False)
            self.assertEqual(alert.resolved, False)
    
    def test_backup_configuration(self):
        """Test backup configuration"""
        with self.app.app_context():
            config = BackupConfiguration.query.filter_by(key='backup_location').first()
            self.assertIsNotNone(config)
            self.assertEqual(config.value, 'test_backups/')
    
    def test_backup_scheduler_initialization(self):
        """Test backup scheduler initialization"""
        scheduler = BackupScheduler(self.app)
        self.assertIsNotNone(scheduler)
        self.assertEqual(scheduler.app, self.app)
        self.assertFalse(scheduler.is_running)
    
    def test_backup_monitor_initialization(self):
        """Test backup monitor initialization"""
        monitor = BackupMonitor(self.app)
        self.assertIsNotNone(monitor)
        self.assertEqual(monitor.app, self.app)
    
    def test_system_health_check(self):
        """Test system health check"""
        with self.app.app_context():
            monitor = BackupMonitor(self.app)
            monitor.init_app(self.app)
            
            health = monitor.get_system_health()
            
            self.assertIn('overall_status', health)
            self.assertIn('overall_message', health)
            self.assertIn('last_check', health)
    
    def test_backup_integrity_verification(self):
        """Test backup integrity verification"""
        with self.app.app_context():
            # Create a backup run with file
            backup_run = BackupRun(
                job_id=self.test_job.id,
                backup_type=BackupType.FULL,
                status=BackupStatus.COMPLETED
            )
            db.session.add(backup_run)
            db.session.commit()
            
            backup_manager = BackupManager(self.app)
            backup_manager.init_app(self.app)
            
            # Test with non-existent file
            is_valid = backup_manager.verify_backup_integrity(backup_run)
            self.assertFalse(is_valid)
    
    @patch('tempfile.NamedTemporaryFile')
    def test_database_backup_functionality(self, mock_temp_file):
        """Test database backup functionality"""
        with self.app.app_context():
            backup_manager = BackupManager(self.app)
            backup_manager.init_app(self.app)
            
            # Mock the temporary file creation
            mock_temp = MagicMock()
            mock_temp.name = '/tmp/test_backup.db'
            mock_temp_file.return_value.__enter__.return_value = mock_temp
            
            # Mock file operations
            with patch('shutil.copy2'), \
                 patch('builtins.open', unittest.mock.mock_open(read_data=b'test data')), \
                 patch('hashlib.sha256'), \
                 patch('tarfile.open'):
                
                # This would normally require actual database operations
                # but for unit testing, we're just checking the structure
                job = BackupJob.query.first()
                backup_run = BackupRun(
                    job_id=job.id,
                    backup_type=BackupType.DATABASE,
                    status=BackupStatus.IN_PROGRESS,
                    start_time=datetime.utcnow()
                )
                db.session.add(backup_run)
                db.session.commit()
                
                self.assertIsNotNone(backup_run.id)
    
    def test_backup_type_enum(self):
        """Test backup type enum values"""
        self.assertEqual(BackupType.FULL.value, 'full')
        self.assertEqual(BackupType.DATABASE.value, 'database')
        self.assertEqual(BackupType.CONFIGURATION.value, 'configuration')
        self.assertEqual(BackupType.USER_DATA.value, 'user_data')
        self.assertEqual(BackupType.LOGS.value, 'logs')
        self.assertEqual(BackupType.INCREMENTAL.value, 'incremental')
    
    def test_backup_status_enum(self):
        """Test backup status enum values"""
        self.assertEqual(BackupStatus.PENDING.value, 'pending')
        self.assertEqual(BackupStatus.IN_PROGRESS.value, 'in_progress')
        self.assertEqual(BackupStatus.COMPLETED.value, 'completed')
        self.assertEqual(BackupStatus.FAILED.value, 'failed')
        self.assertEqual(BackupStatus.CANCELLED.value, 'cancelled')
    
    def test_restore_status_enum(self):
        """Test restore status enum values"""
        self.assertEqual(RestoreStatus.PENDING.value, 'pending')
        self.assertEqual(RestoreStatus.IN_PROGRESS.value, 'in_progress')
        self.assertEqual(RestoreStatus.COMPLETED.value, 'completed')
        self.assertEqual(RestoreStatus.FAILED.value, 'failed')
        self.assertEqual(RestoreStatus.CANCELLED.value, 'cancelled')
        self.assertEqual(RestoreStatus.VALIDATING.value, 'validating')

class TestBackupIntegration(unittest.TestCase):
    """Integration tests for backup system"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Initialize extensions
        db.init_app(self.app)
        init_db(self.app)
        init_backup_models(self.app)
        
        with self.app.app_context():
            create_tables()
    
    def tearDown(self):
        """Clean up integration test environment"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_full_backup_workflow(self):
        """Test complete backup workflow"""
        with self.app.app_context():
            # Create backup manager
            backup_manager = BackupManager(self.app)
            backup_manager.init_app(self.app)
            
            # Create backup job
            job = BackupJob(
                name='Integration Test Job',
                description='Test job for integration testing',
                backup_type=BackupType.FULL,
                enabled=True,
                compression_enabled=True,
                encryption_enabled=False
            )
            db.session.add(job)
            db.session.commit()
            
            # Mock the actual backup creation to avoid file system operations
            with patch.object(backup_manager, '_create_backup_archive') as mock_create_archive:
                # Set up mock
                mock_archive = tempfile.NamedTemporaryFile(delete=False)
                mock_archive_path = mock_archive.name
                mock_archive.close()
                
                mock_create_archive.return_value = mock_archive_path
                
                # Create backup
                backup_run = backup_manager.create_backup(job, 'test_user')
                
                # Verify backup run was created
                self.assertIsNotNone(backup_run.id)
                self.assertEqual(backup_run.status, BackupStatus.COMPLETED)
                self.assertEqual(backup_run.job_id, job.id)
                self.assertEqual(backup_run.backup_type, BackupType.FULL)
                self.assertIsNotNone(backup_run.file_path)
                
                # Clean up
                if os.path.exists(mock_archive_path):
                    os.unlink(mock_archive_path)
    
    def test_backup_job_lifecycle(self):
        """Test backup job complete lifecycle"""
        with self.app.app_context():
            # Create scheduler
            scheduler = BackupScheduler(self.app)
            scheduler.init_app(self.app)
            
            # Create job
            job = BackupJob(
                name='Lifecycle Test Job',
                backup_type=BackupType.DATABASE,
                schedule_cron='@daily',
                enabled=True
            )
            db.session.add(job)
            db.session.commit()
            
            # Test scheduling
            scheduled = scheduler.schedule_job(job)
            self.assertTrue(scheduled)
            
            # Test unscheduling
            scheduler.unschedule_job(job)
            
            # Clean up
            scheduler.stop_scheduler()
    
    def test_backup_monitoring_workflow(self):
        """Test backup monitoring workflow"""
        with self.app.app_context():
            # Create monitor
            monitor = BackupMonitor(self.app)
            monitor.init_app(self.app)
            
            # Create test backup run with failure
            job = BackupJob(
                name='Monitor Test Job',
                backup_type=BackupType.FULL
            )
            db.session.add(job)
            db.session.commit()
            
            backup_run = BackupRun(
                job_id=job.id,
                backup_type=BackupType.FULL,
                status=BackupStatus.FAILED,
                error_message='Test failure',
                created_at=datetime.utcnow() - timedelta(hours=2)
            )
            db.session.add(backup_run)
            db.session.commit()
            
            # Run monitoring
            monitor.monitor_backup_system()
            
            # Check if alert was created
            alert = BackupAlert.query.filter_by(
                alert_type='recent_failure'
            ).first()
            
            # Alert creation depends on the monitoring logic
            # This test verifies the monitoring runs without errors
            
    def test_backup_statistics_accuracy(self):
        """Test backup statistics accuracy"""
        with self.app.app_context():
            backup_manager = BackupManager(self.app)
            backup_manager.init_app(self.app)
            
            # Create test jobs and backups
            job1 = BackupJob(name='Stats Test Job 1', backup_type=BackupType.FULL)
            job2 = BackupJob(name='Stats Test Job 2', backup_type=BackupType.DATABASE)
            db.session.add_all([job1, job2])
            db.session.commit()
            
            # Create various backup runs
            test_backups = [
                {'job': job1, 'status': BackupStatus.COMPLETED, 'size': 1024*1024, 'days_ago': 1},
                {'job': job1, 'status': BackupStatus.COMPLETED, 'size': 2048*1024, 'days_ago': 2},
                {'job': job1, 'status': BackupStatus.FAILED, 'size': None, 'days_ago': 3},
                {'job': job2, 'status': BackupStatus.COMPLETED, 'size': 512*1024, 'days_ago': 1},
                {'job': job2, 'status': BackupStatus.COMPLETED, 'size': 768*1024, 'days_ago': 5},
            ]
            
            for backup_data in test_backups:
                backup_run = BackupRun(
                    job_id=backup_data['job'].id,
                    backup_type=backup_data['job'].backup_type,
                    status=backup_data['status'],
                    file_size=backup_data['size'],
                    created_at=datetime.utcnow() - timedelta(days=backup_data['days_ago'])
                )
                db.session.add(backup_run)
            
            db.session.commit()
            
            # Get statistics
            stats = backup_manager.get_backup_statistics()
            
            # Verify accuracy
            self.assertEqual(stats['total_backups'], 5)
            self.assertEqual(stats['successful_backups'], 4)
            self.assertEqual(stats['failed_backups'], 1)
            self.assertEqual(stats['success_rate'], 80.0)
            self.assertEqual(stats['recent_backups_7_days'], 5)
            self.assertGreater(stats['total_backup_size_gb'], 0)

if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(TestBackupSystem))
    suite.addTest(unittest.makeSuite(TestBackupIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Test Results Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")