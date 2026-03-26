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
