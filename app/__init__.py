from flask import Flask, render_template
from sqlalchemy import inspect

from config import Config
from .auth import load_current_user
from .extensions import db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    @app.before_request
    def before_request() -> None:
        load_current_user()

    from .routes import main_bp
    from .models import Client, FeedbackMessage, IntegrationLog, IntegrationSetting, Role, User

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template("errors/500.html"), 500

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

    @app.cli.command("seed-clients")
    def seed_clients() -> None:
        db.create_all()

        clients_data = [
            ("Иван Петров", "ivan.petrov@example.com", "+7 (900) 111-22-33", "Москва", "Новый"),
            ("Мария Соколова", "maria.sokolova@example.com", "+7 (901) 222-33-44", "Санкт-Петербург", "В работе"),
            ("Алексей Кузнецов", "alexey.kuznetsov@example.com", "+7 (902) 333-44-55", "Казань", "Постоянный"),
            ("Елена Смирнова", "elena.smirnova@example.com", "+7 (903) 444-55-66", "Екатеринбург", "Неактивный"),
        ]

        for full_name, email, phone, city, status in clients_data:
            client = Client.query.filter_by(email=email).first()
            if client is None:
                client = Client(
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    city=city,
                    status=status,
                )
                db.session.add(client)

        db.session.commit()
        print("Демонстрационные клиенты добавлены.")

    return app
