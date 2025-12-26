import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key_here")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:oMjTTmqBjCxuBXiEGUmQyngfKnaekmVt@centerbeam.proxy.rlwy.net:58790/railway"
       # "mysql+pymysql://root:123456@localhost/cricpro"
    )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    PAYMENT_SIMULATE = False