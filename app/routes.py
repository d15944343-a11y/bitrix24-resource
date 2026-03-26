from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
import requests

from .auth import login_required, role_required
from .extensions import db
from .models import Client, FeedbackMessage, IntegrationLog, IntegrationSetting, Role, User


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html", breadcrumbs=[{"title": "Главная"}])


@main_bp.route("/about")
def about():
    return render_template(
        "about.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "О проекте"},
        ],
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

        feedback = FeedbackMessage(name=name, email=email, subject=subject, message=message)
        db.session.add(feedback)
        db.session.commit()

        flash("Сообщение отправлено и сохранено в системе.", "success")
        return redirect(url_for("main.contacts"))

    return render_template("contacts.html", form_data={}, breadcrumbs=breadcrumbs)


@main_bp.route("/analytics")
def analytics():
    return render_template(
        "analytics.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Аналитика"},
        ],
    )


@main_bp.route("/segments")
def segments():
    return render_template(
        "segments.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Сегментация"},
        ],
    )


@main_bp.route("/reports")
def reports():
    return render_template(
        "reports.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Отчеты"},
        ],
    )


@main_bp.route("/clients")
@login_required
def clients():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    clients_list = Client.query.order_by(Client.id.asc()).all()

    if search:
        normalized_search = search.casefold()
        clients_list = [
            client
            for client in clients_list
            if normalized_search in client.full_name.casefold()
            or normalized_search in client.email.casefold()
        ]

    if status:
        clients_list = [client for client in clients_list if client.status == status]

    statuses = sorted({client.status for client in Client.query.all()})

    return render_template(
        "clients.html",
        clients=clients_list,
        search=search,
        selected_status=status,
        statuses=statuses,
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Клиенты"},
        ],
    )


@main_bp.route("/clients/create", methods=["GET", "POST"])
@login_required
def client_create():
    breadcrumbs = [
        {"title": "Главная", "endpoint": "main.index"},
        {"title": "Клиенты", "endpoint": "main.clients"},
        {"title": "Новый клиент"},
    ]

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        city = request.form.get("city", "").strip()
        status = request.form.get("status", "").strip()

        if not all([full_name, email, phone, city, status]):
            flash("Заполните все поля формы.", "error")
            return render_template("client_create.html", form_data=request.form, breadcrumbs=breadcrumbs)

        existing_client = Client.query.filter_by(email=email).first()
        if existing_client is not None:
            flash("Клиент с таким email уже существует.", "error")
            return render_template("client_create.html", form_data=request.form, breadcrumbs=breadcrumbs)

        client = Client(full_name=full_name, email=email, phone=phone, city=city, status=status)
        db.session.add(client)
        db.session.commit()

        flash("Клиент успешно добавлен.", "success")
        return redirect(url_for("main.client_detail", client_id=client.id))

    return render_template("client_create.html", form_data={}, breadcrumbs=breadcrumbs)


@main_bp.route("/clients/<int:client_id>")
@login_required
def client_detail(client_id: int):
    client = Client.query.get_or_404(client_id)
    return render_template(
        "client_detail.html",
        client=client,
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Клиенты", "endpoint": "main.clients"},
            {"title": "Карточка клиента"},
        ],
    )


@main_bp.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def client_edit(client_id: int):
    client = Client.query.get_or_404(client_id)
    breadcrumbs = [
        {"title": "Главная", "endpoint": "main.index"},
        {"title": "Клиенты", "endpoint": "main.clients"},
        {"title": "Карточка клиента", "endpoint": "main.client_detail", "params": {"client_id": client.id}},
        {"title": "Редактирование"},
    ]

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        city = request.form.get("city", "").strip()
        status = request.form.get("status", "").strip()

        if not all([full_name, email, phone, city, status]):
            flash("Заполните все поля формы.", "error")
            return render_template("client_edit.html", form_data=request.form, breadcrumbs=breadcrumbs)

        existing_client = Client.query.filter(Client.email == email, Client.id != client.id).first()
        if existing_client is not None:
            flash("Другой клиент с таким email уже существует.", "error")
            return render_template("client_edit.html", form_data=request.form, breadcrumbs=breadcrumbs)

        client.full_name = full_name
        client.email = email
        client.phone = phone
        client.city = city
        client.status = status
        db.session.commit()

        flash("Данные клиента обновлены.", "success")
        return redirect(url_for("main.client_detail", client_id=client.id))

    return render_template(
        "client_edit.html",
        form_data={
            "full_name": client.full_name,
            "email": client.email,
            "phone": client.phone,
            "city": client.city,
            "status": client.status,
        },
        breadcrumbs=breadcrumbs,
    )


@main_bp.route("/clients/<int:client_id>/delete", methods=["POST"])
@login_required
def client_delete(client_id: int):
    client = Client.query.get_or_404(client_id)
    client_name = client.full_name

    db.session.delete(client)
    db.session.commit()

    flash(f"Клиент {client_name} удален.", "success")
    return redirect(url_for("main.clients"))


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
                form_data=request.form,
                breadcrumbs=[
                    {"title": "Главная", "endpoint": "main.index"},
                    {"title": "Интеграция Bitrix24"},
                ],
            )

        if setting is None:
            setting = IntegrationSetting(
                service_name="bitrix24",
                webhook_url=webhook_url,
                is_active=is_active,
            )
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
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Интеграция Bitrix24"},
        ],
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


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        user=g.current_user,
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Личный кабинет"},
        ],
    )


@main_bp.route("/admin")
@role_required("Администратор")
def admin_panel():
    users = User.query.order_by(User.id.asc()).all()
    return render_template(
        "admin.html",
        users=users,
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Панель администратора"},
        ],
    )


@main_bp.route("/admin/roles")
@role_required("Администратор")
def admin_roles():
    roles = Role.query.order_by(Role.id.asc()).all()
    return render_template(
        "admin_roles.html",
        roles=roles,
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
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
            {"title": "Главная", "endpoint": "main.index"},
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
            {"title": "Главная", "endpoint": "main.index"},
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
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Панель администратора", "endpoint": "main.admin_panel"},
            {"title": "Карточка пользователя"},
        ],
    )


@main_bp.route("/recommendations")
def recommendations():
    return render_template(
        "recommendations.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Рекомендации"},
        ],
    )


@main_bp.route("/profile")
@login_required
def profile():
    return render_template(
        "profile.html",
        user=g.current_user,
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Личный кабинет", "endpoint": "main.dashboard"},
            {"title": "Профиль"},
        ],
    )


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email, is_active=True).first()
        if user and user.password == password:
            session["user_id"] = user.id
            session["user_name"] = user.full_name
            session["role_name"] = user.role.name
            flash("Вход выполнен успешно.", "success")
            return redirect(url_for("main.dashboard"))

        flash("Неверный email или пароль.", "error")

    return render_template(
        "login.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Вход"},
        ],
    )


@main_bp.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы.", "success")
    return redirect(url_for("main.index"))
