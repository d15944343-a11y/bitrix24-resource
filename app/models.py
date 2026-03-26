from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)


class Role(BaseModel):
    __tablename__ = "roles"

    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)

    users = db.relationship("User", back_populates="role", lazy=True)

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class User(BaseModel):
    __tablename__ = "users"

    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    role = db.relationship("Role", back_populates="users")

    def set_password(self, raw_password: str) -> None:
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password, raw_password)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Client(BaseModel):
    __tablename__ = "clients"

    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)

    def __repr__(self) -> str:
        return f"<Client {self.email}>"


class FeedbackMessage(BaseModel):
    __tablename__ = "feedback_messages"

    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Новое")

    def __repr__(self) -> str:
        return f"<FeedbackMessage {self.email}>"


class IntegrationSetting(BaseModel):
    __tablename__ = "integration_settings"

    service_name = db.Column(db.String(100), nullable=False, unique=True)
    webhook_url = db.Column(db.String(500), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<IntegrationSetting {self.service_name}>"


class IntegrationLog(BaseModel):
    __tablename__ = "integration_logs"

    service_name = db.Column(db.String(100), nullable=False)
    operation = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<IntegrationLog {self.service_name}:{self.operation}>"
