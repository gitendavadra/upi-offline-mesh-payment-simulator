from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.payments import payments_bp
from app.routes.transactions import transactions_bp
from app.routes.network import network_bp
from app.routes.sync import sync_bp
from app.routes.admin import admin_bp

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'payments_bp',
    'transactions_bp',
    'network_bp',
    'sync_bp',
    'admin_bp'
]
