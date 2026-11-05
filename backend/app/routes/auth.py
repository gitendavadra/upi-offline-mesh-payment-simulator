from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.services.crypto_service import crypto_service
from decimal import Decimal
import re

auth_bp = Blueprint('auth', __name__)

def is_valid_email(email: str) -> bool:
    return re.match(r"^[^@]+@[^@]+\.[^@]+$", email) is not None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('auth/register.html')

    data = request.get_json(silent=True) or request.form.to_dict()
    username = data.get('username', '').strip().lower()
    email = data.get('email', '').strip().lower()
    full_name = data.get('full_name', '').strip()
    password = data.get('password', '')
    confirm = data.get('confirm_password', '')
    role = data.get('role', 'USER').upper()

    if not username or len(username) < 3:
        err = "Username must be at least 3 characters long."
        return (jsonify({'error': err}), 400) if request.is_json else (flash(err, 'danger') or render_template('auth/register.html'))

    if not is_valid_email(email):
        err = "Please enter a valid email address."
        return (jsonify({'error': err}), 400) if request.is_json else (flash(err, 'danger') or render_template('auth/register.html'))

    if not password or len(password) < 6:
        err = "Password must be at least 6 characters long."
        return (jsonify({'error': err}), 400) if request.is_json else (flash(err, 'danger') or render_template('auth/register.html'))

    if password != confirm:
        err = "Passwords do not match."
        return (jsonify({'error': err}), 400) if request.is_json else (flash(err, 'danger') or render_template('auth/register.html'))

    if User.query.filter_by(username=username).first():
        err = "Username already taken."
        return (jsonify({'error': err}), 400) if request.is_json else (flash(err, 'danger') or render_template('auth/register.html'))

    if User.query.filter_by(email=email).first():
        err = "Email already registered."
        return (jsonify({'error': err}), 400) if request.is_json else (flash(err, 'danger') or render_template('auth/register.html'))

    # Generate RSA-2048 signing keypair for user's phone
    private_pem, public_pem = crypto_service.generate_sender_keypair()
    vpa = f"{username}@demo"

    user = User(
        username=username,
        email=email,
        full_name=full_name or username.title(),
        role='ADMIN' if role == 'ADMIN' else 'USER',
        vpa=vpa,
        public_key_pem=public_pem,
        private_key_pem=private_pem
    )
    user.set_password(password)
    db.session.add(user)

    # Automatically create user's simulated account
    if not Account.query.filter_by(vpa=vpa).first():
        account = Account(
            vpa=vpa,
            holder_name=user.full_name,
            balance=Decimal('2500.00'),
            user_id=user.id
        )
        db.session.add(account)

    AuditLog.log(
        event_type='USER_REGISTERED',
        actor=username,
        details=f"New user {username} ({vpa}) registered with role {user.role}",
        severity='INFO'
    )
    db.session.commit()

    login_user(user)

    if request.is_json:
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201

    flash('Registration successful! Welcome to UPI Offline Mesh.', 'success')
    return redirect(url_for('dashboard.index'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')

    data = request.get_json(silent=True) or request.form.to_dict()
    username_or_email = data.get('username_or_email', '').strip().lower()
    password = data.get('password', '')

    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if not user or not user.check_password(password):
        err = "Invalid username/email or password."
        AuditLog.log(
            event_type='AUTH_FAILED',
            actor=username_or_email or 'ANONYMOUS',
            details="Failed login attempt",
            severity='WARNING'
        )
        db.session.commit()
        return (jsonify({'error': err}), 401) if request.is_json else (flash(err, 'danger') or render_template('auth/login.html'))

    login_user(user, remember=True)
    AuditLog.log(
        event_type='AUTH_SUCCESS',
        actor=user.username,
        details=f"User {user.username} logged in successfully",
        severity='INFO'
    )
    db.session.commit()

    if request.is_json:
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        })

    flash(f"Welcome back, {user.full_name}!", 'success')
    return redirect(url_for('dashboard.index'))

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    actor = current_user.username if current_user.is_authenticated else 'ANONYMOUS'
    logout_user()
    AuditLog.log(
        event_type='AUTH_LOGOUT',
        actor=actor,
        details="User logged out",
        severity='INFO'
    )
    db.session.commit()

    if request.is_json:
        return jsonify({'message': 'Logged out successfully'})

    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    if not current_user.is_authenticated:
        return jsonify({'authenticated': False}), 200

    account = Account.query.filter_by(vpa=current_user.vpa).first()
    return jsonify({
        'authenticated': True,
        'user': current_user.to_dict(),
        'balance': float(account.balance) if account else 0.0
    })
