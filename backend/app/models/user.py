from datetime import datetime, timezone
from flask_login import UserMixin
from app.extensions import db, ph

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='USER', nullable=False) # 'USER' or 'ADMIN'
    vpa = db.Column(db.String(100), unique=True, nullable=False)
    public_key_pem = db.Column(db.Text, nullable=True) # Sender's RSA signing public key
    private_key_pem = db.Column(db.Text, nullable=True) # Held on sender device for demo signing
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active_user = db.Column(db.Boolean, default=True)

    def set_password(self, password: str):
        self.password_hash = ph.hash(password)

    def check_password(self, password: str) -> bool:
        try:
            return ph.verify(self.password_hash, password)
        except Exception:
            return False

    @property
    def is_admin(self) -> bool:
        return self.role == 'ADMIN'

    @property
    def is_active(self) -> bool:
        return self.is_active_user

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'vpa': self.vpa,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
