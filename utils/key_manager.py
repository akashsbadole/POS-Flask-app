"""
Key Management System for POS Encryption (Flask Web Version)
Provides secure key storage, backup, recovery, and rotation capabilities
"""

import os
import json
import shutil
import logging
from datetime import datetime, timedelta
from .encryption import get_encryption_manager

logger = logging.getLogger(__name__)

class KeyManager:
    """
    Manages encryption keys with secure storage, backup, and rotation
    """
    
    def __init__(self, config_dir=None):
        """
        Initialize key manager
        
        Args:
            config_dir: Directory for key storage. If None, uses default.
        """
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'config')
        self.key_dir = os.path.join(self.config_dir, 'keys')
        self.backup_dir = os.path.join(self.config_dir, 'key_backups')
        
        # Ensure directories exist
        os.makedirs(self.key_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Set secure permissions
        os.chmod(self.key_dir, 0o700)
        os.chmod(self.backup_dir, 0o700)
        
        self.encryption_manager = get_encryption_manager()
    
    def create_key_backup(self, backup_name=None):
        """
        Create a secure backup of the current encryption key
        
        Args:
            backup_name: Name for backup file. If None, generates timestamp.
            
        Returns:
            Path to backup file
        """
        try:
            if not backup_name:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_name = f"key_backup_{timestamp}.json"
            
            source_key_path = self.encryption_manager.key_file_path
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Copy key file to backup location
            shutil.copy2(source_key_path, backup_path)
            
            # Set secure permissions
            os.chmod(backup_path, 0o600)
            
            # Create backup metadata
            metadata = {
                'backup_name': backup_name,
                'created_at': datetime.utcnow().isoformat(),
                'key_file_path': source_key_path,
                'version': '2.0',
                'description': 'Encryption key backup for POS web system'
            }
            
            metadata_path = backup_path.replace('.json', '_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            os.chmod(metadata_path, 0o600)
            
            logger.info(f"Key backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create key backup: {str(e)}")
            raise
    
    def list_key_backups(self):
        """
        List all available key backups
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('_metadata.json'):
                    metadata_path = os.path.join(self.backup_dir, filename)
                    
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        # Check if corresponding backup file exists
                        backup_filename = filename.replace('_metadata.json', '.json')
                        backup_path = os.path.join(self.backup_dir, backup_filename)
                        
                        if os.path.exists(backup_path):
                            # Get file stats
                            stat = os.stat(backup_path)
                            metadata.update({
                                'backup_path': backup_path,
                                'file_size': stat.st_size,
                                'created_timestamp': stat.st_mtime
                            })
                            backups.append(metadata)
                    
                    except Exception as e:
                        logger.warning(f"Failed to read backup metadata {filename}: {str(e)}")
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x.get('created_timestamp', 0), reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list key backups: {str(e)}")
            return []
    
    def restore_key_from_backup(self, backup_path):
        """
        Restore encryption key from backup
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if restore successful, False otherwise
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create backup of current key before restoring
            current_backup = self.create_key_backup("before_restore_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
            
            # Get current key file path
            current_key_path = self.encryption_manager.key_file_path
            
            # Restore from backup
            shutil.copy2(backup_path, current_key_path)
            
            # Set secure permissions
            os.chmod(current_key_path, 0o600)
            
            logger.info(f"Key restored from backup: {backup_path}")
            logger.info(f"Previous key backed up to: {current_backup}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore key from backup: {str(e)}")
            return False
    
    def rotate_encryption_key(self, new_master_key=None):
        """
        Rotate the encryption key with proper backup and verification
        
        Args:
            new_master_key: New master key. If None, generates random.
            
        Returns:
            True if rotation successful, False otherwise
        """
        try:
            # Create backup before rotation
            backup_path = self.create_key_backup("before_rotation_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
            
            # Perform key rotation
            rotation_success = self.encryption_manager.rotate_key(new_master_key)
            
            if rotation_success:
                # Verify new key works
                test_data = "key_rotation_test_" + datetime.utcnow().isoformat()
                encrypted = self.encryption_manager.encrypt(test_data)
                decrypted = self.encryption_manager.decrypt(encrypted)
                
                if test_data == decrypted:
                    logger.info("Key rotation successful and verified")
                    return True
                else:
                    logger.error("Key rotation verification failed")
                    # Restore from backup
                    self.restore_key_from_backup(backup_path)
                    return False
            else:
                logger.error("Key rotation failed")
                # Restore from backup
                self.restore_key_from_backup(backup_path)
                return False
                
        except Exception as e:
            logger.error(f"Key rotation failed: {str(e)}")
            return False
    
    def schedule_key_rotation(self, interval_days=90):
        """
        Schedule automatic key rotation
        
        Args:
            interval_days: Rotation interval in days
        """
        try:
            # Get last rotation time from key file
            key_file_path = self.encryption_manager.key_file_path
            
            if os.path.exists(key_file_path):
                with open(key_file_path, 'r') as f:
                    key_data = json.load(f)
                
                last_rotation_str = key_data.get('last_rotation')
                if last_rotation_str:
                    last_rotation = datetime.fromisoformat(last_rotation_str)
                    
                    # Check if rotation is due
                    if datetime.utcnow() - last_rotation > timedelta(days=interval_days):
                        logger.info("Scheduled key rotation due")
                        return self.rotate_encryption_key()
                    else:
                        days_until_rotation = interval_days - (datetime.utcnow() - last_rotation).days
                        logger.info(f"Key rotation due in {days_until_rotation} days")
                        return True
                else:
                    logger.info("No previous rotation found, scheduling rotation")
                    return self.rotate_encryption_key()
            else:
                logger.warning("Key file not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to schedule key rotation: {str(e)}")
            return False
    
    def verify_key_integrity(self):
        """
        Verify the integrity of the current encryption key
        
        Returns:
            True if key is valid, False otherwise
        """
        try:
            # Test encryption/decryption
            test_data = "key_integrity_test_" + datetime.utcnow().isoformat()
            encrypted = self.encryption_manager.encrypt(test_data)
            decrypted = self.encryption_manager.decrypt(encrypted)
            
            if test_data != decrypted:
                logger.error("Key integrity test failed")
                return False
            
            # Check key file permissions
            key_file_path = self.encryption_manager.key_file_path
            if os.path.exists(key_file_path):
                stat = os.stat(key_file_path)
                permissions = oct(stat.st_mode)[-3:]
                
                if permissions != '600':
                    logger.warning(f"Key file permissions are not secure: {permissions}")
                    # Fix permissions
                    os.chmod(key_file_path, 0o600)
                    logger.info("Key file permissions fixed to 600")
            
            logger.info("Key integrity verified")
            return True
            
        except Exception as e:
            logger.error(f"Key integrity verification failed: {str(e)}")
            return False
    
    def cleanup_old_backups(self, keep_count=10):
        """
        Clean up old key backups, keeping only the most recent ones
        
        Args:
            keep_count: Number of recent backups to keep
        """
        try:
            backups = self.list_key_backups()
            
            if len(backups) > keep_count:
                # Remove oldest backups
                backups_to_remove = backups[keep_count:]
                
                for backup in backups_to_remove:
                    backup_path = backup.get('backup_path')
                    metadata_path = backup_path.replace('.json', '_metadata.json')
                    
                    try:
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                            logger.info(f"Removed old backup: {backup_path}")
                        
                        if os.path.exists(metadata_path):
                            os.remove(metadata_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove backup {backup_path}: {str(e)}")
                
                logger.info(f"Cleanup completed. Kept {keep_count} most recent backups")
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {str(e)}")
    
    def get_key_status(self):
        """
        Get comprehensive status of encryption keys
        
        Returns:
            Dictionary with key status information
        """
        try:
            key_info = self.encryption_manager.get_key_info()
            backups = self.list_key_backups()
            
            # Get last rotation info
            key_file_path = self.encryption_manager.key_file_path
            last_rotation = None
            
            if os.path.exists(key_file_path):
                with open(key_file_path, 'r') as f:
                    key_data = json.load(f)
                last_rotation_str = key_data.get('last_rotation')
                if last_rotation_str:
                    last_rotation = datetime.fromisoformat(last_rotation_str)
            
            status = {
                'key_info': key_info,
                'last_rotation': last_rotation.isoformat() if last_rotation else None,
                'backup_count': len(backups),
                'backups': backups[:5],  # Show 5 most recent
                'integrity_verified': self.verify_key_integrity(),
                'rotation_due': False
            }
            
            # Check if rotation is due
            if last_rotation:
                days_since_rotation = (datetime.utcnow() - last_rotation).days
                if days_since_rotation >= 90:
                    status['rotation_due'] = True
                    status['days_overdue'] = days_since_rotation - 90
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get key status: {str(e)}")
            return {'error': str(e)}

# Global key manager instance
_key_manager = None

def get_key_manager():
    """Get the global key manager instance"""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager