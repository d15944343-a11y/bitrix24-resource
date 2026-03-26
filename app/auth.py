from functools import wraps

from flask import flash, g, redirect, session, url_for

from .models import User


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


def load_current_user():
    user_id = session.get("user_id")
    if user_id:
        g.current_user = User.query.get(user_id)
    else:
        g.current_user = None
