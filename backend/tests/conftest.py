import pytest
import sys
from pathlib import Path
from decimal import Decimal

# Ensure project root is in sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from app import create_app
from app.extensions import db
from app.models.account import Account
from app.models.user import User
from app.models.device import Device
from app.services.mesh_service import mesh_service
from app.services.security_service import idempotency_cache

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Ensure fresh state
        mesh_service.reset_mesh()
        idempotency_cache.clear()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def test_accounts(app):
    """Provides standard test accounts with known starting balances."""
    with app.app_context():
        alice = Account.query.filter_by(vpa='alice@demo').first()
        if not alice:
            alice = Account(vpa='alice@demo', holder_name='Alice', balance=Decimal('5000.00'))
            db.session.add(alice)
        else:
            alice.balance = Decimal('5000.00')

        bob = Account.query.filter_by(vpa='bob@demo').first()
        if not bob:
            bob = Account(vpa='bob@demo', holder_name='Bob', balance=Decimal('1000.00'))
            db.session.add(bob)
        else:
            bob.balance = Decimal('1000.00')

        db.session.commit()
        return {'alice': alice, 'bob': bob}
