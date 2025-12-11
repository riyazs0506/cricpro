# config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env (useful in local development)
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Secret key for session/cookies (override in production)
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_123")

    # Database connection
    # LOCAL default → MySQL
    # Render / Railway → will override using DATABASE_URL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",     # For hosting platforms → Render, Railway, etc.
        "mysql+pymysql://root:123456@localhost/cricpro"  # Local fallback
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Static uploads if needed
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False