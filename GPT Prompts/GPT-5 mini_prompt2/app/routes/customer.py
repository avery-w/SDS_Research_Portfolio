from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import CartItem, Order, OrderItem, Product, ReturnRequest, User
from app.utils.sanitize import sanitize_search, sanitize_text

customer_bp = Blueprint("customer", __name__)


@customer_bp.route("/")
def home():
    query = sanitize_search(request.args.get("q", ""), max_length=100)
    products = Product.query.filter(Product.is_active.is_(True))
    if query:
        products = products.filter(Product.name.ilike(f"%{query}%"))
    products = products.all()
    return render_template("customer/home.html", products=products, query=query)


@customer_bp.route("/dashboard")
@login_required
def dashboard():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    return render_template("customer/dashboard.html", orders=orders)


@customer_bp.route("/cart")
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.quantity * item.product.price for item in items)
    return render_template("customer/cart.html", items=items, total=total)


@customer_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        item.quantity += 1
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=product_id, quantity=1))
    db.session.commit()
    flash("Product added to cart.", "success")
    return redirect(url_for("customer.home"))


@customer_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("customer.cart"))

    if request.method == "POST":
        shipping_address = sanitize_text(request.form.get("shipping_address", ""), max_length=500)
        if not shipping_address:
            flash("Shipping address is required.", "danger")
            return render_template("customer/checkout.html", items=items)

        total = sum(item.quantity * item.product.price for item in items)
        order = Order(
            user_id=current_user.id,
            store_id=items[0].product.store_id,
            total_amount=total,
            status="pending",
            shipping_address=shipping_address,
        )
        db.session.add(order)
        db.session.commit()

        for item in items:
            db.session.add(OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity, unit_price=item.product.price))
            item.product.stock -= item.quantity

        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash("Order placed successfully.", "success")
        return redirect(url_for("customer.order_history"))

    return render_template("customer/checkout.html", items=items)


@customer_bp.route("/orders")
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("customer/orders.html", orders=orders)


@customer_bp.route("/return/<int:order_id>", methods=["POST"])
@login_required
def return_request(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("You cannot request a return for another user's order.", "danger")
        return redirect(url_for("customer.order_history"))

    reason = sanitize_text(request.form.get("reason", ""), max_length=500)
    if not reason:
        flash("Please provide a reason for the return.", "warning")
        return redirect(url_for("customer.order_history"))

    existing = ReturnRequest.query.filter_by(order_id=order_id, user_id=current_user.id).first()
    if existing:
        flash("A return request already exists for this order.", "warning")
        return redirect(url_for("customer.order_history"))

    db.session.add(ReturnRequest(order_id=order_id, user_id=current_user.id, reason=reason))
    db.session.commit()
    flash("Return request submitted.", "success")
    return redirect(url_for("customer.order_history"))


@customer_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        current_user.name = sanitize_text(request.form.get("name", current_user.name), max_length=120)
        current_user.email = sanitize_text(request.form.get("email", current_user.email), max_length=120).lower()
        db.session.commit()
        flash("Account updated.", "success")
    return render_template("customer/account.html", user=current_user)
