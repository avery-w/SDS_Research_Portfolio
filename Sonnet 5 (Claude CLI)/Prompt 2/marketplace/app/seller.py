import os
import uuid

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.decorators import role_required
from app.models import Message, OrderItem, Product, ProductImage, Store

seller_bp = Blueprint("seller", __name__, url_prefix="/seller")


def _my_store():
    store = Store.query.filter_by(seller_id=current_user.id).first()
    if store is None:
        abort(404)
    return store


def _owned_product(product_id, store):
    return Product.query.filter_by(id=product_id, store_id=store.id).first() or abort(404)


@seller_bp.route("/setup", methods=["GET", "POST"])
@login_required
@role_required("seller")
def setup_store():
    existing = Store.query.filter_by(seller_id=current_user.id).first()
    if existing:
        return redirect(url_for("seller.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Store name is required.")
            return render_template("seller_setup.html")
        db.session.add(Store(seller_id=current_user.id, name=name, description=request.form.get("description", "")))
        db.session.commit()
        return redirect(url_for("seller.dashboard"))
    return render_template("seller_setup.html")


@seller_bp.route("/dashboard")
@login_required
@role_required("seller")
def dashboard():
    store = _my_store()
    products = Product.query.filter_by(store_id=store.id).all()
    order_items = OrderItem.query.filter_by(store_id=store.id).order_by(OrderItem.id.desc()).all()
    messages = Message.query.filter_by(recipient_id=current_user.id).order_by(Message.created_at.desc()).limit(20).all()
    return render_template("seller_dashboard.html", store=store, products=products, order_items=order_items, messages=messages)


def _allowed_image(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


@seller_bp.route("/products/new", methods=["GET", "POST"])
@login_required
@role_required("seller")
def product_new():
    store = _my_store()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", type=float)
        stock = request.form.get("stock_qty", type=int) or 0
        weight_oz = request.form.get("weight_oz", type=float) or 8.0
        if not name or price is None or price < 0:
            flash("Valid name and price are required.")
            return render_template("product_form.html", product=None)

        product = Product(
            store_id=store.id,
            name=name,
            description=request.form.get("description", ""),
            price_cents=round(price * 100),
            stock_qty=max(0, stock),
            weight_oz=max(0.1, weight_oz),
        )
        db.session.add(product)
        db.session.flush()
        _save_uploaded_images(product)
        db.session.commit()
        flash("Product created.")
        return redirect(url_for("seller.dashboard"))
    return render_template("product_form.html", product=None)


def _save_uploaded_images(product):
    files = request.files.getlist("images")
    for f in files:
        if not f or not f.filename:
            continue
        if not _allowed_image(f.filename):
            continue  # silently skip disallowed types; UI only offers image inputs
        safe_name = secure_filename(f.filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        dest = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
        f.save(dest)
        db.session.add(ProductImage(product_id=product.id, filename=unique_name))


@seller_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("seller")
def product_edit(product_id):
    store = _my_store()
    product = _owned_product(product_id, store)
    if request.method == "POST":
        product.name = request.form.get("name", product.name).strip()
        product.description = request.form.get("description", product.description)
        price = request.form.get("price", type=float)
        if price is not None and price >= 0:
            product.price_cents = round(price * 100)
        stock = request.form.get("stock_qty", type=int)
        if stock is not None:
            product.stock_qty = max(0, stock)
        product.is_active = bool(request.form.get("is_active"))
        _save_uploaded_images(product)
        db.session.commit()
        flash("Product updated.")
        return redirect(url_for("seller.dashboard"))
    return render_template("product_form.html", product=product)


@seller_bp.route("/orders/<int:item_id>/fulfill", methods=["POST"])
@login_required
@role_required("seller")
def fulfill_item(item_id):
    store = _my_store()
    item = OrderItem.query.filter_by(id=item_id, store_id=store.id).first_or_404()
    new_status = request.form.get("status")
    if new_status not in ("fulfilled", "returned"):
        abort(400)
    item.item_status = new_status
    db.session.commit()
    flash("Order item updated.")
    return redirect(url_for("seller.dashboard"))
