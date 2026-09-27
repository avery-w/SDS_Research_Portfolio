import re
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db

bp = Blueprint("auth", __name__)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
# ponytail: in-memory limits are per process, point storage_uri at Redis when running multiple workers.
limiter = Limiter(get_remote_address, storage_uri="memory://")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
DUMMY_HASH = generate_password_hash("timing-equalizer")


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user if user and user.active else None  # deactivated accounts are logged out on next request


def role_required(*roles):
    def deco(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return deco


def clean(name, max_len, required=True, source=None):
    """Trimmed, length-checked form field. Raises ValueError with a user facing message."""
    value = (source or request.form).get(name, "").strip()
    if required and not value:
        raise ValueError(f"{name.replace('_', ' ').capitalize()} is required.")
    if len(value) > max_len:
        raise ValueError(f"{name.replace('_', ' ').capitalize()} must be at most {max_len} characters.")
    return value


def clean_address(source=None):
    street, city = clean("street", 200, source=source), clean("city", 100, source=source)
    state, zip_code = clean("state", 2, source=source).upper(), clean("zip", 5, source=source)
    if not re.fullmatch(r"[A-Z]{2}", state) or not re.fullmatch(r"\d{5}", zip_code):
        raise ValueError("Use a 2 letter state and 5 digit ZIP.")
    return street, city, state, zip_code


def check_password(pw):
    if len(pw) < 10 or len(pw) > 128:
        raise ValueError("Password must be 10 to 128 characters.")


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    if request.method == "POST":
        try:
            name, email = clean("name", 100), clean("email", 254).lower()
            password = request.form.get("password", "")
            role = request.form.get("role", "customer")
            if not EMAIL_RE.fullmatch(email):
                raise ValueError("Enter a valid email.")
            check_password(password)
            if role not in ("customer", "seller"):  # admins are only created from the CLI
                raise ValueError("Invalid account type.")
            if db.session.scalar(select(User).filter_by(email=email)):
                raise ValueError("That email is already registered.")
        except ValueError as e:
            flash(str(e), "error")
            return render_template("auth.html", mode="register"), 400
        user = User(name=name, email=email, role=role, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("seller.dashboard" if role == "seller" else "shop.index"))
    return render_template("auth.html", mode="register")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        user = db.session.scalar(select(User).filter_by(email=email))
        ok = check_password_hash(user.password_hash if user else DUMMY_HASH, request.form.get("password", ""))
        if user and ok and user.active:
            login_user(user)
            return redirect(url_for("shop.index"))  # no ?next= redirect, so no open redirect
        flash("Invalid email or password.", "error")
        return render_template("auth.html", mode="login"), 401
    return render_template("auth.html", mode="login")


@bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("shop.index"))


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        try:
            current_user.name = clean("name", 100)
            if request.form.get("street"):
                current_user.street, current_user.city, current_user.state, current_user.zip = clean_address()
            new_pw = request.form.get("new_password", "")
            if new_pw:
                if not check_password_hash(current_user.password_hash, request.form.get("current_password", "")):
                    raise ValueError("Current password is incorrect.")
                check_password(new_pw)
                current_user.password_hash = generate_password_hash(new_pw)
            db.session.commit()
            flash("Account updated.", "ok")
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "error")
        return redirect(url_for("auth.account"))
    return render_template("account.html")
