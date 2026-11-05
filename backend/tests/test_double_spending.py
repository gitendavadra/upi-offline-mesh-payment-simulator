import pytest
from decimal import Decimal
from app.extensions import db
from app.models.account import Account
from app.services.sync_service import sync_service

def test_double_spending_demonstration_scenario(app):
    with app.app_context():
        res = sync_service.simulate_double_spending()

        assert res['isConsistent'] is True
        assert res['transactionA']['outcome'] == 'SETTLED'
        assert res['transactionB']['outcome'] == 'REJECTED'

        # Check ending balances
        alice = Account.query.filter_by(vpa='alice@demo').first()
        bob = Account.query.filter_by(vpa='bob@demo').first()
        carol = Account.query.filter_by(vpa='carol@demo').first()

        assert alice.balance == Decimal('200.00'), f"Alice balance is {alice.balance}, expected 200.00"
        assert alice.balance >= 0, "Account balance cannot be negative"
        assert res['finalState']['aliceBalance'] == 200.0
