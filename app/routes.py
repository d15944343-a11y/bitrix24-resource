from flask import Blueprint, render_template


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
def dashboard():
    return render_template(
        "dashboard.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Личный кабинет"},
        ],
    )


@main_bp.route("/admin")
def admin_panel():
    return render_template(
        "admin.html",
        breadcrumbs=[
            {"title": "Главная", "endpoint": "main.index"},
            {"title": "Панель администратора"},
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
