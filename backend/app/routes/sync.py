from flask import Blueprint, request, jsonify, render_template
from app.models.offline_queue import OfflineQueueItem
from app.services.sync_service import sync_service

sync_bp = Blueprint('sync', __name__)

@sync_bp.route('/queue/offline')
def queue_page():
    return render_template('queue/offline.html')

@sync_bp.route('/conflicts/double-spend')
def double_spend_page():
    return render_template('conflicts/double_spend.html')

@sync_bp.route('/api/sync/queue', methods=['GET'])
def list_queue():
    items = OfflineQueueItem.query.order_by(OfflineQueueItem.id.desc()).all()
    return jsonify({
        'total': len(items),
        'items': [i.to_dict() for i in items]
    })

@sync_bp.route('/api/sync/run', methods=['POST'])
def run_sync():
    limit = int(request.args.get('limit', 50))
    res = sync_service.sync_pending_queue(limit=limit)
    return jsonify(res)

@sync_bp.route('/api/sync/double-spend-demo', methods=['POST'])
def double_spend_demo():
    res = sync_service.simulate_double_spending()
    return jsonify(res)
