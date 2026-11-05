from datetime import datetime, timezone
from app.extensions import db

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    actor = db.Column(db.String(100), nullable=False, default='SYSTEM')
    ip_address = db.Column(db.String(45), nullable=True)
    details = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), nullable=False, default='INFO') # 'INFO', 'WARNING', 'CRITICAL'

    @classmethod
    def log(cls, event_type: str, actor: str = 'SYSTEM', details: str = '', severity: str = 'INFO', ip_address: str = None):
        entry = cls(
            event_type=event_type,
            actor=actor,
            details=details,
            severity=severity,
            ip_address=ip_address
        )
        db.session.add(entry)
        # Note: caller will commit with unit of work or db.session.commit()
        return entry

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'eventType': self.event_type,
            'actor': self.actor,
            'ipAddress': self.ip_address,
            'details': self.details,
            'severity': self.severity
        }
