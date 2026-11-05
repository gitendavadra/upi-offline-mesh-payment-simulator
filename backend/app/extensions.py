from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from argon2 import PasswordHasher

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'
