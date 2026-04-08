from __future__ import annotations

from .extensions import db
from .models import Client, Role, User


def seed_roles_and_users() -> None:
    roles_data = [
        ("Администратор", "Полный доступ к системе и управлению пользователями."),
        ("Менеджер", "Работа с клиентской базой, прогнозами и рекомендациями."),
        ("Аналитик", "Доступ к витринам данных, моделям и отчетам по качеству ML."),
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
        ("Менеджер по удержанию", "manager@example.com", "manager123", "Менеджер"),
        ("ML-аналитик CRM", "analyst@example.com", "analyst123", "Аналитик"),
    ]

    for full_name, email, password, role_name in users_data:
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(full_name=full_name, email=email, role=roles[role_name])
            user.set_password(password)
            db.session.add(user)

    db.session.commit()


def seed_clients_data() -> None:
    clients_data = [
        {
            "full_name": "Иван Петров",
            "email": "ivan.petrov@example.com",
            "phone": "+7 (900) 111-22-33",
            "city": "Москва",
            "status": "Новый",
            "customer_code": "CRM-1001",
            "senior_citizen": False,
            "tenure_months": 2,
            "monthly_charges": 95.0,
            "total_charges": 190.0,
            "service_count": 2,
            "contract_type": "Month-to-month",
            "payment_method": "Electronic check",
            "internet_service": "Fiber optic",
            "paperless_billing": True,
            "has_family_plan": False,
            "has_tech_support": False,
        },
        {
            "full_name": "Мария Соколова",
            "email": "maria.sokolova@example.com",
            "phone": "+7 (901) 222-33-44",
            "city": "Санкт-Петербург",
            "status": "В работе",
            "customer_code": "CRM-1002",
            "senior_citizen": False,
            "tenure_months": 18,
            "monthly_charges": 71.5,
            "total_charges": 1287.0,
            "service_count": 5,
            "contract_type": "One year",
            "payment_method": "Credit card (automatic)",
            "internet_service": "DSL",
            "paperless_billing": True,
            "has_family_plan": True,
            "has_tech_support": True,
        },
        {
            "full_name": "Алексей Кузнецов",
            "email": "alexey.kuznetsov@example.com",
            "phone": "+7 (902) 333-44-55",
            "city": "Казань",
            "status": "Постоянный",
            "customer_code": "CRM-1003",
            "senior_citizen": False,
            "tenure_months": 56,
            "monthly_charges": 109.9,
            "total_charges": 6154.4,
            "service_count": 6,
            "contract_type": "Two year",
            "payment_method": "Bank transfer (automatic)",
            "internet_service": "Fiber optic",
            "paperless_billing": False,
            "has_family_plan": True,
            "has_tech_support": True,
        },
        {
            "full_name": "Елена Смирнова",
            "email": "elena.smirnova@example.com",
            "phone": "+7 (903) 444-55-66",
            "city": "Екатеринбург",
            "status": "Неактивный",
            "customer_code": "CRM-1004",
            "senior_citizen": True,
            "tenure_months": 5,
            "monthly_charges": 83.2,
            "total_charges": 416.0,
            "service_count": 3,
            "contract_type": "Month-to-month",
            "payment_method": "Mailed check",
            "internet_service": "Fiber optic",
            "paperless_billing": True,
            "has_family_plan": False,
            "has_tech_support": False,
        },
    ]

    for payload in clients_data:
        client = Client.query.filter_by(email=payload["email"]).first()
        if client is None:
            client = Client(**payload)
            db.session.add(client)
            continue

        for key, value in payload.items():
            setattr(client, key, value)

    db.session.commit()
