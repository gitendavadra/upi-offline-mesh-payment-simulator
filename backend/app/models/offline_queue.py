from datetime import datetime, timezone
from decimal import Decimal
import uuid
from app.extensions import db

class OfflineQueueItem(db.Model):
    __tablename__ = 'offline_queue'

    id = db.Column(db.Integer, primary_key=True)
    queue_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    packet_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    sender_vpa = db.Column(db.String(100), nullable=False, index=True)
    receiver_vpa = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(precision=19, scale=2), nullable=False)
    pin_hash = db.Column(db.String(64), nullable=False)
    nonce = db.Column(db.String(64), nullable=False, unique=True)
    signed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    ciphertext = db.Column(db.Text, nullable=False)
    signature = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='PENDING_OFFLINE')
    # State transitions:
    # CREATED -> PENDING_OFFLINE -> READY_TO_SYNC -> SYNCING -> COMPLETED_SIMULATION
    # Or -> FAILED or -> REQUIRES_REVIEW
    attempts = db.Column(db.Integer, default=0, nullable=False)
    last_attempt_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    VALID_TRANSITIONS = {
        'CREATED': ['PENDING_OFFLINE', 'FAILED'],
        'PENDING_OFFLINE': ['READY_TO_SYNC', 'FAILED', 'SYNCING'],
        'READY_TO_SYNC': ['SYNCING', 'PENDING_OFFLINE', 'FAILED'],
        'SYNCING': ['COMPLETED_SIMULATION', 'FAILED', 'REQUIRES_REVIEW', 'READY_TO_SYNC'],
        'FAILED': ['READY_TO_SYNC'], # Can retry
        'REQUIRES_REVIEW': ['COMPLETED_SIMULATION', 'FAILED'],
        'COMPLETED_SIMULATION': [] # Terminal
    }

    def transition_to(self, new_status: str, reason: str = None):
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValueError(f"Invalid state transition from {self.status} to {new_status}")
        self.status = new_status
        if reason:
            self.error_message = reason
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            'id': self.id,
            'queueId': self.queue_id,
            'packetId': self.packet_id,
            'senderVpa': self.sender_vpa,
            'receiverVpa': self.receiver_vpa,
            'amount': float(self.amount),
            'nonce': self.nonce,
            'signedAt': self.signed_at.isoformat() if self.signed_at else None,
            'status': self.status,
            'attempts': self.attempts,
            'lastAttemptAt': self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            'errorMessage': self.error_message,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
