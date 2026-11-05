from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    packet_hash = db.Column(db.String(64), unique=True, nullable=False, index=True) # SHA-256 of ciphertext
    idempotency_key = db.Column(db.String(64), unique=True, nullable=True, index=True) # Nonce UUID
    sender_vpa = db.Column(db.String(100), nullable=False, index=True)
    receiver_vpa = db.Column(db.String(100), nullable=False, index=True)
    amount = db.Column(db.Numeric(precision=19, scale=2), nullable=False)
    signed_at = db.Column(db.DateTime, nullable=False)
    settled_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    bridge_node_id = db.Column(db.String(100), nullable=False, default='direct-gateway')
    hop_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default='SETTLED')
    # Statuses: SETTLED, REJECTED, DUPLICATE_DROPPED, REQUIRES_REVIEW, INVALID
    rejection_reason = db.Column(db.String(255), nullable=True)
    signature = db.Column(db.Text, nullable=True)
    signature_valid = db.Column(db.Boolean, default=True)
    is_offline_origin = db.Column(db.Boolean, default=True)
    reconciliation_notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'packetHash': self.packet_hash,
            'idempotencyKey': self.idempotency_key,
            'senderVpa': self.sender_vpa,
            'receiverVpa': self.receiver_vpa,
            'amount': float(self.amount),
            'signedAt': self.signed_at.isoformat() if self.signed_at else None,
            'settledAt': self.settled_at.isoformat() if self.settled_at else None,
            'bridgeNodeId': self.bridge_node_id,
            'hopCount': self.hop_count,
            'status': self.status,
            'rejectionReason': self.rejection_reason,
            'signatureValid': self.signature_valid,
            'isOfflineOrigin': self.is_offline_origin,
            'reconciliationNotes': self.reconciliation_notes
        }
