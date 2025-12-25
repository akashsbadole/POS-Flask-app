"""
Database migration script to encrypt existing sensitive data
Run this script once after implementing encryption to encrypt all existing sensitive data
"""

import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the path to import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_cloud.app import create_app
from web_cloud.models import db, User, Payment, Order, Settings
from web_cloud.utils.encryption import get_encryption_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def encrypt_existing_data():
    """Encrypt all existing sensitive data in the database"""
    app = create_app()
    
    with app.app_context():
        logger.info("Starting encryption of existing sensitive data...")
        
        try:
            # Initialize encryption manager
            encryption_manager = get_encryption_manager()
            logger.info("Encryption manager initialized")
            
            # Encrypt User model sensitive fields
            logger.info("Encrypting User model data...")
            users = User.query.all()
            for user in users:
                updated = False
                
                # Encrypt email if not already encrypted
                if user.email and not user.email.startswith('gAAAA'):
                    original_email = user.email
                    user.email = encryption_manager.encrypt_field(original_email)
                    updated = True
                    logger.info(f"Encrypted email for user: {user.username}")
                
                # Encrypt password hash if not already encrypted
                if user.password_hash and not user.password_hash.startswith('gAAAA'):
                    original_hash = user.password_hash
                    user.password_hash = encryption_manager.encrypt_field(original_hash)
                    updated = True
                    logger.info(f"Encrypted password hash for user: {user.username}")
                
                if updated:
                    db.session.add(user)
            
            # Encrypt Payment model sensitive fields
            logger.info("Encrypting Payment model data...")
            payments = Payment.query.all()
            for payment in payments:
                updated = False
                
                # Encrypt reference number if not already encrypted
                if payment.reference_number and not payment.reference_number.startswith('gAAAA'):
                    original_ref = payment.reference_number
                    payment.reference_number = encryption_manager.encrypt_field(original_ref)
                    updated = True
                    logger.info(f"Encrypted reference number for payment ID: {payment.id}")
                
                # Encrypt payment details if not already encrypted
                if payment.payment_details and not payment.payment_details.startswith('gAAAA'):
                    original_details = payment.payment_details
                    payment.payment_details = encryption_manager.encrypt_field(original_details)
                    updated = True
                    logger.info(f"Encrypted payment details for payment ID: {payment.id}")
                
                if updated:
                    db.session.add(payment)
            
            # Encrypt Order model sensitive fields
            logger.info("Encrypting Order model data...")
            orders = Order.query.all()
            for order in orders:
                updated = False
                
                # Encrypt customer name if not already encrypted
                if order.customer_name and not order.customer_name.startswith('gAAAA'):
                    original_name = order.customer_name
                    order.customer_name = encryption_manager.encrypt_field(original_name)
                    updated = True
                    logger.info(f"Encrypted customer name for order: {order.order_number}")
                
                # Encrypt customer mobile if not already encrypted
                if order.customer_mobile and not order.customer_mobile.startswith('gAAAA'):
                    original_mobile = order.customer_mobile
                    order.customer_mobile = encryption_manager.encrypt_field(original_mobile)
                    updated = True
                    logger.info(f"Encrypted customer mobile for order: {order.order_number}")
                
                if updated:
                    db.session.add(order)
            
            # Encrypt Settings model sensitive fields
            logger.info("Encrypting Settings model data...")
            sensitive_keys = [
                'sms_api_key',
                'restaurant_email',
                'restaurant_phone',
                'restaurant_address'
            ]
            
            for key in sensitive_keys:
                settings = Settings.query.filter_by(key=key).all()
                for setting in settings:
                    if setting.value and not setting.value.startswith('gAAAA'):
                        original_value = setting.value
                        setting.value = encryption_manager.encrypt_field(original_value)
                        db.session.add(setting)
                        logger.info(f"Encrypted value for setting: {key}")
            
            # Commit all changes
            db.session.commit()
            logger.info("All sensitive data has been encrypted successfully!")
            
            # Create a backup record of this migration
            migration_record = Settings(
                key='encryption_migration_completed',
                value=str(datetime.utcnow()),
                description='Timestamp when existing data was encrypted',
                is_public=False
            )
            db.session.add(migration_record)
            db.session.commit()
            
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during encryption migration: {str(e)}")
            db.session.rollback()
            raise

def verify_encryption():
    """Verify that sensitive data is properly encrypted"""
    app = create_app()
    
    with app.app_context():
        logger.info("Verifying encryption of sensitive data...")
        
        try:
            encryption_manager = get_encryption_manager()
            
            # Check User model
            users = User.query.all()
            for user in users:
                if user.email and not user.email.startswith('gAAAA'):
                    logger.warning(f"Unencrypted email found for user: {user.username}")
                
                if user.password_hash and not user.password_hash.startswith('gAAAA'):
                    logger.warning(f"Unencrypted password hash found for user: {user.username}")
            
            # Check Payment model
            payments = Payment.query.all()
            for payment in payments:
                if payment.reference_number and not payment.reference_number.startswith('gAAAA'):
                    logger.warning(f"Unencrypted reference number found for payment ID: {payment.id}")
                
                if payment.payment_details and not payment.payment_details.startswith('gAAAA'):
                    logger.warning(f"Unencrypted payment details found for payment ID: {payment.id}")
            
            # Check Order model
            orders = Order.query.all()
            for order in orders:
                if order.customer_name and not order.customer_name.startswith('gAAAA'):
                    logger.warning(f"Unencrypted customer name found for order: {order.order_number}")
                
                if order.customer_mobile and not order.customer_mobile.startswith('gAAAA'):
                    logger.warning(f"Unencrypted customer mobile found for order: {order.order_number}")
            
            # Check Settings model
            sensitive_keys = [
                'sms_api_key',
                'restaurant_email',
                'restaurant_phone',
                'restaurant_address'
            ]
            
            for key in sensitive_keys:
                settings = Settings.query.filter_by(key=key).all()
                for setting in settings:
                    if setting.value and not setting.value.startswith('gAAAA'):
                        logger.warning(f"Unencrypted value found for setting: {key}")
            
            logger.info("Encryption verification completed!")
            
        except Exception as e:
            logger.error(f"Error during encryption verification: {str(e)}")
            raise

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_encryption()
    else:
        encrypt_existing_data()