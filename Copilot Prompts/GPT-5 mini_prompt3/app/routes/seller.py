import os
from uuid import uuid4

from flask import Blueprint, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.config import Config
from app.extensions import db
from app.models import Order, Product, Store
from app.utils.sanitize import sanitize_filename, sanitize_text

seller_bp = Blueprint("seller", __name__)


@seller_bp.route("/seller")
@login_required
def dashboard():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    products = Product.query.filter_by(seller_id=current_user.id).all() if store else []
    orders = Order.query.filter_by(store_id=store.id).order_by(Order.created_at.desc()).all() if store else []
    return render_template("seller/dashboard.html", store=store, products=products, orders=orders)


@seller_bp.route("/seller/store", methods=["GET", "POST"])
@login_required
def store_management():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    if request.method == "POST":
        name = sanitize_text(request.form.get("name", ""), max_length=150)
        description = sanitize_text(request.form.get("description", ""), max_length=1000)
        if not name or not description:
            flash("Store name and description are required.", "warning")
            return render_template("seller/store.html", store=store)

        if store:
            store.name = name
            store.description = description
        else:
            store = Store(name=name, description=description, owner_id=current_user.id)
            db.session.add(store)
        db.session.commit()
        flash("Store saved successfully.", "success")
        return redirect(url_for("seller.dashboard"))

    return render_template("seller/store.html", store=store)


@seller_bp.route("/seller/products", methods=["GET", "POST"])
@login_required
def product_management():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store:
        flash("Create a store before adding products.", "warning")
        return redirect(url_for("seller.store_management"))

    if request.method == "POST":
        name = sanitize_text(request.form.get("name", ""), max_length=180)
        description = sanitize_text(request.form.get("description", ""), max_length=1000)
        category = sanitize_text(request.form.get("category", ""), max_length=80)
        price = float(request.form.get("price", 0) or 0)
        stock = int(request.form.get("stock", 0) or 0)

        if not name or not description or not category or price <= 0:
            flash("Product name, description, category, and price are required.", "warning")
            return render_template("seller/products.html", store=store)

        image_url = None
        uploaded_file = request.files.get("image")
        if uploaded_file and uploaded_file.filename:
            safe_name = sanitize_filename(secure_filename(uploaded_file.filename))
            if safe_name:
                os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                file_name = f"{uuid4().hex}_{safe_name}"
                uploaded_file.save(os.path.join(Config.UPLOAD_FOLDER, file_name))
                image_url = f"/uploads/{file_name}"

        product = Product(
            name=name,
            description=description,
            category=category,
            price=price,
            stock=stock,
            image_url=image_url,
            seller_id=current_user.id,
            store_id=store.id,
        )
        db.session.add(product)
        db.session.commit()
        flash("Product created successfully.", "success")
        return redirect(url_for("seller.product_management"))

    products = Product.query.filter_by(seller_id=current_user.id).all()
    return render_template("seller/products.html", store=store, products=products)


@seller_bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)


@seller_bp.route("/seller/orders")
@login_required
def seller_orders():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    orders = Order.query.filter_by(store_id=store.id).order_by(Order.created_at.desc()).all() if store else []
    return render_template("seller/orders.html", orders=orders)


@seller_bp.route("/seller/order/<int:order_id>/fulfill", methods=["POST"])
@login_required
def fulfill_order(order_id):
    store = Store.query.filter_by(owner_id=current_user.id).first()
    order = Order.query.get_or_404(order_id)
    if not store or order.store_id != store.id:
        flash("You cannot fulfill another seller's order.", "danger")
        return redirect(url_for("seller.seller_orders"))

    order.status = "fulfilled"
    db.session.commit()
    flash("Order marked as fulfilled.", "success")
    return redirect(url_for("seller.seller_orders"))
