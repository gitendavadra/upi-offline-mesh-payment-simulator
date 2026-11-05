from flask import Blueprint, request, jsonify, render_template
from flask_login import current_user
from app.models.transaction import Transaction

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/transactions')
def history_page():
    return render_template('transactions/history.html')

@transactions_bp.route('/api/transactions', methods=['GET'])
def list_transactions():
    """
    Returns transactions list with support for search, status filtering,
    and pagination. Defaults to 20 most recent to match Java demo.
    """
    status_filter = request.args.get('status')
    search = request.args.get('search')
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))

    query = Transaction.query

    # If logged in as normal user (and not admin), only show user's transactions
    if current_user.is_authenticated and not current_user.is_admin:
        query = query.filter(
            (Transaction.sender_vpa == current_user.vpa) |
            (Transaction.receiver_vpa == current_user.vpa)
        )

    if status_filter:
        query = query.filter(Transaction.status == status_filter.upper())

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Transaction.sender_vpa.ilike(search_pattern)) |
            (Transaction.receiver_vpa.ilike(search_pattern)) |
            (Transaction.packet_hash.ilike(search_pattern)) |
            (Transaction.bridge_node_id.ilike(search_pattern))
        )

    total = query.count()
    txs = query.order_by(Transaction.id.desc()).offset(offset).limit(limit).all()

    return jsonify({
        'total': total,
        'limit': limit,
        'offset': offset,
        'transactions': [tx.to_dict() for tx in txs]
    })

@transactions_bp.route('/api/transactions/<int:tx_id>', methods=['GET'])
def get_transaction(tx_id: int):
    tx = Transaction.query.get_or_404(tx_id)
    return jsonify(tx.to_dict())
