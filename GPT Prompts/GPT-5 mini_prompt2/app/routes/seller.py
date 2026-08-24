import os
from uuid import uuid4

from flask import Blueprint, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.config import Config
from app.extensions import db
from app.models import Order, OrderItem, Product, Store
from app.utils.sanitize import sanitize_filename, sanitize_text

seller_bp = Blueprint("seller", __name__)


@seller_bp.route("/seller")
@login_required
def seller_home():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    products = Product.query.filter_by(seller_id=current_user.id).all() if store else []
    orders = []
    if store:
        orders = Order.query.filter_by(store_id=store.id).order_by(Order.created_at.desc()).all()
    return render_template("seller/dashboard.html", store=store, products=products, orders=orders)


@seller_bp.route("/seller/store", methods=["GET", "POST"])
@login_required
def store_management():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    if request.method == "POST":
        name = sanitize_text(request.form.get("name", ""), max_length=120)
        description = sanitize_text(request.form.get("description", ""), max_length=1000)
        if not store:
            store = Store(name=name, description=description, owner_id=current_user.id)
            db.session.add(store)
        else:
            store.name = name
            store.description = description
        db.session.commit()
        flash("Store updated successfully.", "success")
        return redirect(url_for("seller.store_management"))
    return render_template("seller/store.html", store=store)


@seller_bp.route("/seller/products", methods=["GET", "POST"])
@login_required
def product_management():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    if request.method == "POST" and store:
        name = sanitize_text(request.form.get("name", ""), max_length=150)
        description = sanitize_text(request.form.get("description", ""), max_length=1000)
        category = sanitize_text(request.form.get("category", ""), max_length=80)
        price = float(request.form.get("price", 0) or 0)
        stock = int(request.form.get("stock", 0) or 0)

        image_file = request.files.get("image")
        image_url = None
        if image_file and image_file.filename:
            filename = secure_filename(sanitize_filename(image_file.filename))
            if filename:
                os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                saved_name = f"{uuid4().hex}_{filename}"
                path = os.path.join(Config.UPLOAD_FOLDER, saved_name)
                image_file.save(path)
                image_url = f"/uploads/{saved_name}"

        prod = Product(
            name=name,
            description=description,
            category=category,
            price=price,
            stock=stock,
            image_url=image_url,
            seller_id=current_user.id,
            store_id=store.id,
        )
        db.session.add(prod)
        db.session.commit()
        flash("Product created successfully.", "success")
        return redirect(url_for("seller.product_management"))

    products = Product.query.filter_by(seller_id=current_user.id).all()
    return render_template("seller/products.html", products=products, store=store)


@seller_bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)


@seller_bp.route("/seller/orders")
@login_required
def seller_orders():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    orders = []
    if store:
        orders = Order.query.filter_by(store_id=store.id).order_by(Order.created_at.desc()).all()
    return render_template("seller/orders.html", orders=orders)


@seller_bp.route("/seller/order/<int:order_id>/fulfill", methods=["POST"])
@login_required
def fulfill_order(order_id):
    order = Order.query.get_or_404(order_id)
    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store or order.store_id != store.id:
        flash("You cannot fulfill another seller's order.", "danger")
        return redirect(url_for("seller.seller_orders"))

    order.status = "fulfilled"
    db.session.commit()
    flash("Order marked as fulfilled.", "success")
    return redirect(url_for("seller.seller_orders"))
