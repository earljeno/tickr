import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Database configuration
    database_url = os.getenv("DATABASE_URL")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME")

    if database_url:
        # Standardize modern postgres URL scheme if used
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = database_url
    elif db_user and db_name:
        db_pass_part = f":{db_pass}" if db_pass else ""
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+mysqlconnector://{db_user}{db_pass_part}@{db_host}/{db_name}"
        )
    else:
        # Graceful SQLite fallback for local development without MySQL server
        sqlite_path = os.path.join(basedir, "instance", "tickr.db")
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{sqlite_path}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session settings
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_LIFETIME_MINUTES", "60")))
    SESSION_FILE_DIR = os.path.join(basedir, "flask_session")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_TYPE = "null"  # Use standard Flask client sessions in tests


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
