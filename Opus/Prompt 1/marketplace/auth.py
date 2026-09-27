import re
from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from .models import User, db

bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        email = f.get("email", "").strip().lower()
        name = f.get("name", "").strip()
        password = f.get("password", "")
        role = f.get("role") if f.get("role") in ("customer", "seller") else "customer"
        error = None
        if not EMAIL_RE.match(email):
            error = "Enter a valid email."
        elif not name:
            error = "Enter your name."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif db.session.scalar(select(User).filter_by(email=email)):
            error = "That email is already registered."
        if error:
            flash(error, "error")
        else:
            user = User(email=email, name=name, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome! Set up your store to start selling." if role == "seller" else "Welcome!", "success")
            return redirect(url_for("seller.dashboard") if role == "seller" else url_for("shop.index"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db.session.scalar(select(User).filter_by(email=request.form.get("email", "").strip().lower()))
        if not user or not user.check_password(request.form.get("password", "")):
            flash("Invalid email or password.", "error")
        elif not user.active:
            flash("This account has been deactivated. Contact support.", "error")
        else:
            login_user(user, remember=bool(request.form.get("remember")))
            target = request.args.get("next", "")
            if not target.startswith("/") or urlsplit(target).netloc or target.startswith("//"):
                target = url_for("shop.index")  # block open redirects
            return redirect(target)
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("shop.index"))
