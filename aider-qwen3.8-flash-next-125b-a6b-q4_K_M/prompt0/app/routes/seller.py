import os, uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.product import Product, ProductImage, Category
from app.models.order import Order, OrderItem, OrderStatus
from app.models.store import Store
from app.models.message import Conversation, Message
from app.utils.decorators import seller_required

seller_bp = Blueprint("seller", __name__)

@seller_bp.route("/dashboard")
@login_required
@seller_required
def dashboard():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    products = Product.query.filter_by(store_id=store.id).all() if store else []
    orders = (
        Order.query.join(OrderItem)
        .filter(OrderItem.seller_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("seller/dashboard.html", store=store, products=products, orders=orders)

@seller_bp.route("/store/create", methods=["GET", "POST"])
@login_required
@seller_required
def create_store():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if Store.query.filter_by(owner_id=current_user.id).first():
            flash("You already have a store.", "warning")
            return redirect(url_for("seller.dashboard"))
        store = Store(name=name, description=description, owner_id=current_user.id)
        db.session.add(store)
        db.session.commit()
        flash("Store created!", "success")
        return redirect(url_for("seller.dashboard"))
    return render_template("seller/create_store.html")

@seller_bp.route("/products/new", methods=["GET", "POST"])
@login_required
@seller_required
def create_product():
    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store:
        flash("Create a store first.", "warning")
        return redirect(url_for("seller.create_store"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", type=float)
        stock = request.form.get("stock_quantity", type=int)
        sku = request.form.get("sku", "").strip()
        weight = request.form.get("weight_oz", type=float)
        length = request.form.get("length_in", type=float)
        width = request.form.get("width_in", type=float)
        height = request.form.get("height_in", type=float)
        category_id = request.form.get("category_id", type=int)

        product = Product(
            name=name, description=description, price=price,
            stock_quantity=stock, sku=sku, weight_oz=weight,
            length_in=length, width_in=width, height_in=height,
            category_id=category_id, store_id=store.id,
        )
        db.session.add(product)
        db.session.flush()

        # Handle image uploads
        files = request.files.getlist("images")
        for f in files:
            if f and f.filename:
                filename = secure_filename(f.filename)
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                dest = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
                f.save(dest)
                db.session.add(ProductImage(
                    product_id=product.id,
                    image_url=f"/static/uploads/{unique_name}",
                    is_primary=(len(product.images) == 0),
                ))

        db.session.commit()
        flash("Product created!", "success")
        return redirect(url_for("seller.dashboard"))

    categories = Category.query.all()
    return render_template("seller/create_product.html", categories=categories)

@seller_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@seller_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.store.owner_id != current_user.id:
        abort(403)

    if request.method == "POST":
        product.name = request.form.get("name", product.name)
        product.description = request.form.get("description", product.description)
        product.price = request.form.get("price", type=float) or product.price
        product.stock_quantity = request.form.get("stock_quantity", type=int) or product.stock_quantity
        product.sku = request.form.get("sku", product.sku)
        product.is_active = request.form.get("is_active") == "on"
        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("seller.dashboard"))

    return render_template("seller/edit_product.html", product=product)

@seller_bp.route("/orders/<int:order_id>/fulfill", methods=["POST"])
@login_required
@seller_required
def fulfill_order(order_id):
    order = Order.query.get_or_404(order_id)
    tracking = request.form.get("tracking_number", "").strip()
    order.status = OrderStatus.SHIPPED
    order.tracking_number = tracking
    db.session.commit()
    flash("Order marked as shipped.", "success")
    return redirect(url_for("seller.dashboard"))

@seller_bp.route("/messages")
@login_required
@seller_required
def messages():
    conversations = (
        Conversation.query
        .filter(Conversation.seller_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return render_template("seller/messages.html", conversations=conversations)
