import pytest
from decimal import Decimal
from app.extensions import db
from app.models.offline_queue import OfflineQueueItem
from app.models.account import Account
from app.services.payment_service import payment_service
from app.services.sync_service import sync_service

def test_offline_queue_creation_and_persistence(app, test_accounts):
    with app.app_context():
        item = payment_service.queue_offline_payment(
            sender_vpa='alice@demo',
            receiver_vpa='bob@demo',
            amount=Decimal('400.00'),
            pin='1234'
        )
        assert item.id is not None
        assert item.status == 'PENDING_OFFLINE'
        assert item.nonce is not None
        assert item.ciphertext is not None

        # Query back from DB
        saved = OfflineQueueItem.query.filter_by(queue_id=item.queue_id).first()
        assert saved is not None
        assert saved.amount == Decimal('400.00')

def test_offline_queue_state_transitions(app):
    with app.app_context():
        item = OfflineQueueItem(
            sender_vpa='alice@demo',
            receiver_vpa='bob@demo',
            amount=Decimal('100.00'),
            pin_hash='hash',
            nonce='nonce-1',
            ciphertext='cipher',
            status='CREATED'
        )
        db.session.add(item)
        db.session.commit()

        # Valid transition
        item.transition_to('PENDING_OFFLINE')
        assert item.status == 'PENDING_OFFLINE'

        item.transition_to('READY_TO_SYNC')
        assert item.status == 'READY_TO_SYNC'

        # Invalid transition directly to COMPLETED_SIMULATION
        with pytest.raises(ValueError):
            item.transition_to('COMPLETED_SIMULATION')

def test_sync_pending_queue(app, test_accounts):
    with app.app_context():
        # Queue 2 payments
        payment_service.queue_offline_payment(
            sender_vpa='alice@demo',
            receiver_vpa='bob@demo',
            amount=Decimal('200.00'),
            pin='1234'
        )
        payment_service.queue_offline_payment(
            sender_vpa='alice@demo',
            receiver_vpa='bob@demo',
            amount=Decimal('300.00'),
            pin='1234'
        )

        res = sync_service.sync_pending_queue()
        assert res['totalProcessed'] == 2
        assert res['syncedCount'] == 2

        alice = Account.query.filter_by(vpa='alice@demo').first()
        # 5000 - 200 - 300 = 4500
        assert alice.balance == Decimal('4500.00')
