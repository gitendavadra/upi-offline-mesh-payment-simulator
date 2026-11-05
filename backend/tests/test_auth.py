import pytest
from app.models.user import User
from app.models.account import Account

def test_user_registration(client, app):
    res = client.post('/auth/register', json={
        'username': 'rahul',
        'email': 'rahul@example.com',
        'full_name': 'Rahul Verma',
        'password': 'password123',
        'confirm_password': 'password123',
        'role': 'USER'
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['user']['username'] == 'rahul'
    assert data['user']['vpa'] == 'rahul@demo'

    # Verify user and account created in database
    with app.app_context():
        user = User.query.filter_by(username='rahul').first()
        assert user is not None
        assert user.check_password('password123')
        assert not user.check_password('wrongpass')
        assert user.public_key_pem is not None
        assert user.private_key_pem is not None

        acc = Account.query.filter_by(vpa='rahul@demo').first()
        assert acc is not None

def test_duplicate_registration_prevented(client):
    payload = {
        'username': 'priya',
        'email': 'priya@example.com',
        'full_name': 'Priya Sen',
        'password': 'password123',
        'confirm_password': 'password123'
    }
    res1 = client.post('/auth/register', json=payload)
    assert res1.status_code == 201

    res2 = client.post('/auth/register', json=payload)
    assert res2.status_code == 400
    assert 'already taken' in res2.get_json()['error']

def test_login_and_logout(client):
    # Register user first
    client.post('/auth/register', json={
        'username': 'kunal',
        'email': 'kunal@example.com',
        'full_name': 'Kunal Roy',
        'password': 'mypassword',
        'confirm_password': 'mypassword'
    })

    # Test login with wrong password
    bad_res = client.post('/auth/login', json={
        'username_or_email': 'kunal',
        'password': 'wrongpassword'
    })
    assert bad_res.status_code == 401

    # Test login with correct password
    good_res = client.post('/auth/login', json={
        'username_or_email': 'kunal',
        'password': 'mypassword'
    })
    assert good_res.status_code == 200
    assert good_res.get_json()['user']['username'] == 'kunal'

    # Verify session
    me_res = client.get('/auth/me')
    assert me_res.status_code == 200
    assert me_res.get_json()['authenticated'] is True
    assert me_res.get_json()['user']['username'] == 'kunal'

    # Logout
    logout_res = client.post('/auth/logout', json={})
    assert logout_res.status_code == 200


    # Verify session cleared
    me_after = client.get('/auth/me')
    assert me_after.get_json()['authenticated'] is False
