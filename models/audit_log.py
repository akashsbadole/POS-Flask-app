"""
Audit Log Model for tracking all workflow actions and system changes
"""

from datetime import datetime
from . import db


class AuditLog(db.Model):
    """Audit log model for tracking all system changes and workflow actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    
    # Action details
    action = db.Column(db.String(100), nullable=False)  # e.g., 'workflow_action', 'status_change'
    entity_type = db.Column(db.String(50), nullable=False)  # e.g., 'order', 'inventory_item', 'user'
    entity_id = db.Column(db.Integer, nullable=False)
    entity_name = db.Column(db.String(200), nullable=True)  # e.g., order number, item name
    
    # Status tracking
    previous_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=True)
    
    # Action data
    action_data = db.Column(db.Text, nullable=True)  # JSON string of action details
    result_data = db.Column(db.Text, nullable=True)  # JSON string of result details
    
    # Context information
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    user_agent = db.Column(db.Text, nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    
    # Timestamps
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs', lazy=True)
    
    def __init__(self, user_id=None, username=None, action=None, entity_type=None, 
                 entity_id=None, entity_name=None, previous_status=None, new_status=None,
                 action_data=None, result_data=None, ip_address=None, user_agent=None,
                 session_id=None):
        self.user_id = user_id
        self.username = username
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.previous_status = previous_status
        self.new_status = new_status
        self.action_data = action_data
        self.result_data = result_data
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.session_id = session_id
    
    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'entity_name': self.entity_name,
            'previous_status': self.previous_status,
            'new_status': self.new_status,
            'action_data': self.action_data,
            'result_data': self.result_data,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @staticmethod
    def log_action(user_id, username, action, entity_type, entity_id, entity_name=None,
                   previous_status=None, new_status=None, action_data=None, result_data=None,
                   ip_address=None, user_agent=None, session_id=None):
        """Log an action to audit trail"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                username=username,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                previous_status=previous_status,
                new_status=new_status,
                action_data=action_data,
                result_data=result_data,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id
            )
            db.session.add(audit_log)
            db.session.commit()
            return audit_log
        except Exception as e:
            # Log error but don't fail the main operation
            db.session.rollback()
            print(f"Failed to log audit action: {e}")
            return None
    
    @staticmethod
    def get_entity_logs(entity_type, entity_id, limit=50):
        """Get audit logs for specific entity"""
        return AuditLog.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_user_action_logs(user_id, action=None, limit=100):
        """Get action logs for specific user"""
        query = AuditLog.query.filter_by(user_id=user_id)
        if action:
            query = query.filter_by(action=action)
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_recent_logs(hours=24, action=None, entity_type=None):
        """Get recent audit logs with optional filters"""
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        query = AuditLog.query.filter(AuditLog.timestamp >= cutoff_time)
        
        if action:
            query = query.filter_by(action=action)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        
        return query.order_by(AuditLog.timestamp.desc()).all()
    
    @staticmethod
    def get_workflow_statistics(date_range=None):
        """Get workflow action statistics"""
        query = AuditLog.query.filter_by(action='workflow_action')
        
        if date_range:
            start_date, end_date = date_range
            query = query.filter(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            )
        
        logs = query.all()
        
        stats = {
            'total_actions': len(logs),
            'by_entity_type': {},
            'by_action_type': {},
            'by_user': {},
            'timeline': []
        }
        
        # Group by entity type
        for log in logs:
            entity_type = log.entity_type
            stats['by_entity_type'][entity_type] = stats['by_entity_type'].get(entity_type, 0) + 1
            
            # Group by action type
            action_type = f"{log.entity_type}.{log.action}"
            stats['by_action_type'][action_type] = stats['by_action_type'].get(action_type, 0) + 1
            
            # Group by user
            username = log.username or 'System'
            stats['by_user'][username] = stats['by_user'].get(username, 0) + 1
        
        # Create timeline (hourly breakdown)
        hourly_counts = {}
        for log in logs:
            hour_key = log.timestamp.strftime('%Y-%m-%d %H:00')
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
        
        stats['timeline'] = [{'hour': k, 'count': v} for k, v in sorted(hourly_counts.items())]
        
        return stats
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type}#{self.entity_id}>'