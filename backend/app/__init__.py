import os
from decimal import Decimal
from flask import Flask, jsonify
from app.config import config_by_name
from app.extensions import db, login_manager, csrf
from app.models.user import User
from app.models.account import Account
from app.services.mesh_service import mesh_service
from app.services.crypto_service import crypto_service

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_name='development'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Ensure instance directory exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.payments import payments_bp
    from app.routes.transactions import transactions_bp
    from app.routes.network import network_bp
    from app.routes.sync import sync_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(payments_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(network_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(admin_bp)

    # Disable CSRF for API endpoints so JSON fetch / automated clients work seamlessly
    csrf.init_app(app)
    csrf.exempt(auth_bp)
    csrf.exempt(payments_bp)
    csrf.exempt(transactions_bp)
    csrf.exempt(network_bp)
    csrf.exempt(sync_bp)
    csrf.exempt(admin_bp)


    # Add CORS headers for Vite frontend proxy
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Bridge-Node-Id,X-Hop-Count'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        return response

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Resource not found', 'status': 404}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'status': 500}), 500

    # Auto-seed database tables and initial demo entities
    with app.app_context():
        db.create_all()
        if app.config.get('DEMO_SEED', True):
            _seed_initial_data()

    return app

def _seed_initial_data():
    """Seeds baseline accounts and devices if the database is fresh."""
    # 1. Accounts
    default_accounts = [
        ('alice@demo', 'Alice Sharma', Decimal('5000.00')),
        ('bob@demo', 'Bob Verma', Decimal('1000.00')),
        ('carol@demo', 'Carol Sen', Decimal('2500.00')),
        ('dave@demo', 'Dave Nair', Decimal('500.00'))
    ]

    for vpa, name, balance in default_accounts:
        if not Account.query.filter_by(vpa=vpa).first():
            acc = Account(vpa=vpa, holder_name=name, balance=balance)
            db.session.add(acc)

    # 2. Users (alice, admin)
    if not User.query.filter_by(username='alice').first():
        priv_pem, pub_pem = crypto_service.generate_sender_keypair()
        alice_user = User(
            username='alice',
            email='alice@example.com',
            full_name='Alice Sharma',
            role='USER',
            vpa='alice@demo',
            public_key_pem=pub_pem,
            private_key_pem=priv_pem
        )
        alice_user.set_password('alice123')
        db.session.add(alice_user)

    if not User.query.filter_by(username='admin').first():
        priv_pem, pub_pem = crypto_service.generate_sender_keypair()
        admin_user = User(
            username='admin',
            email='admin@demo.bank',
            full_name='System Administrator',
            role='ADMIN',
            vpa='admin@demo',
            public_key_pem=pub_pem,
            private_key_pem=priv_pem
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)

    # 3. Seed Mesh Devices
    mesh_service.seed_default_devices()

    db.session.commit()
