from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.decorators import role_required
from app.models import (
    User,
    Store,
    Product,
    Order,
    OrderItem,
    ReturnRequest,
    PlatformSetting,
    ROLE_ADMIN,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
@login_required
@role_required(ROLE_ADMIN)
def require_admin():
    pass


@admin_bp.route("/")
def dashboard():
    total_users = User.query.count()
    total_sellers = Store.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()

    all_items = OrderItem.query.all()
    total_revenue = sum(
        (i.unit_price * i.quantity for i in all_items if i.status != "cancelled"), Decimal("0")
    )

    top_products = (
        db.session.query(Product.name, db.func.sum(OrderItem.quantity).label("qty"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id)
        .order_by(db.desc("qty"))
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_sellers=total_sellers,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        top_products=top_products,
    )


@admin_bp.route("/users")
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("admin.users"))
    user.is_active_user = not user.is_active_user
    db.session.commit()
    flash(f"User {user.email} {'activated' if user.is_active_user else 'deactivated'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/stores")
def stores():
    stores = Store.query.order_by(Store.created_at.desc()).all()
    return render_template("admin/stores.html", stores=stores)


@admin_bp.route("/stores/<int:store_id>/toggle-active", methods=["POST"])
def toggle_store_active(store_id):
    store = Store.query.get_or_404(store_id)
    store.is_active = not store.is_active
    db.session.commit()
    flash(f"Store {store.name} {'activated' if store.is_active else 'deactivated'}.", "success")
    return redirect(url_for("admin.stores"))


@admin_bp.route("/products")
def products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=products)


@admin_bp.route("/products/<int:product_id>/toggle-active", methods=["POST"])
def toggle_product_active(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    flash(f"Product {product.name} {'activated' if product.is_active else 'deactivated'}.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.route("/orders")
def orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=orders)


@admin_bp.route("/orders/item/<int:item_id>/override-status", methods=["POST"])
def override_item_status(item_id):
    item = OrderItem.query.get_or_404(item_id)
    new_status = request.form.get("status")
    from app.models import ORDER_ITEM_STATUSES

    if new_status in ORDER_ITEM_STATUSES:
        item.status = new_status
        db.session.commit()
        flash("Order item status overridden.", "success")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/returns")
def returns():
    returns = ReturnRequest.query.order_by(ReturnRequest.created_at.desc()).all()
    return render_template("admin/returns.html", returns=returns)


@admin_bp.route("/returns/<int:return_id>/<string:decision>", methods=["POST"])
def decide_return(return_id, decision):
    ret = ReturnRequest.query.get_or_404(return_id)
    if decision not in ("approved", "rejected", "refunded"):
        abort(400)
    ret.status = decision
    if decision in ("approved", "refunded"):
        ret.order_item.status = "returned"
        ret.order_item.product.stock_qty += ret.order_item.quantity
    else:
        ret.order_item.status = "delivered"
    db.session.commit()
    flash(f"Return request {decision}.", "success")
    return redirect(url_for("admin.returns"))


@admin_bp.route("/settings", methods=["GET", "POST"])
def settings():
    setting = PlatformSetting.get()
    if request.method == "POST":
        setting.site_name = request.form["site_name"].strip()
        setting.commission_rate_pct = float(request.form.get("commission_rate_pct", 10))
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", setting=setting)
