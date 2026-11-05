from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db

class Account(db.Model):
    __tablename__ = 'accounts'

    vpa = db.Column(db.String(100), primary_key=True)
    holder_name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Numeric(precision=19, scale=2), nullable=False, default=Decimal('0.00'))
    version = db.Column(db.Integer, nullable=False, default=1) # Optimistic locking counter
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def credit(self, amount: Decimal):
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        self.balance = self.balance + amount
        self.version += 1

    def debit(self, amount: Decimal):
        if amount <= 0:
            raise ValueError("Debit amount must be positive")
        if self.balance < amount:
            raise ValueError("Insufficient balance")
        self.balance = self.balance - amount
        self.version += 1

    def to_dict(self):
        return {
            'vpa': self.vpa,
            'holderName': self.holder_name,
            'balance': float(self.balance),
            'version': self.version,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
