# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_123")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",  # Railway uses DATABASE_URL
        "mysql+pymysql://root:123456@localhost/cricpro"  # Local fallback
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False