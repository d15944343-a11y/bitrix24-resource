from flask import Flask, render_template

from config import Config
from .auth import load_current_user
from .db_setup import ensure_database_schema, migrate_plaintext_passwords
from .extensions import db
from .seeds import seed_clients_data, seed_roles_and_users


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)

    @app.before_request
    def before_request() -> None:
        load_current_user()

    from .routes import main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        ensure_database_schema()
        migrate_plaintext_passwords()

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template("errors/500.html"), 500

    @app.cli.command("init-db")
    def init_db() -> None:
        with app.app_context():
            ensure_database_schema()
        print("База данных инициализирована.")

    @app.cli.command("seed-users")
    def seed_users() -> None:
        with app.app_context():
            ensure_database_schema()
            seed_roles_and_users()
        print("Роли и демонстрационные пользователи добавлены.")

    @app.cli.command("seed-clients")
    def seed_clients() -> None:
        with app.app_context():
            ensure_database_schema()
            seed_clients_data()
        print("Демонстрационные клиенты добавлены.")

    return app
