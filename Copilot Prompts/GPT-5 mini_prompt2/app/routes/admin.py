from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Product, Store, User, Order
from app.utils.sanitize import sanitize_search, sanitize_text

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    from functools import wraps

    @wraps(f)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("customer.home"))
        return f(*args, **kwargs)

    return wrapped


@admin_bp.route("/admin")
@admin_required
def dashboard():
    search = sanitize_search(request.args.get("q", ""), max_length=100)
    users = User.query
    stores = Store.query
    products = Product.query
    orders = Order.query

    if search:
        users = users.filter(User.name.ilike(f"%{search}%"))
        stores = stores.filter(Store.name.ilike(f"%{search}%"))
        products = products.filter(Product.name.ilike(f"%{search}%"))

    return render_template(
        "admin/dashboard.html",
        users=users.all(),
        stores=stores.all(),
        products=products.all(),
        orders=orders.order_by(Order.created_at.desc()).all(),
        search=search,
    )


@admin_bp.route("/admin/user/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash("User account status updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/store/<int:store_id>/toggle")
@admin_required
def toggle_store(store_id):
    store = Store.query.get_or_404(store_id)
    store.is_active = not store.is_active
    db.session.commit()
    flash("Store state updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/product/<int:product_id>/toggle")
@admin_required
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    flash("Product state updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        platform_name = sanitize_text(request.form.get("platform_name", "Marketplace"), max_length=120)
        support_email = sanitize_text(request.form.get("support_email", "support@market.local"), max_length=120)
        flash(f"Platform settings saved for {platform_name}.", "success")
    return render_template("admin/settings.html")
