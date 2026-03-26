from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import User


HASH_PREFIXES = ("pbkdf2:", "scrypt:")


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


def migrate_plaintext_passwords() -> None:
    users = User.query.all()
    changed = False

    for user in users:
        if not user.password.startswith(HASH_PREFIXES):
            user.password = generate_password_hash(user.password)
            changed = True

    if changed:
        db.session.commit()
