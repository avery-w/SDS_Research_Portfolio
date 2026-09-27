from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.order import Order, ReturnRequest
from app.models.product import Product
from app.models.store import Store
from app.services.analytics import generate_sales_report
from app.utils.sanitizers import sanitize_string
from functools import wraps

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return wrapper

@bp.route("/users", methods=["GET"])
@login_required
@admin_required
def list_users():
    page = int(request.args.get("page", 1))
    users = User.query.paginate(page=page, per_page=50)
    return jsonify({"users": [{"id": u.id, "email": u.email, "role": u.role, "active": u.is_active} for u in users.items], "total": users.total})

@bp.route("/users/<int:user_id>/deactivate", methods=["PATCH"])
@login_required
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return jsonify({"status": "deactivated"})

@bp.route("/orders/<int:order_id>/override", methods=["PATCH"])
@login_required
@admin_required
def override_order(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json(silent=True) or {}
    order.status = sanitize_string(data.get("status", order.status))
    db.session.commit()
    return jsonify({"status": order.status})

@bp.route("/analytics/sales", methods=["GET"])
@login_required
@admin_required
def sales_analytics():
    start = request.args.get("start")
    end = request.args.get("end")
    report = generate_sales_report(start, end)
    return jsonify(report)
