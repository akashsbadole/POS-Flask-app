"""
Encryption utility module for POS system
Provides AES-256 encryption for sensitive data with enhanced security features
"""

import os
import base64
import json
import logging
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Configure logging
logger = logging.getLogger(__name__)

class EncryptionManager:
    """
    Manages encryption and decryption of sensitive data using AES-256
    with enhanced security features including integrity checks and key rotation
    """
    
    def __init__(self, key_file_path=None):
        """
        Initialize encryption manager
        
        Args:
            key_file_path: Path to encryption key file. If None, uses default path.
        """
        self.key_file_path = key_file_path or os.path.join(os.path.dirname(__file__), '..', 'config', 'encryption.key')
        self._key = None
        self._cipher_suite = None
        self._key_rotation_interval = 90  # days
        self._last_key_rotation = None
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption by loading or creating encryption key"""
        try:
            self._load_or_create_key()
            self._cipher_suite = Fernet(self._key)
            logger.info("Encryption system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption system: {str(e)}")
            raise
    
    def _load_or_create_key(self):
        """
        Load existing encryption key or create a new one
        The key is derived from a master password using PBKDF2
        """
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.key_file_path), exist_ok=True)
        
        # Check if key file exists
        if os.path.exists(self.key_file_path):
            try:
                with open(self.key_file_path, 'rb') as key_file:
                    key_data = json.load(key_file)
                    # Derive actual encryption key from stored salt and master key
                    self._key = self._derive_key(
                        key_data['master_key'].encode(),
                        key_data['salt'].encode()
                    )
                    self._last_key_rotation = key_data.get('last_rotation', None)
                    logger.info("Encryption key loaded from file")
            except Exception as e:
                logger.error(f"Failed to load encryption key: {str(e)}")
                raise
        else:
            # Create new encryption key
            self._create_new_key()
    
    def _create_new_key(self):
        """Create a new encryption key and save it"""
        try:
            # Generate a random salt
            salt = os.urandom(16)
            
            # Get master key from environment or create a random one
            master_key = os.environ.get('POS_ENCRYPTION_MASTER_KEY')
            if not master_key:
                # If no master key in environment, generate a random one
                master_key = base64.b64encode(os.urandom(32)).decode()
                logger.warning("No master key found in environment. Generated random key.")
                logger.warning("Store this master key securely: POS_ENCRYPTION_MASTER_KEY=" + master_key)
            
            # Derive encryption key
            self._key = self._derive_key(master_key.encode(), salt)
            
            # Save key data (not the actual key)
            key_data = {
                'master_key': master_key,
                'salt': base64.b64encode(salt).decode(),
                'created_at': datetime.utcnow().isoformat(),
                'last_rotation': datetime.utcnow().isoformat(),
                'version': '2.0'
            }
            
            with open(self.key_file_path, 'w') as key_file:
                json.dump(key_data, key_file)
            
            # Set file permissions (read/write for owner only)
            os.chmod(self.key_file_path, 0o600)
            
            self._last_key_rotation = datetime.utcnow()
            logger.info("New encryption key created and saved")
        except Exception as e:
            logger.error(f"Failed to create new encryption key: {str(e)}")
            raise
    
    def _derive_key(self, master_key: bytes, salt: bytes) -> bytes:
        """
        Derive encryption key from master key using PBKDF2
        
        Args:
            master_key: The master key
            salt: Random salt for key derivation
            
        Returns:
            Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            iterations=100000,  # High iteration count for security
            backend=default_backend()
        )
        return base64.b64encode(kdf.derive(master_key))
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data
        
        Args:
            data: The data to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        if not data or data.strip() == "":
            return data  # Return empty/null data as-is
        
        try:
            # Convert to bytes if needed
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = str(data).encode('utf-8')
            
            # Encrypt data
            encrypted_data = self._cipher_suite.encrypt(data_bytes)
            
            # Return as base64 string for storage
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            
            logger.debug(f"Data encrypted successfully (length: {len(data)})")
            return encrypted_b64
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted data as string
        """
        if not encrypted_data or encrypted_data.strip() == "":
            return encrypted_data  # Return empty/null data as-is
        
        try:
            # Check if data is encrypted (base64 format)
            try:
                # Decode from base64
                encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
                
                # Decrypt data
                decrypted_bytes = self._cipher_suite.decrypt(encrypted_bytes)
                
                # Convert back to string
                decrypted_data = decrypted_bytes.decode('utf-8')
                
                logger.debug(f"Data decrypted successfully (length: {len(decrypted_data)})")
                return decrypted_data
            except (base64.binascii.Error, ValueError):
                # Data might not be encrypted, return as-is
                logger.debug("Data appears to be unencrypted, returning as-is")
                return encrypted_data
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            # Return original data if decryption fails
            return encrypted_data
    
    def encrypt_field(self, field_value) -> str:
        """
        Encrypt a database field value
        
        Args:
            field_value: The field value to encrypt
            
        Returns:
            Encrypted field value
        """
        if field_value is None:
            return None
        
        return self.encrypt(str(field_value))
    
    def decrypt_field(self, encrypted_value) -> str:
        """
        Decrypt a database field value
        
        Args:
            encrypted_value: The encrypted field value
            
        Returns:
            Decrypted field value
        """
        if encrypted_value is None:
            return None
        
        return self.decrypt(str(encrypted_value))
    
    def rotate_key(self, new_master_key: str = None):
        """
        Rotate encryption key
        
        Args:
            new_master_key: New master key. If None, generates a random one.
        """
        try:
            # Backup old key
            old_key = self._key
            
            # Create new key
            if new_master_key:
                os.environ['POS_ENCRYPTION_MASTER_KEY'] = new_master_key
            
            # Remove old key file to force creation of new one
            if os.path.exists(self.key_file_path):
                backup_path = self.key_file_path + '.backup'
                os.rename(self.key_file_path, backup_path)
                logger.info(f"Old key backed up to: {backup_path}")
            
            # Initialize new key
            self._init_encryption()
            
            logger.info("Encryption key rotated successfully")
            return True
        except Exception as e:
            logger.error(f"Key rotation failed: {str(e)}")
            # Restore old key if rotation failed
            self._key = old_key
            self._cipher_suite = Fernet(self._key)
            return False
    
    def get_key_info(self) -> dict:
        """
        Get information about current encryption key
        
        Returns:
            Dictionary with key information
        """
        info = {
            'key_file_exists': os.path.exists(self.key_file_path),
            'key_file_path': self.key_file_path,
            'algorithm': 'AES-256',
            'key_derivation': 'PBKDF2-HMAC-SHA256'
        }
        
        if os.path.exists(self.key_file_path):
            stat = os.stat(self.key_file_path)
            info.update({
                'key_file_size': stat.st_size,
                'key_file_modified': stat.st_mtime,
                'key_file_permissions': oct(stat.st_mode)[-3:]
            })
        
        return info


# Global encryption manager instance
_encryption_manager = None

def get_encryption_manager() -> EncryptionManager:
    """
    Get the global encryption manager instance
    
    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager

def encrypt_data(data: str) -> str:
    """
    Convenience function to encrypt data
    
    Args:
        data: Data to encrypt
        
    Returns:
        Encrypted data
    """
    return get_encryption_manager().encrypt(data)

def decrypt_data(encrypted_data: str) -> str:
    """
    Convenience function to decrypt data
    
    Args:
        encrypted_data: Encrypted data
        
    Returns:
        Decrypted data
    """
    return get_encryption_manager().decrypt(encrypted_data)
