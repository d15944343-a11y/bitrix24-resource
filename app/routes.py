from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from .auth import login_required, role_required
from .extensions import db
from .models import Client, Role, User


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template(
        "index.html",
        breadcrumbs=[{"title": "Главная"}],
    )


@main_bp.route("/about")
def about():
    return render_template(
        "about.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "О проекте"},
        ],
    )


@main_bp.route("/contacts")
def contacts():
    return render_template(
        "contacts.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Контакты"},
        ],
    )


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
    clients_list = Client.query.order_by(Client.id.asc()).all()
    return render_template(
        "clients.html",
        clients=clients_list,
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Клиенты"},
        ],
    )


@main_bp.route("/integration")
def integration():
    return render_template(
        "integration.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Интеграция Bitrix24"},
        ],
    )


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
