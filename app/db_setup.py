from __future__ import annotations

from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import User


HASH_PREFIXES = ("pbkdf2:", "scrypt:")

SQLITE_CLIENT_COLUMNS = {
    "customer_code": "VARCHAR(40) NOT NULL DEFAULT ''",
    "senior_citizen": "BOOLEAN NOT NULL DEFAULT 0",
    "tenure_months": "INTEGER NOT NULL DEFAULT 0",
    "monthly_charges": "FLOAT NOT NULL DEFAULT 0",
    "total_charges": "FLOAT NOT NULL DEFAULT 0",
    "service_count": "INTEGER NOT NULL DEFAULT 0",
    "contract_type": "VARCHAR(40) NOT NULL DEFAULT 'Month-to-month'",
    "payment_method": "VARCHAR(80) NOT NULL DEFAULT 'Electronic check'",
    "internet_service": "VARCHAR(40) NOT NULL DEFAULT 'DSL'",
    "paperless_billing": "BOOLEAN NOT NULL DEFAULT 0",
    "has_family_plan": "BOOLEAN NOT NULL DEFAULT 0",
    "has_tech_support": "BOOLEAN NOT NULL DEFAULT 0",
    "churn_probability": "FLOAT",
    "churn_prediction": "VARCHAR(40)",
    "risk_level": "VARCHAR(20)",
}


def ensure_database_schema() -> None:
    db.create_all()

    engine = db.engine
    inspector = inspect(engine)

    if engine.dialect.name != "sqlite":
        return

    if inspector.has_table("feedback_messages"):
        columns = {column["name"] for column in inspector.get_columns("feedback_messages")}
        if "status" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE feedback_messages "
                        "ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'Новое'"
                    )
                )

    if inspector.has_table("clients"):
        existing_columns = {column["name"] for column in inspector.get_columns("clients")}
        with engine.begin() as connection:
            for column_name, definition in SQLITE_CLIENT_COLUMNS.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(f"ALTER TABLE clients ADD COLUMN {column_name} {definition}"))

            connection.execute(
                text(
                    "UPDATE clients "
                    "SET customer_code = 'CLIENT-' || id "
                    "WHERE customer_code IS NULL OR customer_code = ''"
                )
            )


def migrate_plaintext_passwords() -> None:
    users = User.query.all()
    changed = False

    for user in users:
        if not user.password.startswith(HASH_PREFIXES):
            user.password = generate_password_hash(user.password)
            changed = True

    if changed:
        db.session.commit()
