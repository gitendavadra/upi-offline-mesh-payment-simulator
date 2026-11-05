import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'upi-offline-mesh-simulation-super-secret-key-2025')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_PACKET_AGE_SECONDS = int(os.environ.get('MAX_PACKET_AGE_SECONDS', 86400))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    DEMO_SEED = os.environ.get('DEMO_SEED', 'true').lower() == 'true'

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI', f"sqlite:///{BASE_DIR / 'instance' / 'upi_offline.db'}"
    )

class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAX_PACKET_AGE_SECONDS = 86400

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI', f"sqlite:///{BASE_DIR / 'instance' / 'upi_offline_prod.db'}"
    )

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
