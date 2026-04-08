import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    APP_NAME = "Bitrix24 AI Resource"
    APP_HOST = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    APP_PORT = int(os.getenv("FLASK_RUN_PORT", "5000"))
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///site.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
