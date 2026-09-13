import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.decorators import role_required
from app.models import Store, Product, ProductImage, OrderItem, Message, User, ROLE_SELLER

seller_bp = Blueprint("seller", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _my_store():
    store = Store.query.filter_by(seller_id=current_user.id).first()
    if not store:
        abort(404)
    return store


@seller_bp.before_request
@login_required
@role_required(ROLE_SELLER)
def require_seller():
    pass


@seller_bp.route("/dashboard")
def dashboard():
    store = _my_store()
    items = (
        OrderItem.query.filter_by(store_id=store.id).order_by(OrderItem.id.desc()).limit(10).all()
    )
    total_sales = sum(
        (i.unit_price * i.quantity for i in OrderItem.query.filter_by(store_id=store.id).all()
         if i.status not in ("cancelled",)),
    )
    return render_template("seller/dashboard.html", store=store, items=items, total_sales=total_sales)


@seller_bp.route("/store", methods=["GET", "POST"])
def store_profile():
    store = _my_store()
    if request.method == "POST":
        store.name = request.form["name"].strip()
        store.description = request.form.get("description", "").strip()
        db.session.commit()
        flash("Store updated.", "success")
        return redirect(url_for("seller.store_profile"))
    return render_template("seller/store.html", store=store)


@seller_bp.route("/products")
def products():
    store = _my_store()
    products = Product.query.filter_by(store_id=store.id).order_by(Product.created_at.desc()).all()
    return render_template("seller/products.html", products=products)


@seller_bp.route("/products/new", methods=["GET", "POST"])
def product_new():
    store = _my_store()
    if request.method == "POST":
        product = Product(
            store_id=store.id,
            name=request.form["name"].strip(),
            description=request.form.get("description", "").strip(),
            price=request.form["price"],
            weight_oz=float(request.form.get("weight_oz", 16)),
            category=request.form.get("category", "").strip(),
            sku=request.form.get("sku", "").strip(),
            stock_qty=int(request.form.get("stock_qty", 0)),
        )
        db.session.add(product)
        db.session.flush()
        _save_uploaded_images(product)
        db.session.commit()
        flash("Product created.", "success")
        return redirect(url_for("seller.products"))
    return render_template("seller/product_form.html", product=None)


@seller_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def product_edit(product_id):
    store = _my_store()
    product = Product.query.get_or_404(product_id)
    if product.store_id != store.id:
        abort(403)

    if request.method == "POST":
        product.name = request.form["name"].strip()
        product.description = request.form.get("description", "").strip()
        product.price = request.form["price"]
        product.weight_oz = float(request.form.get("weight_oz", 16))
        product.category = request.form.get("category", "").strip()
        product.sku = request.form.get("sku", "").strip()
        product.stock_qty = int(request.form.get("stock_qty", 0))
        product.is_active = bool(request.form.get("is_active"))
        _save_uploaded_images(product)
        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("seller.products"))

    return render_template("seller/product_form.html", product=product)


@seller_bp.route("/products/<int:product_id>/delete", methods=["POST"])
def product_delete(product_id):
    store = _my_store()
    product = Product.query.get_or_404(product_id)
    if product.store_id != store.id:
        abort(403)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("seller.products"))


def _save_uploaded_images(product):
    files = request.files.getlist("images")
    for file in files:
        if not file or not file.filename:
            continue
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue
        filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        is_primary = len(product.images) == 0
        db.session.add(ProductImage(product_id=product.id, filename=filename, is_primary=is_primary))


@seller_bp.route("/orders")
def orders():
    store = _my_store()
    items = OrderItem.query.filter_by(store_id=store.id).order_by(OrderItem.id.desc()).all()
    return render_template("seller/orders.html", items=items)


@seller_bp.route("/orders/item/<int:item_id>/status", methods=["POST"])
def update_item_status(item_id):
    store = _my_store()
    item = OrderItem.query.get_or_404(item_id)
    if item.store_id != store.id:
        abort(403)
    new_status = request.form.get("status")
    if new_status in ("shipped", "delivered"):
        item.status = new_status
        db.session.commit()
        flash("Order item updated.", "success")
    return redirect(url_for("seller.orders"))


@seller_bp.route("/messages")
def inbox():
    threads = (
        Message.query.filter(
            (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
        )
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template("seller/inbox.html", threads=threads)
