from flask import Flask
from sqlalchemy import inspect

from config import Config
from .extensions import db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from .routes import main_bp
    from .models import Role, User

    app.register_blueprint(main_bp)

    @app.cli.command("init-db")
    def init_db() -> None:
        db.create_all()
        print("База данных инициализирована.")

    @app.cli.command("seed-users")
    def seed_users() -> None:
        inspector = inspect(db.engine)
        if not inspector.has_table("roles") or not inspector.has_table("users"):
            db.create_all()

        roles_data = [
            ("Администратор", "Полный доступ к системе и управлению пользователями."),
            ("Менеджер", "Работа с клиентской базой, аналитикой и рекомендациями."),
            ("Аналитик", "Доступ к отчетам, сегментации и аналитическим разделам."),
        ]

        roles = {}
        for name, description in roles_data:
            role = Role.query.filter_by(name=name).first()
            if role is None:
                role = Role(name=name, description=description)
                db.session.add(role)
            roles[name] = role

        db.session.flush()

        users_data = [
            ("Администратор системы", "admin@example.com", "admin123", "Администратор"),
            ("Менеджер отдела продаж", "manager@example.com", "manager123", "Менеджер"),
            ("Бизнес-аналитик", "analyst@example.com", "analyst123", "Аналитик"),
        ]

        for full_name, email, password, role_name in users_data:
            user = User.query.filter_by(email=email).first()
            if user is None:
                user = User(
                    full_name=full_name,
                    email=email,
                    password=password,
                    role=roles[role_name],
                )
                db.session.add(user)

        db.session.commit()
        print("Роли и демонстрационные пользователи добавлены.")

    return app
