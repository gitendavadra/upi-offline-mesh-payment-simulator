import pytest
import time
from decimal import Decimal
from app.extensions import db
from app.models.account import Account
from app.models.transaction import Transaction
from app.services.payment_service import payment_service
from app.services.crypto_service import crypto_service

def test_successful_bridge_ingest_settles_payment(client, app, test_accounts):
    packet = payment_service.create_mesh_packet(
        sender_vpa='alice@demo',
        receiver_vpa='bob@demo',
        amount=Decimal('500.00'),
        pin='1234'
    )

    res = client.post(
        '/api/bridge/ingest',
        json=packet,
        headers={'X-Bridge-Node-Id': 'phone-bridge', 'X-Hop-Count': '2'}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['outcome'] == 'SETTLED'
    assert data['transactionId'] is not None

    with app.app_context():
        alice = Account.query.filter_by(vpa='alice@demo').first()
        bob = Account.query.filter_by(vpa='bob@demo').first()
        assert alice.balance == Decimal('4500.00')
        assert bob.balance == Decimal('1500.00')

        tx = db.session.get(Transaction, data['transactionId'])
        assert tx.status == 'SETTLED'
        assert tx.hop_count == 2
        assert tx.bridge_node_id == 'phone-bridge'

def test_insufficient_balance_returns_rejected(client, app, test_accounts):
    # Alice attempts to send 99999.00 (exceeds balance)
    packet = payment_service.create_mesh_packet(
        sender_vpa='alice@demo',
        receiver_vpa='bob@demo',
        amount=Decimal('99999.00'),
        pin='1234'
    )

    res = client.post('/api/bridge/ingest', json=packet)
    assert res.status_code == 200
    data = res.get_json()
    assert data['outcome'] == 'REJECTED'

    with app.app_context():
        alice = Account.query.filter_by(vpa='alice@demo').first()
        bob = Account.query.filter_by(vpa='bob@demo').first()
        assert alice.balance == Decimal('5000.00') # Unchanged
        assert bob.balance == Decimal('1000.00') # Unchanged

def test_tampered_packet_is_rejected_as_invalid(client, app):
    packet = payment_service.create_mesh_packet(
        sender_vpa='alice@demo',
        receiver_vpa='bob@demo',
        amount=Decimal('100.00'),
        pin='1234'
    )

    # Corrupt the ciphertext
    ct = packet['ciphertext']
    corrupted_ct = ct[:30] + ('A' if ct[30] != 'A' else 'B') + ct[31:]
    packet['ciphertext'] = corrupted_ct

    res = client.post('/api/bridge/ingest', json=packet)
    assert res.status_code == 200
    data = res.get_json()
    assert data['outcome'] == 'INVALID'
    assert 'decryption_failed' in data['reason']

def test_stale_packet_is_rejected(client, app):
    # Instruction signed 48 hours ago
    old_time = int((time.time() - 48 * 3600) * 1000)
    instruction = {
        'senderVpa': 'alice@demo',
        'receiverVpa': 'bob@demo',
        'amount': '100.00',
        'pinHash': crypto_service.hash_pin('1234'),
        'nonce': 'old-nonce-48h',
        'signedAt': old_time
    }
    ciphertext = crypto_service.encrypt(instruction)

    packet = {
        'packetId': 'old-packet',
        'ciphertext': ciphertext
    }

    res = client.post('/api/bridge/ingest', json=packet)
    assert res.status_code == 200
    data = res.get_json()
    assert data['outcome'] == 'INVALID'
    assert data['reason'] == 'stale_packet'
