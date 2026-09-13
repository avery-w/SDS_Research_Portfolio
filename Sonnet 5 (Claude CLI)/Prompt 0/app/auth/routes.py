from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, Store, Cart, ROLE_CUSTOMER, ROLE_SELLER

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("customer.home"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        name = request.form["name"].strip()
        role = request.form.get("role", ROLE_CUSTOMER)
        if role not in (ROLE_CUSTOMER, ROLE_SELLER):
            role = ROLE_CUSTOMER

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("auth/register.html")

        user = User(email=email, name=name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        db.session.add(Cart(user_id=user.id))

        if role == ROLE_SELLER:
            store_name = request.form.get("store_name") or f"{name}'s Store"
            db.session.add(Store(seller_id=user.id, name=store_name))

        db.session.commit()
        login_user(user)
        flash("Welcome! Your account has been created.", "success")
        return redirect(url_for("customer.home"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("customer.home"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        if not user.is_active_user:
            flash("This account has been deactivated. Contact support.", "danger")
            return render_template("auth/login.html")

        login_user(user)
        next_url = request.args.get("next")
        return redirect(next_url or url_for("customer.home"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        current_user.name = request.form["name"].strip()
        current_user.address_line1 = request.form.get("address_line1", "").strip()
        current_user.city = request.form.get("city", "").strip()
        current_user.state = request.form.get("state", "").strip()
        current_user.zip_code = request.form.get("zip_code", "").strip()
        new_password = request.form.get("new_password")
        if new_password:
            current_user.set_password(new_password)
        db.session.commit()
        flash("Account updated.", "success")
        return redirect(url_for("auth.account"))

    return render_template("auth/account.html")
