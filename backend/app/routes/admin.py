from flask import Blueprint, request, jsonify, render_template
from decimal import Decimal
from app.extensions import db
from app.models.account import Account
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.transaction import Transaction
from app.models.offline_queue import OfflineQueueItem
from app.services.mesh_service import mesh_service
from app.services.security_service import idempotency_cache

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
def admin_page():
    return render_template('admin/index.html')

@admin_bp.route('/api/accounts', methods=['GET'])
def list_accounts():
    """Returns all accounts and balances. Matches original Java endpoint."""
    accounts = Account.query.order_by(Account.vpa).all()
    return jsonify([a.to_dict() for a in accounts])

@admin_bp.route('/api/admin/users', methods=['GET'])
def list_users():
    users = User.query.order_by(User.id).all()
    return jsonify([u.to_dict() for u in users])

@admin_bp.route('/api/admin/audit-logs', methods=['GET'])
def list_audit_logs():
    limit = int(request.args.get('limit', 100))
    logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(limit).all()
    return jsonify([log.to_dict() for log in logs])

@admin_bp.route('/api/admin/reset-system', methods=['POST'])
def reset_system():
    """Resets demo accounts and flushes all caches and queues."""
    # Reset accounts
    default_accounts = [
        ('alice@demo', 'Alice', Decimal('5000.00')),
        ('bob@demo', 'Bob', Decimal('1000.00')),
        ('carol@demo', 'Carol', Decimal('2500.00')),
        ('dave@demo', 'Dave', Decimal('500.00'))
    ]

    for vpa, name, bal in default_accounts:
        acc = Account.query.filter_by(vpa=vpa).first()
        if acc:
            acc.balance = bal
            acc.version = 1
        else:
            acc = Account(vpa=vpa, holder_name=name, balance=bal)
            db.session.add(acc)

    # Clear mesh & idempotency
    mesh_service.reset_mesh()
    idempotency_cache.clear()

    # Clear transactions & offline queue
    Transaction.query.delete()
    OfflineQueueItem.query.delete()

    AuditLog.log(
        event_type='SYSTEM_RESET',
        actor='ADMIN',
        details="System state, account balances, and ledger history reset to baseline defaults",
        severity='WARNING'
    )
    db.session.commit()

    return jsonify({'status': 'System reset successfully to baseline state'})
