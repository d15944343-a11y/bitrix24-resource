from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

import requests
from flask import (
    Blueprint,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from .auth import login_required, role_required
from .extensions import db
from .ml import (
    activate_model,
    dataset_preview,
    get_active_model,
    latest_prediction_run,
    model_metrics,
    next_best_action,
    register_dataset_from_url,
    register_uploaded_dataset,
    sync_client_predictions,
    train_model,
)
from .models import (
    Client,
    DatasetAsset,
    FeedbackMessage,
    IntegrationLog,
    IntegrationSetting,
    ModelArtifact,
    PredictionRun,
    Role,
    User,
)
from .validators import is_valid_email


main_bp = Blueprint("main", __name__)

CLIENT_STATUS_CHOICES = ["Новый", "В работе", "Постоянный", "Неактивный", "Импортирован из Bitrix24"]
CONTRACT_CHOICES = ["Month-to-month", "One year", "Two year"]
PAYMENT_CHOICES = [
    "Electronic check",
    "Mailed check",
    "Bank transfer (automatic)",
    "Credit card (automatic)",
]
INTERNET_CHOICES = ["DSL", "Fiber optic", "No"]


def base_breadcrumbs() -> list[dict]:
    return [{"title": "Главная", "endpoint": "main.index"}]


def build_client_form_data(source: dict | Client | None = None) -> dict:
    defaults = {
        "full_name": "",
        "email": "",
        "phone": "",
        "city": "",
        "status": "Новый",
        "customer_code": "",
        "senior_citizen": False,
        "tenure_months": 0,
        "monthly_charges": 0.0,
        "total_charges": 0.0,
        "service_count": 1,
        "contract_type": "Month-to-month",
        "payment_method": "Electronic check",
        "internet_service": "DSL",
        "paperless_billing": False,
        "has_family_plan": False,
        "has_tech_support": False,
    }

    if source is None:
        return defaults

    if isinstance(source, Client):
        defaults.update(
            {
                "full_name": source.full_name,
                "email": source.email,
                "phone": source.phone,
                "city": source.city,
                "status": source.status,
                "customer_code": source.customer_code,
                "senior_citizen": source.senior_citizen,
                "tenure_months": source.tenure_months,
                "monthly_charges": source.monthly_charges,
                "total_charges": source.total_charges,
                "service_count": source.service_count,
                "contract_type": source.contract_type,
                "payment_method": source.payment_method,
                "internet_service": source.internet_service,
                "paperless_billing": source.paperless_billing,
                "has_family_plan": source.has_family_plan,
                "has_tech_support": source.has_tech_support,
            }
        )
        return defaults

    defaults.update(source)
    return defaults


def parse_checkbox(name: str) -> bool:
    return request.form.get(name) == "on"


def ensure_predictions() -> None:
    active_model = get_active_model()
    if active_model is None:
        return
    if Client.query.filter(Client.churn_probability.is_(None)).count():
        sync_client_predictions(active_model)


def parse_client_payload() -> tuple[dict, list[str]]:
    payload = {
        "full_name": request.form.get("full_name", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
        "phone": request.form.get("phone", "").strip(),
        "city": request.form.get("city", "").strip(),
        "status": request.form.get("status", "").strip(),
        "customer_code": request.form.get("customer_code", "").strip(),
        "contract_type": request.form.get("contract_type", "").strip(),
        "payment_method": request.form.get("payment_method", "").strip(),
        "internet_service": request.form.get("internet_service", "").strip(),
        "senior_citizen": parse_checkbox("senior_citizen"),
        "paperless_billing": parse_checkbox("paperless_billing"),
        "has_family_plan": parse_checkbox("has_family_plan"),
        "has_tech_support": parse_checkbox("has_tech_support"),
    }

    errors = []
    for field_name in ("full_name", "email", "phone", "city", "status", "customer_code"):
        if not payload[field_name]:
            errors.append("Заполните все обязательные поля карточки клиента.")
            break

    if payload["status"] and payload["status"] not in CLIENT_STATUS_CHOICES:
        errors.append("Выбран некорректный статус клиента.")

    if payload["contract_type"] and payload["contract_type"] not in CONTRACT_CHOICES:
        errors.append("Выбран некорректный тип контракта.")

    if payload["payment_method"] and payload["payment_method"] not in PAYMENT_CHOICES:
        errors.append("Выбран некорректный способ оплаты.")

    if payload["internet_service"] and payload["internet_service"] not in INTERNET_CHOICES:
        errors.append("Выбран некорректный тип интернет-услуги.")

    if payload["email"] and not is_valid_email(payload["email"]):
        errors.append("Укажите корректный email адрес клиента.")

    try:
        payload["tenure_months"] = int(request.form.get("tenure_months", 0))
        payload["service_count"] = int(request.form.get("service_count", 0))
        payload["monthly_charges"] = float(request.form.get("monthly_charges", 0))
        payload["total_charges"] = float(request.form.get("total_charges", 0))
    except ValueError:
        errors.append("Числовые поля содержат некорректные значения.")

    if payload.get("tenure_months", 0) < 0 or payload.get("service_count", 0) < 0:
        errors.append("Числовые показатели клиента не могут быть отрицательными.")

    if payload.get("monthly_charges", 0) < 0 or payload.get("total_charges", 0) < 0:
        errors.append("Финансовые показатели клиента не могут быть отрицательными.")

    return payload, errors


@main_bp.route("/")
def index():
    active_model = get_active_model()
    ensure_predictions()
    clients = Client.query.order_by(Client.churn_probability.desc(), Client.id.asc()).limit(3).all()
    metrics_bundle = model_metrics(active_model)
    current_metrics = metrics_bundle.get("metrics", {})

    return render_template(
        "index.html",
        active_model=active_model,
        current_metrics=current_metrics,
        top_clients=clients,
        total_clients=Client.query.count(),
        datasets_count=DatasetAsset.query.count(),
        models_count=ModelArtifact.query.count(),
        prediction_runs_count=PredictionRun.query.count(),
        breadcrumbs=[{"title": "Главная"}],
    )


@main_bp.route("/about")
def about():
    return render_template(
        "about.html",
        active_model=get_active_model(),
        datasets_count=DatasetAsset.query.count(),
        models_count=ModelArtifact.query.count(),
        breadcrumbs=[*base_breadcrumbs(), {"title": "О проекте"}],
    )


@main_bp.route("/contacts", methods=["GET", "POST"])
def contacts():
    breadcrumbs = [{"title": "Контакты"}]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not all([name, email, subject, message]):
            flash("Заполните все поля формы обратной связи.", "error")
            return render_template("contacts.html", form_data=request.form, breadcrumbs=breadcrumbs)

        if not is_valid_email(email):
            flash("Укажите корректный email адрес.", "error")
            return render_template("contacts.html", form_data=request.form, breadcrumbs=breadcrumbs)

        feedback = FeedbackMessage(name=name, email=email, subject=subject, message=message)
        db.session.add(feedback)
        db.session.commit()

        flash("Сообщение отправлено и сохранено в системе.", "success")
        return redirect(url_for("main.contacts"))

    return render_template("contacts.html", form_data={}, breadcrumbs=breadcrumbs)


@main_bp.route("/analytics")
@login_required
def analytics():
    ensure_predictions()
    clients = Client.query.order_by(Client.churn_probability.desc(), Client.id.asc()).all()
    active_model = get_active_model()
    metrics_bundle = model_metrics(active_model)
    current_metrics = metrics_bundle.get("metrics", {})
    baseline_metrics = metrics_bundle.get("baseline_metrics", {})
    feature_importances = metrics_bundle.get("feature_importances", [])
    confusion = metrics_bundle.get("confusion_matrix", {})

    total_clients = len(clients)
    avg_probability = round(sum((client.churn_probability or 0.0) for client in clients) / total_clients, 4) if clients else 0
    high_risk_count = sum(1 for client in clients if client.risk_level == "Высокий")
    medium_risk_count = sum(1 for client in clients if client.risk_level == "Средний")
    low_risk_count = sum(1 for client in clients if client.risk_level == "Низкий")

    status_counts = {}
    city_counts = {}
    for client in clients:
        status_counts[client.status] = status_counts.get(client.status, 0) + 1
        city_counts[client.city] = city_counts.get(client.city, 0) + 1

    return render_template(
        "analytics.html",
        total_clients=total_clients,
        avg_probability=avg_probability,
        high_risk_count=high_risk_count,
        medium_risk_count=medium_risk_count,
        low_risk_count=low_risk_count,
        status_counts=status_counts,
        city_counts=city_counts,
        top_clients=clients[:5],
        active_model=active_model,
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics,
        feature_importances=feature_importances,
        confusion=confusion,
        latest_run=latest_prediction_run(),
        breadcrumbs=[*base_breadcrumbs(), {"title": "AI-аналитика"}],
    )


@main_bp.route("/segments")
@login_required
def segments():
    ensure_predictions()
    clients = Client.query.order_by(Client.churn_probability.desc(), Client.full_name.asc()).all()
    segments_map = {"Высокий риск": [], "Средний риск": [], "Низкий риск": []}

    for client in clients:
        if client.risk_level == "Высокий":
            segments_map["Высокий риск"].append(client)
        elif client.risk_level == "Средний":
            segments_map["Средний риск"].append(client)
        else:
            segments_map["Низкий риск"].append(client)

    return render_template(
        "segments.html",
        segments_map=segments_map,
        breadcrumbs=[*base_breadcrumbs(), {"title": "Сегментация"}],
    )


@main_bp.route("/reports")
@login_required
def reports():
    ensure_predictions()
    prediction_runs = PredictionRun.query.order_by(PredictionRun.created_at.desc()).limit(10).all()
    models = ModelArtifact.query.order_by(ModelArtifact.trained_at.desc()).all()
    datasets = DatasetAsset.query.order_by(DatasetAsset.created_at.desc()).all()
    clients = Client.query.order_by(Client.churn_probability.desc(), Client.id.asc()).all()

    risk_counts = {"Высокий": 0, "Средний": 0, "Низкий": 0}
    for client in clients:
        risk_counts[client.risk_level or "Низкий"] = risk_counts.get(client.risk_level or "Низкий", 0) + 1

    return render_template(
        "reports.html",
        prediction_runs=prediction_runs,
        models=models,
        datasets=datasets,
        risk_counts=risk_counts,
        latest_run=prediction_runs[0] if prediction_runs else None,
        breadcrumbs=[*base_breadcrumbs(), {"title": "Отчеты"}],
    )


@main_bp.route("/reports/export")
@login_required
def reports_export():
    ensure_predictions()
    clients = Client.query.order_by(Client.id.asc()).all()

    output = StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "ID",
            "Код клиента",
            "ФИО",
            "Email",
            "Телефон",
            "Город",
            "Статус",
            "Тип контракта",
            "Ежемесячная выручка",
            "Вероятность оттока",
            "Риск",
            "Рекомендация",
        ]
    )

    for client in clients:
        writer.writerow(
            [
                client.id,
                client.customer_code,
                client.full_name,
                client.email,
                client.phone,
                client.city,
                client.status,
                client.contract_type,
                client.monthly_charges,
                client.churn_probability,
                client.risk_level,
                next_best_action(client),
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=crm_ai_report.csv"},
    )


@main_bp.route("/reports/export-predictions")
@login_required
def reports_export_predictions():
    run = latest_prediction_run()
    if run is None:
        flash("Сначала выполните прогнозирование клиентской базы.", "error")
        return redirect(url_for("main.reports"))

    return send_file(
        run.file_path,
        as_attachment=True,
        download_name=Path(run.file_path).name,
    )


@main_bp.route("/clients")
@login_required
def clients():
    ensure_predictions()
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    risk = request.args.get("risk", "").strip()

    clients_list = Client.query.order_by(Client.churn_probability.desc(), Client.id.asc()).all()

    if search:
        normalized_search = search.casefold()
        clients_list = [
            client
            for client in clients_list
            if normalized_search in client.full_name.casefold()
            or normalized_search in client.email.casefold()
            or normalized_search in client.customer_code.casefold()
        ]

    if status:
        clients_list = [client for client in clients_list if client.status == status]

    if risk:
        clients_list = [client for client in clients_list if client.risk_level == risk]

    return render_template(
        "clients.html",
        clients=clients_list,
        search=search,
        selected_status=status,
        selected_risk=risk,
        statuses=CLIENT_STATUS_CHOICES,
        risk_levels=["Высокий", "Средний", "Низкий"],
        breadcrumbs=[*base_breadcrumbs(), {"title": "CRM-клиенты"}],
    )


@main_bp.route("/clients/create", methods=["GET", "POST"])
@login_required
def client_create():
    breadcrumbs = [*base_breadcrumbs(), {"title": "CRM-клиенты", "endpoint": "main.clients"}, {"title": "Новый клиент"}]

    if request.method == "POST":
        payload, errors = parse_client_payload()

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "client_create.html",
                form_data=payload,
                statuses=CLIENT_STATUS_CHOICES,
                contract_choices=CONTRACT_CHOICES,
                payment_choices=PAYMENT_CHOICES,
                internet_choices=INTERNET_CHOICES,
                breadcrumbs=breadcrumbs,
            )

        if Client.query.filter_by(email=payload["email"]).first() is not None:
            flash("Клиент с таким email уже существует.", "error")
            return render_template(
                "client_create.html",
                form_data=payload,
                statuses=CLIENT_STATUS_CHOICES,
                contract_choices=CONTRACT_CHOICES,
                payment_choices=PAYMENT_CHOICES,
                internet_choices=INTERNET_CHOICES,
                breadcrumbs=breadcrumbs,
            )

        if Client.query.filter_by(customer_code=payload["customer_code"]).first() is not None:
            flash("Клиент с таким кодом уже существует.", "error")
            return render_template(
                "client_create.html",
                form_data=payload,
                statuses=CLIENT_STATUS_CHOICES,
                contract_choices=CONTRACT_CHOICES,
                payment_choices=PAYMENT_CHOICES,
                internet_choices=INTERNET_CHOICES,
                breadcrumbs=breadcrumbs,
            )

        client = Client(**payload)
        db.session.add(client)
        db.session.commit()

        sync_client_predictions()
        flash("CRM-клиент успешно добавлен и готов к AI-анализу.", "success")
        return redirect(url_for("main.client_detail", client_id=client.id))

    suggested_code = f"CRM-{1000 + Client.query.count() + 1}"
    form_data = build_client_form_data({"customer_code": suggested_code})
    return render_template(
        "client_create.html",
        form_data=form_data,
        statuses=CLIENT_STATUS_CHOICES,
        contract_choices=CONTRACT_CHOICES,
        payment_choices=PAYMENT_CHOICES,
        internet_choices=INTERNET_CHOICES,
        breadcrumbs=breadcrumbs,
    )


@main_bp.route("/clients/<int:client_id>")
@login_required
def client_detail(client_id: int):
    ensure_predictions()
    client = Client.query.get_or_404(client_id)
    return render_template(
        "client_detail.html",
        client=client,
        next_action=next_best_action(client),
        breadcrumbs=[
            *base_breadcrumbs(),
            {"title": "CRM-клиенты", "endpoint": "main.clients"},
            {"title": "Карточка клиента"},
        ],
    )


@main_bp.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def client_edit(client_id: int):
    client = Client.query.get_or_404(client_id)
    breadcrumbs = [
        *base_breadcrumbs(),
        {"title": "CRM-клиенты", "endpoint": "main.clients"},
        {"title": "Карточка клиента", "endpoint": "main.client_detail", "params": {"client_id": client.id}},
        {"title": "Редактирование"},
    ]

    if request.method == "POST":
        payload, errors = parse_client_payload()
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "client_edit.html",
                form_data=payload,
                statuses=CLIENT_STATUS_CHOICES,
                contract_choices=CONTRACT_CHOICES,
                payment_choices=PAYMENT_CHOICES,
                internet_choices=INTERNET_CHOICES,
                breadcrumbs=breadcrumbs,
            )

        existing_client = Client.query.filter(Client.email == payload["email"], Client.id != client.id).first()
        if existing_client is not None:
            flash("Другой клиент с таким email уже существует.", "error")
            return render_template(
                "client_edit.html",
                form_data=payload,
                statuses=CLIENT_STATUS_CHOICES,
                contract_choices=CONTRACT_CHOICES,
                payment_choices=PAYMENT_CHOICES,
                internet_choices=INTERNET_CHOICES,
                breadcrumbs=breadcrumbs,
            )

        existing_code = Client.query.filter(Client.customer_code == payload["customer_code"], Client.id != client.id).first()
        if existing_code is not None:
            flash("Другой клиент с таким кодом уже существует.", "error")
            return render_template(
                "client_edit.html",
                form_data=payload,
                statuses=CLIENT_STATUS_CHOICES,
                contract_choices=CONTRACT_CHOICES,
                payment_choices=PAYMENT_CHOICES,
                internet_choices=INTERNET_CHOICES,
                breadcrumbs=breadcrumbs,
            )

        for key, value in payload.items():
            setattr(client, key, value)

        db.session.commit()
        sync_client_predictions()
        flash("Карточка клиента обновлена и пересчитана моделью.", "success")
        return redirect(url_for("main.client_detail", client_id=client.id))

    return render_template(
        "client_edit.html",
        form_data=build_client_form_data(client),
        statuses=CLIENT_STATUS_CHOICES,
        contract_choices=CONTRACT_CHOICES,
        payment_choices=PAYMENT_CHOICES,
        internet_choices=INTERNET_CHOICES,
        breadcrumbs=breadcrumbs,
    )


@main_bp.route("/clients/<int:client_id>/delete", methods=["POST"])
@login_required
def client_delete(client_id: int):
    client = Client.query.get_or_404(client_id)
    client_name = client.full_name

    db.session.delete(client)
    db.session.commit()
    sync_client_predictions()

    flash(f"Клиент {client_name} удален.", "success")
    return redirect(url_for("main.clients"))


@main_bp.route("/ml-lab")
@login_required
def ml_lab():
    datasets = DatasetAsset.query.order_by(DatasetAsset.created_at.desc()).all()
    models = ModelArtifact.query.order_by(ModelArtifact.trained_at.desc()).all()
    active_model = get_active_model()
    preview_target = datasets[0] if datasets else None
    preview_rows = dataset_preview(preview_target) if preview_target else []
    metrics_bundle = model_metrics(active_model)

    return render_template(
        "ml_lab.html",
        datasets=datasets,
        models=models,
        active_model=active_model,
        preview_rows=preview_rows,
        preview_headers=list(preview_rows[0].keys()) if preview_rows else [],
        current_metrics=metrics_bundle.get("metrics", {}),
        baseline_metrics=metrics_bundle.get("baseline_metrics", {}),
        feature_importances=metrics_bundle.get("feature_importances", []),
        confusion=metrics_bundle.get("confusion_matrix", {}),
        latest_run=latest_prediction_run(),
        breadcrumbs=[*base_breadcrumbs(), {"title": "ML-лаборатория"}],
    )


@main_bp.route("/ml-lab/upload-dataset", methods=["POST"])
@login_required
def ml_upload_dataset():
    dataset_file = request.files.get("dataset_file")
    if dataset_file is None or not dataset_file.filename:
        flash("Выберите CSV-файл для загрузки датасета.", "error")
        return redirect(url_for("main.ml_lab"))

    try:
        register_uploaded_dataset(dataset_file)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("main.ml_lab"))

    flash("Датасет успешно загружен и зарегистрирован в системе.", "success")
    return redirect(url_for("main.ml_lab"))


@main_bp.route("/ml-lab/import-url", methods=["POST"])
@login_required
def ml_import_url():
    source_url = request.form.get("source_url", "").strip()
    if not source_url:
        flash("Укажите ссылку на CSV-файл.", "error")
        return redirect(url_for("main.ml_lab"))

    try:
        register_dataset_from_url(source_url)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("main.ml_lab"))
    except Exception:
        flash("Не удалось загрузить датасет по указанной ссылке.", "error")
        return redirect(url_for("main.ml_lab"))

    flash("Внешний датасет загружен и доступен для обучения модели.", "success")
    return redirect(url_for("main.ml_lab"))


@main_bp.route("/ml-lab/train", methods=["POST"])
@login_required
def ml_train():
    dataset_id = request.form.get("dataset_id", type=int)
    algorithm = request.form.get("algorithm", "random_forest").strip()

    dataset = DatasetAsset.query.get_or_404(dataset_id)
    artifact = train_model(dataset, algorithm=algorithm)

    flash(
        f"Модель обучена. Accuracy: {artifact.accuracy:.3f}, F1: {artifact.f1_score:.3f}, ROC-AUC: {artifact.roc_auc:.3f}.",
        "success",
    )
    return redirect(url_for("main.ml_lab"))


@main_bp.route("/ml-lab/models/activate", methods=["POST"])
@login_required
def ml_activate_model():
    model_id = request.form.get("model_id", type=int)
    activate_model(model_id)
    flash("Модель активирована и повторно применена к CRM-клиентам.", "success")
    return redirect(url_for("main.ml_lab"))


@main_bp.route("/ml-lab/predict-clients", methods=["POST"])
@login_required
def ml_predict_clients():
    run = sync_client_predictions()
    if run is None:
        flash("Нет активной модели или клиентской базы для прогнозирования.", "error")
        return redirect(url_for("main.ml_lab"))

    flash(f"Прогнозирование завершено. Обработано клиентов: {run.rows_scored}.", "success")
    return redirect(url_for("main.ml_lab"))


@main_bp.route("/integration", methods=["GET", "POST"])
@login_required
def integration():
    setting = IntegrationSetting.query.filter_by(service_name="bitrix24").first()
    logs = IntegrationLog.query.filter_by(service_name="bitrix24").order_by(IntegrationLog.id.desc()).limit(5).all()

    if request.method == "POST":
        webhook_url = request.form.get("webhook_url", "").strip()
        is_active = request.form.get("is_active") == "on"

        if not webhook_url:
            flash("Укажите webhook URL для интеграции.", "error")
            return render_template(
                "integration.html",
                setting=setting,
                logs=logs,
                form_data=request.form,
                breadcrumbs=[*base_breadcrumbs(), {"title": "Интеграция Bitrix24"}],
            )

        if setting is None:
            setting = IntegrationSetting(service_name="bitrix24", webhook_url=webhook_url, is_active=is_active)
            db.session.add(setting)
        else:
            setting.webhook_url = webhook_url
            setting.is_active = is_active

        db.session.commit()
        flash("Настройки интеграции сохранены.", "success")
        return redirect(url_for("main.integration"))

    return render_template(
        "integration.html",
        setting=setting,
        logs=logs,
        form_data={
            "webhook_url": setting.webhook_url if setting else "",
            "is_active": setting.is_active if setting else False,
        },
        breadcrumbs=[*base_breadcrumbs(), {"title": "Интеграция Bitrix24"}],
    )


@main_bp.route("/integration/check", methods=["POST"])
@login_required
def integration_check():
    setting = IntegrationSetting.query.filter_by(service_name="bitrix24").first()
    if setting is None or not setting.webhook_url:
        flash("Сначала сохраните webhook URL для интеграции.", "error")
        return redirect(url_for("main.integration"))

    check_url = setting.webhook_url.rstrip("/") + "/profile.json"
    try:
        response = requests.get(check_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "result" in data:
            db.session.add(
                IntegrationLog(
                    service_name="bitrix24",
                    operation="check_connection",
                    status="success",
                    message="Подключение к Bitrix24 успешно проверено.",
                )
            )
            db.session.commit()
            flash("Подключение к Bitrix24 успешно проверено.", "success")
        else:
            db.session.add(
                IntegrationLog(
                    service_name="bitrix24",
                    operation="check_connection",
                    status="error",
                    message="Bitrix24 ответил без ожидаемого результата.",
                )
            )
            db.session.commit()
            flash("Bitrix24 ответил без ожидаемого результата.", "error")
    except requests.RequestException:
        db.session.add(
            IntegrationLog(
                service_name="bitrix24",
                operation="check_connection",
                status="error",
                message="Не удалось подключиться к Bitrix24 по указанному webhook URL.",
            )
        )
        db.session.commit()
        flash("Не удалось подключиться к Bitrix24 по указанному webhook URL.", "error")
    except ValueError:
        db.session.add(
            IntegrationLog(
                service_name="bitrix24",
                operation="check_connection",
                status="error",
                message="Bitrix24 вернул некорректный формат ответа.",
            )
        )
        db.session.commit()
        flash("Bitrix24 вернул некорректный формат ответа.", "error")

    return redirect(url_for("main.integration"))


@main_bp.route("/integration/import-clients", methods=["POST"])
@login_required
def integration_import_clients():
    setting = IntegrationSetting.query.filter_by(service_name="bitrix24").first()
    if setting is None or not setting.webhook_url:
        flash("Сначала сохраните webhook URL для интеграции.", "error")
        return redirect(url_for("main.integration"))

    import_url = setting.webhook_url.rstrip("/") + "/crm.contact.list.json"
    try:
        response = requests.get(
            import_url,
            params={"select[]": ["NAME", "LAST_NAME", "PHONE", "EMAIL", "ADDRESS_CITY"]},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("result", [])

        imported_count = 0
        for item in items:
            first_name = (item.get("NAME") or "").strip()
            last_name = (item.get("LAST_NAME") or "").strip()
            full_name = " ".join(part for part in [first_name, last_name] if part).strip() or "Клиент без имени"

            email_list = item.get("EMAIL") or []
            phone_list = item.get("PHONE") or []
            email = (email_list[0].get("VALUE") or "").strip().lower() if email_list else ""
            phone = (phone_list[0].get("VALUE") or "").strip() if phone_list else ""

            if not email or Client.query.filter_by(email=email).first() is not None:
                continue

            client = Client(
                full_name=full_name,
                email=email,
                phone=phone or "Не указан",
                city=(item.get("ADDRESS_CITY") or "").strip() or "Не указан",
                status="Импортирован из Bitrix24",
                customer_code=f"BITRIX-{10000 + imported_count + 1}",
                tenure_months=1,
                monthly_charges=59.0,
                total_charges=59.0,
                service_count=1,
                contract_type="Month-to-month",
                payment_method="Electronic check",
                internet_service="DSL",
                paperless_billing=True,
                has_family_plan=False,
                has_tech_support=False,
            )
            db.session.add(client)
            imported_count += 1

        db.session.add(
            IntegrationLog(
                service_name="bitrix24",
                operation="import_clients",
                status="success",
                message=f"Импортировано клиентов: {imported_count}",
            )
        )
        db.session.commit()
        sync_client_predictions()
        flash(f"Импорт завершен. Добавлено записей: {imported_count}.", "success")
    except requests.RequestException:
        db.session.add(
            IntegrationLog(
                service_name="bitrix24",
                operation="import_clients",
                status="error",
                message="Не удалось выполнить импорт клиентов из Bitrix24.",
            )
        )
        db.session.commit()
        flash("Не удалось выполнить импорт клиентов из Bitrix24.", "error")
    except ValueError:
        db.session.add(
            IntegrationLog(
                service_name="bitrix24",
                operation="import_clients",
                status="error",
                message="Bitrix24 вернул некорректный ответ при импорте клиентов.",
            )
        )
        db.session.commit()
        flash("Bitrix24 вернул некорректный ответ при импорте клиентов.", "error")

    return redirect(url_for("main.integration"))


@main_bp.route("/integration/logs")
@login_required
def integration_logs():
    logs = IntegrationLog.query.filter_by(service_name="bitrix24").order_by(IntegrationLog.id.desc()).all()
    return render_template(
        "integration_logs.html",
        logs=logs,
        breadcrumbs=[
            *base_breadcrumbs(),
            {"title": "Интеграция Bitrix24", "endpoint": "main.integration"},
            {"title": "Журнал операций"},
        ],
    )


@main_bp.route("/dashboard")
@login_required
def dashboard():
    ensure_predictions()
    return render_template(
        "dashboard.html",
        user=g.current_user,
        active_model=get_active_model(),
        high_risk_count=Client.query.filter_by(risk_level="Высокий").count(),
        datasets_count=DatasetAsset.query.count(),
        breadcrumbs=[*base_breadcrumbs(), {"title": "Личный кабинет"}],
    )


@main_bp.route("/admin")
@role_required("Администратор")
def admin_panel():
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "").strip()

    users = User.query.order_by(User.id.asc()).all()
    roles = Role.query.order_by(Role.name.asc()).all()

    if search:
        normalized_search = search.casefold()
        users = [
            user
            for user in users
            if normalized_search in user.full_name.casefold() or normalized_search in user.email.casefold()
        ]

    if role_filter:
        users = [user for user in users if user.role.name == role_filter]

    return render_template(
        "admin.html",
        users=users,
        roles=roles,
        search=search,
        selected_role=role_filter,
        breadcrumbs=[*base_breadcrumbs(), {"title": "Панель администратора"}],
    )


@main_bp.route("/admin/users/create", methods=["GET", "POST"])
@role_required("Администратор")
def admin_user_create():
    roles = Role.query.order_by(Role.name.asc()).all()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        role_id = request.form.get("role_id", type=int)
        is_active = request.form.get("is_active") == "on"

        if not all([full_name, email, password, role_id]):
            flash("Заполните все обязательные поля.", "error")
            return render_template(
                "admin_user_create.html",
                roles=roles,
                form_data=request.form,
                breadcrumbs=[
                    *base_breadcrumbs(),
                    {"title": "Панель администратора", "endpoint": "main.admin_panel"},
                    {"title": "Новый пользователь"},
                ],
            )

        if not is_valid_email(email):
            flash("Укажите корректный email адрес пользователя.", "error")
            return render_template(
                "admin_user_create.html",
                roles=roles,
                form_data=request.form,
                breadcrumbs=[
                    *base_breadcrumbs(),
                    {"title": "Панель администратора", "endpoint": "main.admin_panel"},
                    {"title": "Новый пользователь"},
                ],
            )

        if User.query.filter_by(email=email).first() is not None:
            flash("Пользователь с таким email уже существует.", "error")
            return render_template(
                "admin_user_create.html",
                roles=roles,
                form_data=request.form,
                breadcrumbs=[
                    *base_breadcrumbs(),
                    {"title": "Панель администратора", "endpoint": "main.admin_panel"},
                    {"title": "Новый пользователь"},
                ],
            )

        user = User(full_name=full_name, email=email, role_id=role_id, is_active=is_active)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Пользователь успешно создан.", "success")
        return redirect(url_for("main.admin_user_detail", user_id=user.id))

    return render_template(
        "admin_user_create.html",
        roles=roles,
        form_data={},
        breadcrumbs=[
            *base_breadcrumbs(),
            {"title": "Панель администратора", "endpoint": "main.admin_panel"},
            {"title": "Новый пользователь"},
        ],
    )


@main_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@role_required("Администратор")
def admin_user_delete(user_id: int):
    user = User.query.get_or_404(user_id)

    if session.get("user_id") == user.id:
        flash("Нельзя удалить текущую учетную запись администратора.", "error")
        return redirect(url_for("main.admin_user_detail", user_id=user.id))

    user_name = user.full_name
    db.session.delete(user)
    db.session.commit()

    flash(f"Пользователь {user_name} удален.", "success")
    return redirect(url_for("main.admin_panel"))


@main_bp.route("/admin/roles")
@role_required("Администратор")
def admin_roles():
    roles = Role.query.order_by(Role.id.asc()).all()
    return render_template(
        "admin_roles.html",
        roles=roles,
        breadcrumbs=[
            *base_breadcrumbs(),
            {"title": "Панель администратора", "endpoint": "main.admin_panel"},
            {"title": "Роли"},
        ],
    )


@main_bp.route("/admin/feedback")
@role_required("Администратор")
def admin_feedback():
    messages = FeedbackMessage.query.order_by(FeedbackMessage.id.desc()).all()
    return render_template(
        "admin_feedback.html",
        messages=messages,
        breadcrumbs=[
            *base_breadcrumbs(),
            {"title": "Панель администратора", "endpoint": "main.admin_panel"},
            {"title": "Обращения"},
        ],
    )


@main_bp.route("/admin/feedback/<int:message_id>")
@role_required("Администратор")
def admin_feedback_detail(message_id: int):
    message = FeedbackMessage.query.get_or_404(message_id)
    if not message.status:
        message.status = "Новое"
        db.session.commit()
    return render_template(
        "admin_feedback_detail.html",
        message=message,
        statuses=["Новое", "В работе", "Закрыто"],
        breadcrumbs=[
            *base_breadcrumbs(),
            {"title": "Панель администратора", "endpoint": "main.admin_panel"},
            {"title": "Обращения", "endpoint": "main.admin_feedback"},
            {"title": "Карточка обращения"},
        ],
    )


@main_bp.route("/admin/feedback/<int:message_id>/status", methods=["POST"])
@role_required("Администратор")
def admin_feedback_update_status(message_id: int):
    message = FeedbackMessage.query.get_or_404(message_id)
    new_status = request.form.get("status", "").strip()

    if new_status not in {"Новое", "В работе", "Закрыто"}:
        flash("Выбран некорректный статус обращения.", "error")
        return redirect(url_for("main.admin_feedback_detail", message_id=message.id))

    message.status = new_status
    db.session.commit()

    flash("Статус обращения обновлен.", "success")
    return redirect(url_for("main.admin_feedback_detail", message_id=message.id))


@main_bp.route("/admin/users/<int:user_id>", methods=["GET", "POST"])
@role_required("Администратор")
def admin_user_detail(user_id: int):
    user = User.query.get_or_404(user_id)
    roles = Role.query.order_by(Role.name.asc()).all()

    if request.method == "POST":
        role_id = request.form.get("role_id", type=int)
        is_active = request.form.get("is_active") == "on"

        role = Role.query.get(role_id)
        if role is None:
            flash("Выбрана некорректная роль.", "error")
            return redirect(url_for("main.admin_user_detail", user_id=user.id))

        user.role_id = role.id
        user.is_active = is_active
        db.session.commit()

        flash("Данные пользователя обновлены.", "success")
        return redirect(url_for("main.admin_user_detail", user_id=user.id))

    return render_template(
        "admin_user_detail.html",
        user=user,
        roles=roles,
        breadcrumbs=[
            *base_breadcrumbs(),
            {"title": "Панель администратора", "endpoint": "main.admin_panel"},
            {"title": "Карточка пользователя"},
        ],
    )


@main_bp.route("/recommendations")
@login_required
def recommendations():
    ensure_predictions()
    clients = Client.query.order_by(Client.churn_probability.desc(), Client.id.asc()).all()
    grouped_clients = {"Высокий приоритет": [], "Средний приоритет": [], "Плановое сопровождение": []}

    for client in clients:
        row = {"client": client, "action": next_best_action(client)}
        if client.risk_level == "Высокий":
            grouped_clients["Высокий приоритет"].append(row)
        elif client.risk_level == "Средний":
            grouped_clients["Средний приоритет"].append(row)
        else:
            grouped_clients["Плановое сопровождение"].append(row)

    return render_template(
        "recommendations.html",
        grouped_clients=grouped_clients,
        active_model=get_active_model(),
        breadcrumbs=[*base_breadcrumbs(), {"title": "Рекомендации"}],
    )


@main_bp.route("/profile")
@login_required
def profile():
    return render_template(
        "profile.html",
        user=g.current_user,
        breadcrumbs=[
            *base_breadcrumbs(),
            {"title": "Личный кабинет", "endpoint": "main.dashboard"},
            {"title": "Профиль"},
        ],
    )


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not is_valid_email(email):
            flash("Укажите корректный email адрес.", "error")
            return render_template("login.html", breadcrumbs=[*base_breadcrumbs(), {"title": "Вход"}])

        user = User.query.filter_by(email=email, is_active=True).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_name"] = user.full_name
            session["role_name"] = user.role.name
            flash("Вход выполнен успешно.", "success")
            return redirect(url_for("main.dashboard"))

        flash("Неверный email или пароль.", "error")

    return render_template("login.html", breadcrumbs=[*base_breadcrumbs(), {"title": "Вход"}])


@main_bp.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы.", "success")
    return redirect(url_for("main.index"))
