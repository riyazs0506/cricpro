# config.py — NEW FILE

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "devsecret123")

    # MySQL connection — UPDATE this according to your system
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI",
        "mysql+pymysql://root:123456@localhost/cricpro"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads (if needed for player images later)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
