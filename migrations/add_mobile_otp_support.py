"""
Add Mobile OTP Support Migration

This migration adds support for mobile phone authentication using OTP via SMS.
It adds new fields to the users table and creates OTP-related tables.

Revision ID: add_mobile_otp_support
Revises: 
Create Date: 2025-12-26 06:17:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_mobile_otp_support'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Add mobile OTP support to the database"""
    
    # Add new columns to users table
    op.add_column('users', sa.Column('phone_verified', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('phone_verification_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('phone_verification_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('phone_verification_attempts', sa.Integer(), nullable=True, default=0))
    op.add_column('users', sa.Column('phone_verification_last_request', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('mobile_otp_enabled', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('backup_phone', sa.String(20), nullable=True))
    
    # Create OTP table
    op.create_table('otps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('otp_code', sa.String(6), nullable=False),
        sa.Column('otp_type', sa.String(20), nullable=False, default='login'),
        sa.Column('is_used', sa.Boolean(), nullable=True, default=False),
        sa.Column('attempts', sa.Integer(), nullable=True, default=0),
        sa.Column('max_attempts', sa.Integer(), nullable=True, default=3),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_otps_user_id', 'user_id'),
        sa.Index('ix_otps_phone', 'phone'),
        sa.Index('ix_otps_created_at', 'created_at')
    )
    
    # Create OTP Rate Limit table
    op.create_table('otp_rate_limits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False, unique=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=True, default=0),
        sa.Column('window_start', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('last_request', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('blocked_until', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_otp_rate_limits_phone', 'phone')
    )
    
    # Create indexes for better performance
    op.create_index('ix_users_phone_verified', 'users', ['phone_verified'])
    op.create_index('ix_users_mobile_otp_enabled', 'users', ['mobile_otp_enabled'])
    op.create_index('ix_otps_otp_type', 'otps', ['otp_type'])
    op.create_index('ix_otps_is_used', 'otps', ['is_used'])
    op.create_index('ix_otps_expires_at', 'otps', ['expires_at'])
    
    # Create foreign key constraint for users.phone
    op.create_foreign_key('fk_users_phone', 'users', 'users', ['phone'], ['phone'])
    
    print("Mobile OTP support migration completed successfully!")

def downgrade():
    """Remove mobile OTP support from the database"""
    
    # Drop foreign key constraint
    op.drop_constraint('fk_users_phone', 'users', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_users_phone_verified')
    op.drop_index('ix_users_mobile_otp_enabled')
    op.drop_index('ix_otps_otp_type')
    op.drop_index('ix_otps_is_used')
    op.drop_index('ix_otps_expires_at')
    op.drop_index('ix_otp_rate_limits_phone')
    
    # Drop tables
    op.drop_table('otp_rate_limits')
    op.drop_table('otps')
    
    # Remove columns from users table
    op.drop_column('users', 'backup_phone')
    op.drop_column('users', 'mobile_otp_enabled')
    op.drop_column('users', 'phone_verification_last_request')
    op.drop_column('users', 'phone_verification_attempts')
    op.drop_column('users', 'phone_verification_expires')
    op.drop_column('users', 'phone_verification_token')
    op.drop_column('users', 'phone_verified')
    
    print("Mobile OTP support migration rolled back successfully!")