from .extensions import db
from .models import Client, Role, User


def seed_roles_and_users() -> None:
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
                role=roles[role_name],
            )
            user.set_password(password)
            db.session.add(user)

    db.session.commit()


def seed_clients_data() -> None:
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
