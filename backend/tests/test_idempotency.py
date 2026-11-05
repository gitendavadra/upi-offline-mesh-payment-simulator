import pytest
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from app.extensions import db
from app.models.account import Account
from app.models.transaction import Transaction
from app.services.payment_service import payment_service
from app.services.security_service import security_service, idempotency_cache

def test_single_packet_delivered_by_multiple_bridges_settles_exactly_once(app, test_accounts):
    """
    Core headline test:
    Simulates three bridge nodes delivering the exact same packet simultaneously.
    Asserts:
    - Exactly 1 delivery outcomes is 'SETTLED'
    - Exactly 2 delivery outcomes are 'DUPLICATE_DROPPED'
    - Alice is debited exactly once (₹300, not ₹900)
    """
    packet = payment_service.create_mesh_packet(
        sender_vpa='alice@demo',
        receiver_vpa='bob@demo',
        amount=Decimal('300.00'),
        pin='1234'
    )

    results = []

    def ingest_task(bridge_id):
        with app.app_context():
            return security_service.ingest_packet(
                packet=packet,
                bridge_node_id=bridge_id,
                hop_count=2
            )

    bridges = ['phone-bridge-1', 'phone-bridge-2', 'phone-bridge-3']
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(ingest_task, b) for b in bridges]
        for f in futures:
            results.append(f.result())

    outcomes = [r['outcome'] for r in results]
    settled_count = outcomes.count('SETTLED')
    duplicate_count = outcomes.count('DUPLICATE_DROPPED')

    assert settled_count == 1, f"Expected 1 SETTLED, got outcomes: {outcomes}"
    assert duplicate_count == 2, f"Expected 2 DUPLICATE_DROPPED, got outcomes: {outcomes}"

    with app.app_context():
        alice = Account.query.filter_by(vpa='alice@demo').first()
        bob = Account.query.filter_by(vpa='bob@demo').first()
        # Initial was 5000 and 1000. Exactly 300 transferred!
        assert alice.balance == Decimal('4700.00')
        assert bob.balance == Decimal('1300.00')

        # Check database records
        txs = Transaction.query.all()
        assert len(txs) == 1
        assert txs[0].status == 'SETTLED'
