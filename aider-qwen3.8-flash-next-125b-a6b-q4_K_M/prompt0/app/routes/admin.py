from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole
from app.models.store import Store
from app.models.product import Product, Category
from app.models.order import Order, OrderStatus, ReturnRequest
from app.services.analytics import AnalyticsService
from app.utils.decorators import admin_required

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    overview = AnalyticsService.platform_overview()
    sales = AnalyticsService.sales_by_period(30)
    top_products = AnalyticsService.top_selling_products(10)
    status_breakdown = AnalyticsService.order_status_breakdown()
    return render_template(
        "admin/dashboard.html",
        overview=overview, sales=sales,
        top_products=top_products, status_breakdown=status_breakdown,
    )

@admin_bp.route("/users")
@login_required
@admin_required
def manage_users():
    page = request.args.get("page", 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=25)
    return render_template("admin/manage_users.html", users=users)

@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@login_required
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_account = False
    db.session.commit()
    flash(f"Account for {user.username} deactivated.", "info")
    return redirect(url_for("admin.manage_users"))

@admin_bp.route("/users/<int:user_id>/reactivate", methods=["POST"])
@login_required
@admin_required
def reactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_account = True
    db.session.commit()
    flash(f"Account for {user.username} reactivated.", "info")
    return redirect(url_for("admin.manage_users"))

@admin_bp.route("/stores")
@login_required
@admin_required
def manage_stores():
    stores = Store.query.order_by(Store.created_at.desc()).all()
    return render_template("admin/manage_stores.html", stores=stores)

@admin_bp.route("/stores/<int:store_id>/deactivate", methods=["POST"])
@login_required
@admin_required
def deactivate_store(store_id):
    store = Store.query.get_or_404(store_id)
    store.is_active = False
    db.session.commit()
    flash("Store deactivated.", "info")
    return redirect(url_for("admin.manage_stores"))

@admin_bp.route("/products")
@login_required
@admin_required
def manage_products():
    page = request.args.get("page", 1, type=int)
    products = Product.query.order_by(Product.created_at.desc()).paginate(page=page, per_page=25)
    return render_template("admin/manage_products.html", products=products)

@admin_bp.route("/products/<int:product_id>/deactivate", methods=["POST"])
@login_required
@admin_required
def deactivate_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = False
    db.session.commit()
    flash("Product deactivated.", "info")
    return redirect(url_for("admin.manage_products"))

@admin_bp.route("/orders")
@login_required
@admin_required
def manage_orders():
    page = request.args.get("page", 1, type=int)
    orders = Order.query.order_by(Order.created_at.desc()).paginate(page=page, per_page=25)
    return render_template("admin/manage_orders.html", orders=orders)

@admin_bp.route("/orders/<int:order_id>/override", methods=["POST"])
@login_required
@admin_required
def override_order(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status", "").strip()
    if new_status in (OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.SHIPPED,
                     OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.RETURNED):
        order.status = new_status
        db.session.commit()
        flash(f"Order status overridden to {new_status}.", "info")
    return redirect(url_for("admin.manage_orders"))

@admin_bp.route("/returns")
@login_required
@admin_required
def manage_returns():
    returns = ReturnRequest.query.order_by(ReturnRequest.created_at.desc()).all()
    return render_template("admin/manage_returns.html", returns=returns)

@admin_bp.route("/returns/<int:return_id>/resolve", methods=["POST"])
@login_required
@admin_required
def resolve_return(return_id):
    rr = ReturnRequest.query.get_or_404(return_id)
    rr.status = request.form.get("status", "approved")
    rr.admin_note = request.form.get("note", "")
    rr.resolved_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    db.session.commit()
    flash("Return request resolved.", "info")
    return redirect(url_for("admin.manage_returns"))

@admin_bp.route("/categories", methods=["GET", "POST"])
@login_required
@admin_required
def manage_categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        parent_id = request.form.get("parent_id", type=int)
        if name:
            db.session.add(Category(name=name, parent_id=parent_id))
            db.session.commit()
            flash("Category added.", "success")
    categories = Category.query.all()
    return render_template("admin/manage_categories.html", categories=categories)
