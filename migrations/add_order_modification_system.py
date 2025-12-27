"""
Database Migration: Add Order Modification System
Creates tables and relationships for the comprehensive order modification system
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Upgrade database to add order modification system"""
    
    # Create order_modifications table
    op.create_table('order_modifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('modification_id', sa.String(50), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('modification_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('original_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('modified_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('price_difference', sa.Numeric(10, 2), nullable=True),
        sa.Column('refund_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('requested_by_user_id', sa.Integer(), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('customer_reason', sa.Text(), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=True),
        sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('auto_approved', sa.Boolean(), nullable=True),
        sa.Column('implemented_by_user_id', sa.Integer(), nullable=True),
        sa.Column('implemented_at', sa.DateTime(), nullable=True),
        sa.Column('implementation_notes', sa.Text(), nullable=True),
        sa.Column('request_time', sa.DateTime(), nullable=True),
        sa.Column('response_time', sa.DateTime(), nullable=True),
        sa.Column('completion_time', sa.DateTime(), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['implemented_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('modification_id')
    )
    
    # Create order_item_modifications table
    op.create_table('order_item_modifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('modification_id', sa.Integer(), nullable=False),
        sa.Column('order_item_id', sa.Integer(), nullable=True),
        sa.Column('original_menu_item_id', sa.Integer(), nullable=False),
        sa.Column('new_menu_item_id', sa.Integer(), nullable=True),
        sa.Column('original_quantity', sa.Integer(), nullable=False),
        sa.Column('new_quantity', sa.Integer(), nullable=False),
        sa.Column('original_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('new_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('price_difference', sa.Numeric(10, 2), nullable=True),
        sa.Column('modification_type', sa.String(50), nullable=False),
        sa.Column('original_instructions', sa.Text(), nullable=True),
        sa.Column('new_instructions', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('applied_by_user_id', sa.Integer(), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['applied_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['modification_id'], ['order_modifications.id'], ),
        sa.ForeignKeyConstraint(['new_menu_item_id'], ['menu_items.id'], ),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], ),
        sa.ForeignKeyConstraint(['original_menu_item_id'], ['menu_items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create modification_requests table
    op.create_table('modification_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(50), nullable=False),
        sa.Column('modification_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('estimated_completion_time', sa.Integer(), nullable=True),
        sa.Column('current_approver_role', sa.String(50), nullable=True),
        sa.Column('auto_approval_enabled', sa.Boolean(), nullable=True),
        sa.Column('auto_approval_criteria', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('due_at', sa.DateTime(), nullable=True),
        sa.Column('escalation_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('notifications_sent', sa.Integer(), nullable=True),
        sa.Column('last_notification_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['modification_id'], ['order_modifications.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_order_modifications_order_id', 'order_modifications', ['order_id'])
    op.create_index('idx_order_modifications_status', 'order_modifications', ['status'])
    op.create_index('idx_order_modifications_requested_by', 'order_modifications', ['requested_by_user_id'])
    op.create_index('idx_order_modifications_type', 'order_modifications', ['modification_type'])
    op.create_index('idx_order_modifications_created', 'order_modifications', ['requested_at'])
    
    op.create_index('idx_order_item_modifications_modification_id', 'order_item_modifications', ['modification_id'])
    op.create_index('idx_order_item_modifications_order_item', 'order_item_modifications', ['order_item_id'])
    op.create_index('idx_order_item_modifications_status', 'order_item_modifications', ['status'])
    
    op.create_index('idx_modification_requests_modification_id', 'modification_requests', ['modification_id'])
    op.create_index('idx_modification_requests_order_id', 'modification_requests', ['order_id'])
    op.create_index('idx_modification_requests_status', 'modification_requests', ['status'])
    op.create_index('idx_modification_requests_priority', 'modification_requests', ['priority'])
    
    # Add constraints for valid values
    op.create_check_constraint('valid_modification_status', 'order_modifications', 
                             "status IN ('Pending', 'Approved', 'Rejected', 'In Progress', 'Completed', 'Failed', 'Cancelled')")
    
    op.create_check_constraint('valid_modification_type', 'order_modifications', 
                             "modification_type IN ('add_items', 'remove_items', 'modify_items', 'cancel_order', 'partial_cancel', 'kitchen_hold')")
    
    op.create_check_constraint('valid_priority', 'order_modifications', 
                             "priority IN ('low', 'normal', 'high', 'critical')")
    
    op.create_check_constraint('valid_item_modification_type', 'order_item_modifications', 
                             "modification_type IN ('add_item', 'remove_item', 'change_quantity', 'change_item', 'update_instructions')")
    
    op.create_check_constraint('valid_item_modification_status', 'order_item_modifications', 
                             "status IN ('Pending', 'Applied', 'Failed')")
    
    op.create_check_constraint('valid_request_status', 'modification_requests', 
                             "status IN ('Pending', 'Approved', 'Rejected', 'Expired', 'Escalated')")
    
    op.create_check_constraint('valid_request_type', 'modification_requests', 
                             "request_type IN ('customer_request', 'kitchen_request', 'manager_initiated')")
    
    op.create_check_constraint('valid_request_priority', 'modification_requests', 
                             "priority IN ('low', 'normal', 'high', 'critical')")
    
    # Add constraints for non-negative values
    op.create_check_constraint('non_negative_price_difference', 'order_modifications', 
                             "price_difference IS NOT NULL")
    
    op.create_check_constraint('non_negative_original_total', 'order_modifications', 
                             "original_total >= 0")
    
    op.create_check_constraint('non_negative_modified_total', 'order_modifications', 
                             "modified_total >= 0")
    
    op.create_check_constraint('non_negative_refund_amount', 'order_modifications', 
                             "refund_amount >= 0")
    
    op.create_check_constraint('non_negative_original_quantity', 'order_item_modifications', 
                             "original_quantity >= 0")
    
    op.create_check_constraint('non_negative_new_quantity', 'order_item_modifications', 
                             "new_quantity >= 0")
    
    op.create_check_constraint('non_negative_original_price', 'order_item_modifications', 
                             "original_price >= 0")
    
    op.create_check_constraint('non_negative_price_difference_item', 'order_item_modifications', 
                             "price_difference IS NOT NULL")
    
    # Add columns to payment_transaction table for modification tracking
    op.add_column('payment_transactions', sa.Column('modification_id', sa.Integer(), nullable=True))
    op.add_column('payment_transactions', sa.Column('refund_reason', sa.String(255), nullable=True))
    op.add_column('payment_transactions', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
    op.add_column('payment_transactions', sa.Column('cancellation_reason', sa.Text(), nullable=True))
    op.add_column('payment_transactions', sa.Column('cancelled_by', sa.Integer(), nullable=True))
    op.add_column('payment_transactions', sa.Column('gateway_refund_id', sa.String(100), nullable=True))
    
    # Add foreign key constraint for modification_id
    op.create_foreign_key('fk_payment_transaction_modification', 'payment_transactions', 'order_modifications',
                         ['modification_id'], ['id'])
    
    # Add foreign key constraint for cancelled_by
    op.create_foreign_key('fk_payment_transaction_cancelled_by', 'payment_transactions', 'users',
                         ['cancelled_by'], ['id'])
    
    # Create trigger function for updating order totals when modifications are completed
    op.execute("""
        CREATE OR REPLACE FUNCTION update_order_total_on_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.status = 'Completed' AND OLD.status != 'Completed' THEN
                UPDATE orders 
                SET grand_total = NEW.modified_total,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.order_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for order total updates
    op.execute("""
        CREATE TRIGGER trigger_update_order_total_on_modification
        AFTER UPDATE ON order_modifications
        FOR EACH ROW
        EXECUTE FUNCTION update_order_total_on_modification();
    """)
    
    # Create function for automatic status updates
    op.execute("""
        CREATE OR REPLACE FUNCTION update_modification_item_status()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.status = 'Applied' AND OLD.status = 'Pending' THEN
                -- Update related order item status if applicable
                IF NEW.order_item_id IS NOT NULL THEN
                    UPDATE order_items 
                    SET status = CASE 
                        WHEN NEW.modification_type = 'remove_item' THEN 'Cancelled'
                        ELSE status
                    END,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.order_item_id;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for item status updates
    op.execute("""
        CREATE TRIGGER trigger_update_modification_item_status
        AFTER UPDATE ON order_item_modifications
        FOR EACH ROW
        EXECUTE FUNCTION update_modification_item_status();
    """)
    
    # Create view for modification summary
    op.execute("""
        CREATE VIEW modification_summary AS
        SELECT 
            om.id,
            om.modification_id,
            om.order_id,
            o.order_number,
            om.modification_type,
            om.status,
            om.price_difference,
            om.requested_by_user_id,
            u.username as requested_by_username,
            om.requested_at,
            om.approved_at,
            om.implemented_at,
            COUNT(oim.id) as item_modification_count,
            COUNT(CASE WHEN oim.status = 'Applied' THEN 1 END) as applied_items,
            COUNT(CASE WHEN oim.status = 'Failed' THEN 1 END) as failed_items
        FROM order_modifications om
        LEFT JOIN orders o ON om.order_id = o.id
        LEFT JOIN users u ON om.requested_by_user_id = u.id
        LEFT JOIN order_item_modifications oim ON om.id = oim.modification_id
        GROUP BY om.id, o.order_number, u.username;
    """)
    
    # Insert default modification settings
    op.execute("""
        INSERT INTO settings (key, value, description)
        VALUES 
        ('modification_auto_approval_enabled', 'false', 'Enable automatic approval for small modifications'),
        ('modification_auto_approval_threshold', '10.00', 'Maximum amount for automatic approval (INR)'),
        ('modification_time_limit_minutes', '30', 'Time limit for modifications after order is sent to kitchen'),
        ('modification_max_items_per_request', '10', 'Maximum number of items that can be modified in a single request'),
        ('modification_refund_processing_time', '24', 'Expected time for refund processing (hours)'),
        ('modification_notification_enabled', 'true', 'Enable notifications for modification requests'),
        ('modification_kitchen_notification_enabled', 'true', 'Enable kitchen notifications for modifications')
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade():
    """Downgrade database to remove order modification system"""
    
    # Drop views
    op.drop_view('modification_summary', if_exists=True)
    
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS trigger_update_modification_item_status ON order_item_modifications")
    op.execute("DROP FUNCTION IF EXISTS update_modification_item_status()")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_order_total_on_modification ON order_modifications")
    op.execute("DROP FUNCTION IF EXISTS update_order_total_on_modification()")
    
    # Remove added columns from payment_transactions
    op.drop_constraint('fk_payment_transaction_cancelled_by', 'payment_transactions', type_='foreignkey')
    op.drop_constraint('fk_payment_transaction_modification', 'payment_transactions', type_='foreignkey')
    
    op.drop_column('payment_transactions', 'gateway_refund_id')
    op.drop_column('payment_transactions', 'cancelled_by')
    op.drop_column('payment_transactions', 'cancellation_reason')
    op.drop_column('payment_transactions', 'cancelled_at')
    op.drop_column('payment_transactions', 'refund_reason')
    op.drop_column('payment_transactions', 'modification_id')
    
    # Drop indexes
    op.drop_index('idx_modification_requests_priority', table_name='modification_requests')
    op.drop_index('idx_modification_requests_status', table_name='modification_requests')
    op.drop_index('idx_modification_requests_order_id', table_name='modification_requests')
    op.drop_index('idx_modification_requests_modification_id', table_name='modification_requests')
    
    op.drop_index('idx_order_item_modifications_status', table_name='order_item_modifications')
    op.drop_index('idx_order_item_modifications_order_item', table_name='order_item_modifications')
    op.drop_index('idx_order_item_modifications_modification_id', table_name='order_item_modifications')
    
    op.drop_index('idx_order_modifications_created', table_name='order_modifications')
    op.drop_index('idx_order_modifications_type', table_name='order_modifications')
    op.drop_index('idx_order_modifications_requested_by', table_name='order_modifications')
    op.drop_index('idx_order_modifications_status', table_name='order_modifications')
    op.drop_index('idx_order_modifications_order_id', table_name='order_modifications')
    
    # Drop tables
    op.drop_table('modification_requests')
    op.drop_table('order_item_modifications')
    op.drop_table('order_modifications')
    
    # Remove settings
    op.execute("""
        DELETE FROM settings 
        WHERE key IN (
            'modification_auto_approval_enabled',
            'modification_auto_approval_threshold', 
            'modification_time_limit_minutes',
            'modification_max_items_per_request',
            'modification_refund_processing_time',
            'modification_notification_enabled',
            'modification_kitchen_notification_enabled'
        )
    """)