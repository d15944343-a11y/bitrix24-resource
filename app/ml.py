from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import joblib
import pandas as pd
from flask import current_app
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from werkzeug.utils import secure_filename

from .extensions import db
from .models import Client, DatasetAsset, ModelArtifact, PredictionRun


DEMO_DATASET_FILENAME = "crm_customer_churn.csv"
ROOT_MODEL_FILENAME = "model.joblib"
TARGET_COLUMN = "churn_target"
ID_COLUMN = "customer_id"

INPUT_COLUMNS = [
    ID_COLUMN,
    "senior_citizen",
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "service_count",
    "contract_type",
    "payment_method",
    "internet_service",
    "paperless_billing",
    "has_family_plan",
    "has_tech_support",
]

NUMERIC_COLUMNS = [
    "senior_citizen",
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "service_count",
]

CATEGORICAL_COLUMNS = [
    "contract_type",
    "payment_method",
    "internet_service",
    "paperless_billing",
    "has_family_plan",
    "has_tech_support",
    "lifecycle_stage",
]

FRIENDLY_COLUMN_NAMES = {
    "senior_citizen": "Старшая возрастная группа",
    "tenure_months": "Срок обслуживания (мес.)",
    "monthly_charges": "Ежемесячная выручка",
    "total_charges": "Накопленная выручка",
    "service_count": "Количество подключённых сервисов",
    "contract_type": "Тип контракта",
    "payment_method": "Способ оплаты",
    "internet_service": "Тип интернет-услуги",
    "paperless_billing": "Безбумажный биллинг",
    "has_family_plan": "Семейный тариф",
    "has_tech_support": "Техподдержка",
    "lifecycle_stage": "Этап жизненного цикла клиента",
}


def project_root() -> Path:
    return Path(current_app.root_path).parent


def data_dir() -> Path:
    return project_root() / "data"


def runtime_dir() -> Path:
    return Path(current_app.instance_path)


def datasets_dir() -> Path:
    return runtime_dir() / "datasets"


def models_dir() -> Path:
    return runtime_dir() / "models"


def predictions_dir() -> Path:
    return runtime_dir() / "predictions"


def root_model_path() -> Path:
    return project_root() / ROOT_MODEL_FILENAME


def demo_dataset_path() -> Path:
    return data_dir() / DEMO_DATASET_FILENAME


def ensure_ml_dirs() -> None:
    for path in (data_dir(), runtime_dir(), datasets_dir(), models_dir(), predictions_dir()):
        path.mkdir(parents=True, exist_ok=True)


def now_utc() -> datetime:
    return datetime.now(UTC)


def ensure_demo_assets_registered() -> None:
    ensure_ml_dirs()

    dataset_path = demo_dataset_path()
    if dataset_path.exists():
        sync_dataset_asset(
            name="Встроенный CRM-датасет",
            file_path=dataset_path,
            source_kind="bundled",
            source_reference="IBM Telco Customer Churn (преобразован под CRM-признаки)",
            target_column=TARGET_COLUMN,
            is_builtin=True,
        )

    model_path = root_model_path()
    if model_path.exists():
        payload = load_model_payload(model_path)
        metadata = payload.get("metadata", {})
        sync_model_artifact(
            name="Базовая продакшен-модель",
            algorithm=metadata.get("algorithm", "random_forest"),
            file_path=model_path,
            dataset_name=metadata.get("dataset_name", "Встроенный CRM-датасет"),
            metrics=metadata.get("metrics", {}),
            baseline_metrics=metadata.get("baseline_metrics", {}),
            feature_importances=metadata.get("feature_importances", []),
            confusion=metadata.get("confusion_matrix", {}),
            is_active=True,
        )


def sync_dataset_asset(
    *,
    name: str,
    file_path: Path,
    source_kind: str,
    source_reference: str,
    target_column: str,
    is_builtin: bool = False,
) -> DatasetAsset:
    frame = load_dataset_frame(file_path)
    record = DatasetAsset.query.filter_by(file_path=str(file_path.resolve())).first()

    if record is None:
        record = DatasetAsset(
            name=name,
            source_kind=source_kind,
            source_reference=source_reference,
            file_path=str(file_path.resolve()),
            target_column=target_column,
            is_builtin=is_builtin,
        )
        db.session.add(record)

    record.name = name
    record.source_kind = source_kind
    record.source_reference = source_reference
    record.target_column = target_column
    record.row_count = len(frame.index)
    record.feature_columns = json.dumps(INPUT_COLUMNS[1:], ensure_ascii=False)
    record.is_builtin = is_builtin
    db.session.commit()
    return record


def sync_model_artifact(
    *,
    name: str,
    algorithm: str,
    file_path: Path,
    dataset_name: str,
    metrics: dict[str, Any],
    baseline_metrics: dict[str, Any],
    feature_importances: list[dict[str, Any]],
    confusion: dict[str, Any],
    is_active: bool = False,
) -> ModelArtifact:
    dataset = DatasetAsset.query.filter_by(name=dataset_name).first()
    record = ModelArtifact.query.filter_by(file_path=str(file_path.resolve())).first()

    if record is None:
        record = ModelArtifact(
            name=name,
            algorithm=algorithm,
            file_path=str(file_path.resolve()),
        )
        db.session.add(record)

    if is_active:
        ModelArtifact.query.update({ModelArtifact.is_active: False})

    record.name = name
    record.algorithm = algorithm
    record.file_path = str(file_path.resolve())
    record.dataset_id = dataset.id if dataset else None
    record.accuracy = metrics.get("accuracy")
    record.precision = metrics.get("precision")
    record.recall = metrics.get("recall")
    record.f1_score = metrics.get("f1_score")
    record.roc_auc = metrics.get("roc_auc")
    record.metrics_json = json.dumps(
        {
            "metrics": metrics,
            "baseline_metrics": baseline_metrics,
            "feature_importances": feature_importances,
            "confusion_matrix": confusion,
        },
        ensure_ascii=False,
    )
    record.is_active = is_active
    record.trained_at = now_utc()
    db.session.commit()
    return record


def load_dataset_frame(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if ID_COLUMN not in frame.columns:
        frame.insert(0, ID_COLUMN, [f"CRM-{index + 1:05d}" for index in range(len(frame.index))])
    return frame


def parse_boolean_label(value: Any) -> str:
    if value in (1, "1", True, "true", "True", "Да", "да", "Yes", "yes"):
        return "Yes"
    return "No"


def derive_lifecycle_stage(tenure_value: Any) -> str:
    tenure = int(float(tenure_value or 0))
    if tenure <= 6:
        return "Onboarding"
    if tenure <= 24:
        return "Growth"
    if tenure <= 48:
        return "Retention"
    return "Loyal"


def normalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()

    for column in INPUT_COLUMNS:
        if column not in working.columns:
            if column == ID_COLUMN:
                working[column] = [f"CRM-{index + 1:05d}" for index in range(len(working.index))]
            else:
                raise ValueError(f"Отсутствует обязательный столбец `{column}`.")

    for column in ("senior_citizen", "tenure_months", "service_count"):
        working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0).astype(int)

    for column in ("monthly_charges", "total_charges"):
        working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0.0)

    for column in ("paperless_billing", "has_family_plan", "has_tech_support"):
        working[column] = working[column].map(parse_boolean_label)

    working["contract_type"] = working["contract_type"].fillna("Month-to-month")
    working["payment_method"] = working["payment_method"].fillna("Electronic check")
    working["internet_service"] = working["internet_service"].fillna("DSL")
    working["lifecycle_stage"] = working["tenure_months"].map(derive_lifecycle_stage)

    return working[INPUT_COLUMNS + ["lifecycle_stage"]]


def validate_training_dataset(frame: pd.DataFrame) -> None:
    normalize_feature_frame(frame)
    if TARGET_COLUMN not in frame.columns:
        raise ValueError(f"В датасете отсутствует целевой столбец `{TARGET_COLUMN}`.")


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERIC_COLUMNS,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_COLUMNS,
            ),
        ]
    )


def build_pipeline(algorithm: str) -> Pipeline:
    if algorithm == "logistic_regression":
        model = LogisticRegression(max_iter=2000, class_weight="balanced")
    else:
        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=4,
            random_state=42,
            class_weight="balanced_subsample",
        )

    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("model", model),
        ]
    )


def collect_metrics(y_true: pd.Series, predictions: Any, probabilities: Any) -> dict[str, float]:
    metrics = {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1_score": float(f1_score(y_true, predictions, zero_division=0)),
    }

    try:
        metrics["roc_auc"] = float(roc_auc_score(y_true, probabilities))
    except ValueError:
        metrics["roc_auc"] = 0.0

    return metrics


def collect_confusion(y_true: pd.Series, predictions: Any) -> dict[str, int]:
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    return {"true_negative": int(tn), "false_positive": int(fp), "false_negative": int(fn), "true_positive": int(tp)}


def readable_feature_name(raw_name: str) -> str:
    cleaned = raw_name.replace("num__", "").replace("cat__", "")
    cleaned = cleaned.replace("onehot__", "").replace("remainder__", "")
    if "_" in cleaned:
        prefix, suffix = cleaned.split("_", 1)
        if prefix in FRIENDLY_COLUMN_NAMES:
            return f"{FRIENDLY_COLUMN_NAMES[prefix]}: {suffix}"
    return FRIENDLY_COLUMN_NAMES.get(cleaned, cleaned.replace("_", " "))


def collect_feature_importances(pipeline: Pipeline, limit: int = 8) -> list[dict[str, Any]]:
    model = pipeline.named_steps["model"]
    if not hasattr(model, "feature_importances_"):
        return []

    preprocessor = pipeline.named_steps["preprocessor"]
    feature_names = preprocessor.get_feature_names_out()
    importances = model.feature_importances_

    rows = [
        {"feature": readable_feature_name(name), "value": round(float(value), 4)}
        for name, value in sorted(zip(feature_names, importances, strict=False), key=lambda item: item[1], reverse=True)[:limit]
    ]
    return rows


def train_model(dataset_record: DatasetAsset, algorithm: str = "random_forest") -> ModelArtifact:
    ensure_ml_dirs()
    frame = load_dataset_frame(dataset_record.file_path)
    validate_training_dataset(frame)

    normalized = normalize_feature_frame(frame)
    target = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce").fillna(0).astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        normalized.drop(columns=[ID_COLUMN]),
        target,
        test_size=0.2,
        random_state=42,
        stratify=target,
    )

    baseline_pipeline = build_pipeline("logistic_regression")
    baseline_pipeline.fit(x_train, y_train)
    baseline_probabilities = baseline_pipeline.predict_proba(x_test)[:, 1]
    baseline_predictions = baseline_pipeline.predict(x_test)
    baseline_metrics = collect_metrics(y_test, baseline_predictions, baseline_probabilities)

    production_pipeline = build_pipeline(algorithm)
    production_pipeline.fit(x_train, y_train)
    probabilities = production_pipeline.predict_proba(x_test)[:, 1]
    predictions = production_pipeline.predict(x_test)

    metrics = collect_metrics(y_test, predictions, probabilities)
    confusion = collect_confusion(y_test, predictions)
    feature_importances = collect_feature_importances(production_pipeline)

    timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
    runtime_model_path = models_dir() / f"model_{timestamp}.joblib"
    payload = {
        "pipeline": production_pipeline,
        "metadata": {
            "algorithm": algorithm,
            "dataset_name": dataset_record.name,
            "dataset_path": dataset_record.file_path,
            "feature_columns": INPUT_COLUMNS[1:],
            "target_column": TARGET_COLUMN,
            "trained_at": now_utc().isoformat(),
            "metrics": metrics,
            "baseline_metrics": baseline_metrics,
            "feature_importances": feature_importances,
            "confusion_matrix": confusion,
        },
    }

    joblib.dump(payload, runtime_model_path)
    joblib.dump(payload, root_model_path())

    artifact = sync_model_artifact(
        name=f"ML-модель {timestamp}",
        algorithm=algorithm,
        file_path=runtime_model_path,
        dataset_name=dataset_record.name,
        metrics=metrics,
        baseline_metrics=baseline_metrics,
        feature_importances=feature_importances,
        confusion=confusion,
        is_active=True,
    )

    sync_client_predictions(artifact)
    return artifact


def load_model_payload(path: str | Path) -> dict[str, Any]:
    payload = joblib.load(path)
    if isinstance(payload, Pipeline):
        return {"pipeline": payload, "metadata": {}}
    return payload


def get_active_model() -> ModelArtifact | None:
    return ModelArtifact.query.filter_by(is_active=True).first()


def score_frame(model_path: str | Path, frame: pd.DataFrame) -> pd.DataFrame:
    payload = load_model_payload(model_path)
    pipeline = payload["pipeline"]
    normalized = normalize_feature_frame(frame)
    features = normalized.drop(columns=[ID_COLUMN])
    probabilities = pipeline.predict_proba(features)[:, 1]
    predictions = pipeline.predict(features)

    scored = normalized.copy()
    scored["churn_probability"] = probabilities
    scored["churn_prediction"] = predictions
    scored["risk_level"] = scored["churn_probability"].map(risk_level_label)
    return scored


def risk_level_label(probability: float) -> str:
    if probability >= 0.65:
        return "Высокий"
    if probability >= 0.4:
        return "Средний"
    return "Низкий"


def next_best_action(client: Client) -> str:
    probability = client.churn_probability or 0.0

    if probability >= 0.65 and client.contract_type == "Month-to-month":
        return "Предложить фиксированный контракт и персональную скидку на удержание."
    if probability >= 0.65 and not client.has_tech_support:
        return "Назначить менеджерский контакт и подключить расширенную техподдержку."
    if probability >= 0.4 and not client.has_family_plan:
        return "Сделать оффер на семейный пакет и повышение ценности обслуживания."
    if probability >= 0.4:
        return "Проверить удовлетворённость клиента и зафиксировать следующий касательный сценарий."
    if client.monthly_charges >= 90:
        return "Клиент стабилен: предложить upsell на премиальный сервис без агрессивного давления."
    return "Поддерживать регулярные касания и наблюдать за динамикой жизненного цикла."


def clients_to_frame(clients: list[Client]) -> pd.DataFrame:
    rows = []
    for client in clients:
        rows.append(
            {
                ID_COLUMN: client.customer_code or f"CLIENT-{client.id}",
                "senior_citizen": int(bool(client.senior_citizen)),
                "tenure_months": client.tenure_months,
                "monthly_charges": client.monthly_charges,
                "total_charges": client.total_charges,
                "service_count": client.service_count,
                "contract_type": client.contract_type,
                "payment_method": client.payment_method,
                "internet_service": client.internet_service,
                "paperless_billing": "Yes" if client.paperless_billing else "No",
                "has_family_plan": "Yes" if client.has_family_plan else "No",
                "has_tech_support": "Yes" if client.has_tech_support else "No",
            }
        )
    return pd.DataFrame(rows)


def sync_client_predictions(artifact: ModelArtifact | None = None) -> PredictionRun | None:
    artifact = artifact or get_active_model()
    if artifact is None:
        return None

    clients = Client.query.order_by(Client.id.asc()).all()
    if not clients:
        return None

    frame = clients_to_frame(clients)
    scored = score_frame(artifact.file_path, frame)

    probability_map = {
        row[ID_COLUMN]: (float(row["churn_probability"]), int(row["churn_prediction"]), row["risk_level"])
        for row in scored.to_dict(orient="records")
    }

    for client in clients:
        key = client.customer_code or f"CLIENT-{client.id}"
        probability, prediction, risk_level = probability_map[key]
        client.churn_probability = round(probability, 4)
        client.churn_prediction = "Отток" if prediction == 1 else "Удержание"
        client.risk_level = risk_level

    timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
    output_path = predictions_dir() / f"client_predictions_{timestamp}.csv"

    export_frame = pd.DataFrame(
        [
            {
                "client_id": client.id,
                "customer_code": client.customer_code,
                "full_name": client.full_name,
                "status": client.status,
                "risk_level": client.risk_level,
                "churn_prediction": client.churn_prediction,
                "churn_probability": client.churn_probability,
                "next_best_action": next_best_action(client),
            }
            for client in clients
        ]
    )
    export_frame.to_csv(output_path, index=False)

    run = PredictionRun(
        model_id=artifact.id,
        scope_name="clients",
        rows_scored=len(clients),
        avg_probability=float(export_frame["churn_probability"].mean()),
        high_risk_count=int((export_frame["risk_level"] == "Высокий").sum()),
        file_path=str(output_path.resolve()),
        summary_json=json.dumps(
            {
                "top_risk_clients": export_frame.sort_values("churn_probability", ascending=False)
                .head(5)
                .to_dict(orient="records")
            },
            ensure_ascii=False,
        ),
    )
    db.session.add(run)
    db.session.commit()
    return run


def dataset_preview(dataset_record: DatasetAsset, limit: int = 8) -> list[dict[str, Any]]:
    frame = load_dataset_frame(dataset_record.file_path)
    preview = frame.head(limit).copy()
    return preview.to_dict(orient="records")


def model_metrics(model: ModelArtifact | None) -> dict[str, Any]:
    if model is None or not model.metrics_json:
        return {}
    return json.loads(model.metrics_json)


def latest_prediction_run() -> PredictionRun | None:
    return PredictionRun.query.order_by(PredictionRun.created_at.desc()).first()


def register_uploaded_dataset(file_storage) -> DatasetAsset:
    ensure_ml_dirs()
    filename = secure_filename(file_storage.filename or "dataset.csv")
    if not filename.lower().endswith(".csv"):
        raise ValueError("Допускаются только CSV-файлы.")

    output_path = datasets_dir() / f"{now_utc().strftime('%Y%m%d_%H%M%S')}_{filename}"
    file_storage.save(output_path)

    frame = load_dataset_frame(output_path)
    validate_training_dataset(frame)

    return sync_dataset_asset(
        name=f"Загруженный датасет {filename}",
        file_path=output_path,
        source_kind="upload",
        source_reference=filename,
        target_column=TARGET_COLUMN,
    )


def register_dataset_from_url(source_url: str) -> DatasetAsset:
    ensure_ml_dirs()
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Поддерживаются только ссылки http/https на CSV-файлы.")

    candidate_name = Path(parsed.path).name or "remote_dataset.csv"
    filename = secure_filename(candidate_name)
    if not filename.lower().endswith(".csv"):
        filename = f"{filename}.csv"

    output_path = datasets_dir() / f"{now_utc().strftime('%Y%m%d_%H%M%S')}_{filename}"
    frame = pd.read_csv(source_url)
    frame.to_csv(output_path, index=False)
    validate_training_dataset(frame)

    return sync_dataset_asset(
        name=f"Внешний датасет {filename}",
        file_path=output_path,
        source_kind="url",
        source_reference=source_url,
        target_column=TARGET_COLUMN,
    )


def activate_model(model_id: int) -> ModelArtifact:
    model = ModelArtifact.query.get_or_404(model_id)
    ModelArtifact.query.update({ModelArtifact.is_active: False})
    model.is_active = True
    db.session.commit()
    sync_client_predictions(model)
    return model
