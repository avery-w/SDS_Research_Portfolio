from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Order, Product, Store, User
from app.utils.sanitize import sanitize_search

admin_bp = Blueprint("admin", __name__)


def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("customer.home"))
        return func(*args, **kwargs)

    return wrapper


@admin_bp.route("/admin")
@admin_required
def dashboard():
    query = sanitize_search(request.args.get("q", ""), max_length=100)
    users = User.query.filter(User.name.ilike(f"%{query}%")) if query else User.query.all()
    stores = Store.query.filter(Store.name.ilike(f"%{query}%")) if query else Store.query.all()
    products = Product.query.filter(Product.name.ilike(f"%{query}%")) if query else Product.query.all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/dashboard.html", users=users, stores=stores, products=products, orders=orders, query=query)


@admin_bp.route("/admin/user/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash("User status updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/store/<int:store_id>/toggle")
@admin_required
def toggle_store(store_id):
    store = Store.query.get_or_404(store_id)
    store.is_active = not store.is_active
    db.session.commit()
    flash("Store status updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/product/<int:product_id>/toggle")
@admin_required
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    flash("Product status updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        platform_name = request.form.get("platform_name", "Marketplace")
        support_email = request.form.get("support_email", "support@market.local")
        flash(f"Platform settings saved for {platform_name}.", "success")
    return render_template("admin/settings.html")
