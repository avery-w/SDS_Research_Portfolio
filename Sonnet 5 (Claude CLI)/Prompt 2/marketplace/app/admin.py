from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app import db
from app.decorators import role_required
from app.models import Order, PlatformSetting, Product, Store, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    total_users = User.query.count()
    total_sellers = Store.query.count()
    total_orders = Order.query.count()
    revenue_cents = db.session.query(db.func.coalesce(db.func.sum(Order.total_cents), 0)).filter(
        Order.status.in_(("paid", "shipped", "delivered"))
    ).scalar()
    orders_by_status = dict(
        db.session.query(Order.status, db.func.count(Order.id)).group_by(Order.status).all()
    )
    top_products = (
        db.session.query(Product.name, db.func.count(Product.id))
        .join(Store)
        .group_by(Product.name)
        .order_by(db.func.count(Product.id).desc())
        .limit(5)
        .all()
    )
    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_sellers=total_sellers,
        total_orders=total_orders,
        revenue=revenue_cents / 100,
        orders_by_status=orders_by_status,
        top_products=top_products,
    )


@admin_bp.route("/users")
@login_required
@role_required("admin")
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@role_required("admin")
def toggle_user_active(user_id):
    user = db.session.get(User, user_id) or abort(404)
    user.is_active_account = not user.is_active_account
    db.session.commit()
    flash(f"{user.email} is now {'active' if user.is_active_account else 'deactivated'}.")
    return redirect(url_for("admin.users"))


@admin_bp.route("/stores")
@login_required
@role_required("admin")
def stores():
    all_stores = Store.query.all()
    return render_template("admin_stores.html", stores=all_stores)


@admin_bp.route("/stores/<int:store_id>/toggle-active", methods=["POST"])
@login_required
@role_required("admin")
def toggle_store_active(store_id):
    store = db.session.get(Store, store_id) or abort(404)
    store.is_active = not store.is_active
    db.session.commit()
    flash(f"{store.name} is now {'active' if store.is_active else 'suspended'}.")
    return redirect(url_for("admin.stores"))


@admin_bp.route("/orders")
@login_required
@role_required("admin")
def orders():
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin_orders.html", orders=all_orders)


@admin_bp.route("/orders/<int:order_id>/override-status", methods=["POST"])
@login_required
@role_required("admin")
def override_order_status(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    status = request.form.get("status")
    from app.models import ORDER_STATUSES
    if status not in ORDER_STATUSES:
        abort(400)
    order.status = status
    db.session.commit()
    flash(f"Order #{order.id} status overridden to {status}.")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required("admin")
def settings():
    if request.method == "POST":
        key = request.form.get("key", "").strip()
        value = request.form.get("value", "").strip()
        if key:
            setting = db.session.get(PlatformSetting, key)
            if setting:
                setting.value = value
            else:
                db.session.add(PlatformSetting(key=key, value=value))
            db.session.commit()
        return redirect(url_for("admin.settings"))
    all_settings = PlatformSetting.query.all()
    return render_template("admin_settings.html", settings=all_settings)
