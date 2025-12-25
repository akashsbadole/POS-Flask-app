"""
Test script for encryption functionality
"""

import os
import sys
import unittest
import tempfile
import shutil
from datetime import datetime

# Add parent directory to path to import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.encryption import EncryptionManager, encrypt_data, decrypt_data

class TestEncryption(unittest.TestCase):
    """Test cases for encryption functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test encryption keys
        self.test_dir = tempfile.mkdtemp()
        self.key_file_path = os.path.join(self.test_dir, 'test_encryption.key')
        
        # Initialize encryption manager with test key file
        self.encryption_manager = EncryptionManager(self.key_file_path)
        
        # Set master key for testing
        os.environ['POS_ENCRYPTION_MASTER_KEY'] = 'test_master_key_12345'
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
        
        # Remove test master key from environment
        if 'POS_ENCRYPTION_MASTER_KEY' in os.environ:
            del os.environ['POS_ENCRYPTION_MASTER_KEY']
    
    def test_encrypt_decrypt_string(self):
        """Test basic string encryption and decryption"""
        original_data = "This is a test string with sensitive information"
        
        # Encrypt the data
        encrypted_data = self.encryption_manager.encrypt(original_data)
        
        # Verify encrypted data is different from original
        self.assertNotEqual(original_data, encrypted_data)
        self.assertTrue(encrypted_data.startswith('gAAAA'))  # Fernet encrypted data starts with this
        
        # Decrypt the data
        decrypted_data = self.encryption_manager.decrypt(encrypted_data)
        
        # Verify decrypted data matches original
        self.assertEqual(original_data, decrypted_data)
    
    def test_encrypt_empty_string(self):
        """Test encryption of empty string"""
        original_data = ""
        
        # Encrypt empty string
        encrypted_data = self.encryption_manager.encrypt(original_data)
        
        # Should return empty string as-is
        self.assertEqual(original_data, encrypted_data)
        
        # Decrypt empty string
        decrypted_data = self.encryption_manager.decrypt(encrypted_data)
        self.assertEqual(original_data, decrypted_data)
    
    def test_encrypt_none_value(self):
        """Test encryption of None value"""
        original_data = None
        
        # Encrypt None value
        encrypted_data = self.encryption_manager.encrypt(original_data)
        
        # Should return None as-is
        self.assertEqual(original_data, encrypted_data)
        
        # Decrypt None value
        decrypted_data = self.encryption_manager.decrypt(encrypted_data)
        self.assertEqual(original_data, decrypted_data)
    
    def test_encrypt_field(self):
        """Test field encryption"""
        original_value = "customer@example.com"
        
        # Encrypt field
        encrypted_field = self.encryption_manager.encrypt_field(original_value)
        
        # Verify encrypted field is different
        self.assertNotEqual(original_value, encrypted_field)
        
        # Decrypt field
        decrypted_field = self.encryption_manager.decrypt_field(encrypted_field)
        
        # Verify decrypted field matches original
        self.assertEqual(original_value, decrypted_field)
    
    def test_encrypt_numeric_values(self):
        """Test encryption of numeric values"""
        test_values = [
            1234567890,  # Phone number
            9876543210123456,  # Card number
            123.45,  # Decimal value
            0  # Zero
        ]
        
        for value in test_values:
            with self.subTest(value=value):
                # Encrypt numeric value
                encrypted_value = self.encryption_manager.encrypt_field(value)
                
                # Decrypt numeric value
                decrypted_value = self.encryption_manager.decrypt_field(encrypted_value)
                
                # Verify decrypted value matches original (as string)
                self.assertEqual(str(value), decrypted_value)
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        original_data = "Test data for convenience functions"
        
        # Test encrypt_data convenience function
        encrypted_data = encrypt_data(original_data)
        self.assertNotEqual(original_data, encrypted_data)
        
        # Test decrypt_data convenience function
        decrypted_data = decrypt_data(encrypted_data)
        self.assertEqual(original_data, decrypted_data)
    
    def test_key_rotation(self):
        """Test key rotation functionality"""
        original_data = "Test data for key rotation"
        
        # Encrypt with original key
        encrypted_data = self.encryption_manager.encrypt(original_data)
        
        # Verify decryption works with original key
        decrypted_data = self.encryption_manager.decrypt(encrypted_data)
        self.assertEqual(original_data, decrypted_data)
        
        # Rotate the key
        rotation_success = self.encryption_manager.rotate_key("new_test_master_key")
        self.assertTrue(rotation_success)
        
        # Try to decrypt with new key (should fail gracefully)
        decrypted_after_rotation = self.encryption_manager.decrypt(encrypted_data)
        # Should return original encrypted data if decryption fails
        self.assertEqual(encrypted_data, decrypted_after_rotation)
    
    def test_get_key_info(self):
        """Test key information retrieval"""
        key_info = self.encryption_manager.get_key_info()
        
        # Verify key info contains expected fields
        self.assertIn('key_file_exists', key_info)
        self.assertIn('key_file_path', key_info)
        self.assertIn('algorithm', key_info)
        self.assertIn('key_derivation', key_info)
        
        # Verify algorithm is AES-256
        self.assertEqual('AES-256', key_info['algorithm'])
        
        # Verify key derivation method
        self.assertEqual('PBKDF2-HMAC-SHA256', key_info['key_derivation'])
        
        # Verify key file exists
        self.assertTrue(key_info['key_file_exists'])
    
    def test_unencrypted_data_handling(self):
        """Test handling of unencrypted data"""
        unencrypted_data = "This is not encrypted"
        
        # Try to decrypt unencrypted data
        result = self.encryption_manager.decrypt(unencrypted_data)
        
        # Should return original data as-is
        self.assertEqual(unencrypted_data, result)
    
    def test_large_data_encryption(self):
        """Test encryption of large data"""
        # Create a large string (simulating long payment details)
        large_data = "A" * 10000  # 10KB of data
        
        # Encrypt large data
        encrypted_data = self.encryption_manager.encrypt(large_data)
        
        # Decrypt large data
        decrypted_data = self.encryption_manager.decrypt(encrypted_data)
        
        # Verify data integrity
        self.assertEqual(large_data, decrypted_data)
    
    def test_special_characters(self):
        """Test encryption of data with special characters"""
        special_data = "Test with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        # Encrypt special characters
        encrypted_data = self.encryption_manager.encrypt(special_data)
        
        # Decrypt special characters
        decrypted_data = self.encryption_manager.decrypt(encrypted_data)
        
        # Verify special characters are preserved
        self.assertEqual(special_data, decrypted_data)
    
    def test_unicode_characters(self):
        """Test encryption of Unicode characters"""
        unicode_data = "Test with Unicode: ñáéíóú 中文 العربية русский"
        
        # Encrypt Unicode characters
        encrypted_data = self.encryption_manager.encrypt(unicode_data)
        
        # Decrypt Unicode characters
        decrypted_data = self.encryption_manager.decrypt(encrypted_data)
        
        # Verify Unicode characters are preserved
        self.assertEqual(unicode_data, decrypted_data)


def run_encryption_tests():
    """Run all encryption tests"""
    print("Running encryption tests...")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEncryption)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall result: {'PASSED' if success else 'FAILED'}")
    
    return success


if __name__ == "__main__":
    run_encryption_tests()