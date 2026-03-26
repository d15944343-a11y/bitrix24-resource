from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Для доступа к разделу выполните вход.", "error")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not session.get("user_id"):
                flash("Для доступа к разделу выполните вход.", "error")
                return redirect(url_for("main.login"))

            if session.get("role_name") not in allowed_roles:
                flash("Недостаточно прав для доступа к разделу.", "error")
                return redirect(url_for("main.index"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator
