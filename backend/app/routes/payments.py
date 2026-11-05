from flask import Blueprint, request, jsonify, render_template
from decimal import Decimal
import logging
from app.extensions import db
from app.models.account import Account
from app.services.crypto_service import crypto_service
from app.services.payment_service import payment_service
from app.services.mesh_service import mesh_service
from app.services.security_service import security_service

logger = logging.getLogger(__name__)
payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/payments/send')
def send_page():
    return render_template('payments/send.html')

@payments_bp.route('/api/server-key', methods=['GET'])
def get_server_key():
    return jsonify({
        'publicKey': crypto_service.get_server_public_key_base64(),
        'publicKeyPem': crypto_service.get_server_public_key_pem(),
        'algorithm': 'RSA-2048 / OAEP-SHA256',
        'hybridScheme': 'RSA-OAEP encrypts an ephemeral AES-256-GCM session key',
        'signatureAlgorithm': 'RSA-PSS with SHA-256 for sender non-repudiation'
    })

@payments_bp.route('/api/demo/send', methods=['POST'])
def demo_send():
    """
    Simulates sender phone creating an encrypted payment instruction
    and injecting it into the mesh at the specified starting device.
    Matches original Java /api/demo/send contract.
    """
    data = request.get_json(force=True) or {}
    sender_vpa = data.get('senderVpa', 'alice@demo')
    receiver_vpa = data.get('receiverVpa', 'bob@demo')
    amount_str = str(data.get('amount', '500.00'))
    pin = str(data.get('pin', '1234'))
    ttl = int(data.get('ttl', 5))
    start_device = data.get('startDevice', 'phone-alice')

    try:
        amount = Decimal(amount_str)
        if amount <= Decimal('0.00'):
            return jsonify({'error': 'Amount must be greater than zero'}), 400

        packet = payment_service.create_mesh_packet(
            sender_vpa=sender_vpa,
            receiver_vpa=receiver_vpa,
            amount=amount,
            pin=pin,
            ttl=ttl
        )

        mesh_service.inject(start_device, packet)

        return jsonify({
            'packetId': packet['packetId'],
            'ciphertextPreview': packet['ciphertext'][:64] + "...",
            'ttl': packet['ttl'],
            'injectedAt': start_device,
            'signature': packet.get('signature')[:32] + "..." if packet.get('signature') else None
        }), 200

    except Exception as e:
        logger.error("demo_send error: %s", str(e), exc_info=True)
        return jsonify({'error': str(e)}), 400

@payments_bp.route('/api/payments/create', methods=['POST'])
def create_payment():
    """
    Standard payment creation supporting both direct online settlement
    and persistent offline queueing.
    """
    data = request.get_json(force=True) or {}
    sender_vpa = data.get('senderVpa')
    receiver_vpa = data.get('receiverVpa')
    amount_str = str(data.get('amount', '0'))
    pin = str(data.get('pin', '1234'))
    is_offline = bool(data.get('offline', False))

    if not sender_vpa or not receiver_vpa:
        return jsonify({'error': 'Both sender and receiver VPAs are required'}), 400

    try:
        amount = Decimal(amount_str)
        if amount <= Decimal('0.00'):
            return jsonify({'error': 'Amount must be positive'}), 400

        if is_offline:
            queue_item = payment_service.queue_offline_payment(
                sender_vpa=sender_vpa,
                receiver_vpa=receiver_vpa,
                amount=amount,
                pin=pin
            )
            return jsonify({
                'mode': 'OFFLINE_QUEUED',
                'queueId': queue_item.queue_id,
                'status': queue_item.status,
                'message': 'Payment packet encrypted and stored in durable offline queue'
            }), 201
        else:
            # Direct online settlement simulation
            packet = payment_service.create_mesh_packet(
                sender_vpa=sender_vpa,
                receiver_vpa=receiver_vpa,
                amount=amount,
                pin=pin
            )
            res = security_service.ingest_packet(packet, bridge_node_id='direct-online-gateway', hop_count=0)
            return jsonify({
                'mode': 'ONLINE_DIRECT',
                'outcome': res['outcome'],
                'packetHash': res['packetHash'],
                'transactionId': res.get('transactionId'),
                'reason': res.get('reason')
            }), 200

    except Exception as e:
        logger.error("create_payment error: %s", str(e), exc_info=True)
        return jsonify({'error': str(e)}), 400

@payments_bp.route('/api/bridge/ingest', methods=['POST'])
def bridge_ingest():
    """
    The production gateway endpoint.
    A bridge node with 4G/Wi-Fi uploads collected mesh packets here.
    Headers:
      X-Bridge-Node-Id: e.g. 'phone-bridge'
      X-Hop-Count: int
    """
    packet = request.get_json(force=True) or {}
    bridge_node_id = request.headers.get('X-Bridge-Node-Id', 'unknown-bridge')
    try:
        hop_count = int(request.headers.get('X-Hop-Count', 0))
    except ValueError:
        hop_count = 0

    res = security_service.ingest_packet(packet, bridge_node_id=bridge_node_id, hop_count=hop_count)
    return jsonify(res), 200
