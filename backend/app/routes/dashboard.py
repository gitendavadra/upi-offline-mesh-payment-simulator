from flask import Blueprint, render_template, jsonify
from flask_login import current_user
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.offline_queue import OfflineQueueItem
from app.models.device import Device
from app.services.security_service import idempotency_cache
from app.services.mesh_service import mesh_service

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def index():
    return render_template('dashboard/index.html')

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
def get_stats():
    user_vpa = current_user.vpa if current_user.is_authenticated else 'alice@demo'
    user_account = Account.query.filter_by(vpa=user_vpa).first()

    total_accounts = Account.query.count()
    total_tx = Transaction.query.count()
    settled_tx = Transaction.query.filter_by(status='SETTLED').count()
    rejected_tx = Transaction.query.filter_by(status='REJECTED').count()
    requires_review_tx = Transaction.query.filter_by(status='REQUIRES_REVIEW').count()
    pending_queue_count = OfflineQueueItem.query.filter(
        OfflineQueueItem.status.in_(['PENDING_OFFLINE', 'READY_TO_SYNC', 'SYNCING'])
    ).count()

    devices = mesh_service.get_devices()
    total_packets_held = sum(d.packet_count() for d in devices)

    return jsonify({
        'userVpa': user_vpa,
        'simulatedBalance': float(user_account.balance) if user_account else 0.0,
        'holderName': user_account.holder_name if user_account else 'Guest',
        'totalTransactions': total_tx,
        'settledCount': settled_tx,
        'rejectedCount': rejected_tx,
        'requiresReviewCount': requires_review_tx,
        'pendingQueueCount': pending_queue_count,
        'idempotencyCacheSize': idempotency_cache.size(),
        'totalDevices': len(devices),
        'packetsInMesh': total_packets_held
    })
