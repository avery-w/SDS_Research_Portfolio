from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user, current_user

from app.extensions import db
from app.models import User
from app.utils.sanitize import sanitize_text


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = sanitize_text(request.form.get("email", ""), max_length=120)
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email.lower()).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            flash("You have been logged in.", "success")
            return redirect(url_for("customer.dashboard"))

        flash("Invalid login credentials.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = sanitize_text(request.form.get("name", ""), max_length=120)
        email = sanitize_text(request.form.get("email", ""), max_length=120).lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "warning")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "warning")
            return render_template("auth/register.html")

        user = User(name=name, email=email, role="customer")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
