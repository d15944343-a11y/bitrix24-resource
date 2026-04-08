from __future__ import annotations

from datetime import datetime, UTC

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC)


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

    customer_code = db.Column(db.String(40), unique=True, nullable=False)
    senior_citizen = db.Column(db.Boolean, default=False, nullable=False)
    tenure_months = db.Column(db.Integer, default=0, nullable=False)
    monthly_charges = db.Column(db.Float, default=0.0, nullable=False)
    total_charges = db.Column(db.Float, default=0.0, nullable=False)
    service_count = db.Column(db.Integer, default=0, nullable=False)
    contract_type = db.Column(db.String(40), default="Month-to-month", nullable=False)
    payment_method = db.Column(db.String(80), default="Electronic check", nullable=False)
    internet_service = db.Column(db.String(40), default="DSL", nullable=False)
    paperless_billing = db.Column(db.Boolean, default=False, nullable=False)
    has_family_plan = db.Column(db.Boolean, default=False, nullable=False)
    has_tech_support = db.Column(db.Boolean, default=False, nullable=False)
    churn_probability = db.Column(db.Float, nullable=True)
    churn_prediction = db.Column(db.String(40), nullable=True)
    risk_level = db.Column(db.String(20), nullable=True)

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


class DatasetAsset(BaseModel):
    __tablename__ = "dataset_assets"

    name = db.Column(db.String(120), nullable=False)
    source_kind = db.Column(db.String(40), nullable=False)
    source_reference = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(500), nullable=False, unique=True)
    target_column = db.Column(db.String(80), nullable=False)
    row_count = db.Column(db.Integer, default=0, nullable=False)
    feature_columns = db.Column(db.Text, nullable=False, default="[]")
    is_builtin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    model_artifacts = db.relationship("ModelArtifact", back_populates="dataset", lazy=True)

    def __repr__(self) -> str:
        return f"<DatasetAsset {self.name}>"


class ModelArtifact(BaseModel):
    __tablename__ = "model_artifacts"

    name = db.Column(db.String(120), nullable=False)
    algorithm = db.Column(db.String(80), nullable=False)
    file_path = db.Column(db.String(500), nullable=False, unique=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset_assets.id"), nullable=True)
    accuracy = db.Column(db.Float, nullable=True)
    precision = db.Column(db.Float, nullable=True)
    recall = db.Column(db.Float, nullable=True)
    f1_score = db.Column(db.Float, nullable=True)
    roc_auc = db.Column(db.Float, nullable=True)
    metrics_json = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    trained_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    dataset = db.relationship("DatasetAsset", back_populates="model_artifacts")
    prediction_runs = db.relationship("PredictionRun", back_populates="model", lazy=True)

    def __repr__(self) -> str:
        return f"<ModelArtifact {self.name}>"


class PredictionRun(BaseModel):
    __tablename__ = "prediction_runs"

    model_id = db.Column(db.Integer, db.ForeignKey("model_artifacts.id"), nullable=False)
    scope_name = db.Column(db.String(80), nullable=False)
    rows_scored = db.Column(db.Integer, nullable=False)
    avg_probability = db.Column(db.Float, nullable=False)
    high_risk_count = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    summary_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    model = db.relationship("ModelArtifact", back_populates="prediction_runs")

    def __repr__(self) -> str:
        return f"<PredictionRun {self.scope_name}:{self.model_id}>"
