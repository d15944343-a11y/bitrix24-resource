from flask import Flask

from config import Config
from .extensions import db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from .routes import main_bp
    from . import models

    app.register_blueprint(main_bp)

    @app.cli.command("init-db")
    def init_db() -> None:
        db.create_all()
        print("База данных инициализирована.")

    return app
