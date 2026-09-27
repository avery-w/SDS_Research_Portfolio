from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.utils.sanitizers import sanitize_string
from app.utils.validators import validate_email
import re

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = sanitize_string(data.get("email", ""))
    password = data.get("password", "")
    first = sanitize_string(data.get("first_name", ""))
    last = sanitize_string(data.get("last_name", ""))
    role = data.get("role", "customer")
    if role not in ("customer", "seller"):
        return jsonify({"error": "Invalid role"}), 400
    if not validate_email(email):
        return jsonify({"error": "Invalid email"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password too short"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email exists"}), 409
    user = User(email=email, first_name=first, last_name=last, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"id": user.id, "email": user.email, "role": user.role}), 201

@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = sanitize_string(data.get("email", ""))
    password = data.get("password", "")
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password) and user.is_active:
        login_user(user)
        return jsonify({"id": user.id, "role": user.role})
    return jsonify({"error": "Invalid credentials"}), 401

@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "logged out"})
