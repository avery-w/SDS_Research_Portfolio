from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User, UserRole

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", UserRole.CUSTOMER)
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        if not all([username, email, password, first_name, last_name]):
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.", "danger")
            return redirect(url_for("auth.register"))

        user = User(
            username=username, email=email,
            first_name=first_name, last_name=last_name,
            role=role,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.is_active_account:
            login_user(user)
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            elif user.is_seller:
                return redirect(url_for("seller.dashboard"))
            return redirect(url_for("customer.home"))

        flash("Invalid credentials or deactivated account.", "danger")
    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))
