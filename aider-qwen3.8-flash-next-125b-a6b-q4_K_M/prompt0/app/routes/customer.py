import os, uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.product import Product, ProductImage, Category
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem, OrderStatus, ReturnRequest
from app.models.store import Store
from app.services.shipping import ShippingService

customer_bp = Blueprint("customer", __name__)

@customer_bp.route("/")
@login_required
def home():
    categories = Category.query.all()
    products = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).limit(20).all()
    return render_template("customer/home.html", categories=categories, products=products)

@customer_bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    query = Product.query.filter_by(is_active=True)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    products = query.all()
    return render_template("customer/search_results.html", products=products, q=q)

@customer_bp.route("/product/<int:product_id>")
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("customer/product_detail.html", product=product)

@customer_bp.route("/cart")
@login_required
def view_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    return render_template("customer/cart.html", cart=cart)

@customer_bp.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    product_id = request.form.get("product_id", type=int)
    qty = request.form.get("quantity", 1, type=int)
    product = Product.query.get_or_404(product_id)

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.flush()

    existing = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if existing:
        existing.quantity += qty
    else:
        db.session.add(CartItem(cart_id=cart.id, product_id=product_id, quantity=qty))

    db.session.commit()
    flash("Added to cart.", "success")
    return redirect(url_for("customer.view_cart"))

@customer_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user_id != current_user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("customer.view_cart"))

@customer_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("customer.home"))

    if request.method == "POST":
        street = request.form.get("street", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        zip_code = request.form.get("zip", "").strip()
        shipping_method = request.form.get("shipping_method", "standard")

        subtotal = sum(float(item.product.price) * item.quantity for item in cart.items)

        # Calculate shipping via UPS
        total_weight = sum(item.product.weight_oz * item.quantity for item in cart.items)
        max_dim = max(
            (item.product.length_in, item.product.width_in, item.product.height_in)
            for item in cart.items
        )
        rates = ShippingService.get_shipping_rates(
            street, city, state, zip_code,
            total_weight, max_dim[0], max_dim[1], max_dim[2]
        )
        selected_rate = next((r for r in rates if r["service_code"] == shipping_method), rates[0] if rates else {"cost": 0})
        shipping_cost = selected_rate["cost"]
        total = subtotal + shipping_cost

        order = Order(
            order_number=f"ORD-{uuid.uuid4().hex[:12].upper()}",
            customer_id=current_user.id,
            status=OrderStatus.CONFIRMED,
            shipping_address_street=street,
            shipping_address_city=city,
            shipping_address_state=state,
            shipping_address_zip=zip_code,
            shipping_method=shipping_method,
            shipping_cost=shipping_cost,
            subtotal=subtotal,
            total=total,
        )
        db.session.add(order)
        db.session.flush()

        for item in cart.items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.product.price,
                seller_id=item.product.store.owner_id,
            ))
            item.product.stock_quantity -= item.quantity

        db.session.delete(cart)
        db.session.commit()
        flash("Order placed successfully!", "success")
        return redirect(url_for("customer.order_history"))

    # GET: show checkout form with shipping rates
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    total_weight = sum(item.product.weight_oz * item.quantity for item in cart.items)
    max_dim = max(
        (item.product.length_in, item.product.width_in, item.product.height_in)
        for item in cart.items
    )
    rates = ShippingService.get_shipping_rates(
        current_user.address_street or "", current_user.address_city or "",
        current_user.address_state or "", current_user.address_zip or "",
        total_weight, max_dim[0], max_dim[1], max_dim[2]
    )
    return render_template("customer/checkout.html", cart=cart, rates=rates)

@customer_bp.route("/orders")
@login_required
def order_history():
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("customer/order_history.html", orders=orders)

@customer_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
    if order.status in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
        order.status = OrderStatus.CANCELLED
        db.session.commit()
        flash("Order cancelled.", "info")
    else:
        flash("This order can no longer be cancelled.", "warning")
    return redirect(url_for("customer.order_history"))

@customer_bp.route("/orders/<int:order_id>/return", methods=["POST"])
@login_required
def request_return(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Please provide a reason.", "danger")
        return redirect(url_for("customer.order_history"))
    rr = ReturnRequest(order_id=order.id, customer_id=current_user.id, reason=reason)
    db.session.add(rr)
    db.session.commit()
    flash("Return request submitted.", "success")
    return redirect(url_for("customer.order_history"))
