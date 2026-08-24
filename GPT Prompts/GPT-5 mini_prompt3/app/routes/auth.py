from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import db
from app.models import User
from app.utils.sanitize import sanitize_email, sanitize_text


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = sanitize_email(request.form.get("email", ""))
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user)
            flash("Welcome back.", "success")
            return redirect(url_for("customer.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = sanitize_text(request.form.get("name", ""), max_length=120)
        email = sanitize_email(request.form.get("email", ""))
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Name, valid email, and password of at least 8 characters are required.", "warning")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "warning")
            return render_template("auth/register.html")

        user = User(name=name, email=email, role="customer")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
