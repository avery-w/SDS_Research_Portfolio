from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    Product,
    Store,
    Cart,
    CartItem,
    Order,
    OrderItem,
    ReturnRequest,
    Message,
    User,
    PlatformSetting,
)

customer_bp = Blueprint("customer", __name__)


@customer_bp.route("/")
def home():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    products = Product.query.filter_by(is_active=True).join(Store).filter(Store.is_active == True)
    if query:
        products = products.filter(Product.name.ilike(f"%{query}%"))
    if category:
        products = products.filter(Product.category == category)

    products = products.order_by(Product.created_at.desc()).all()
    categories = [
        c[0] for c in db.session.query(Product.category).distinct() if c[0]
    ]
    return render_template("customer/home.html", products=products, categories=categories, q=query, category=category)


@customer_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("customer/product_detail.html", product=product)


def _get_or_create_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()
    return cart


@customer_bp.route("/cart")
@login_required
def cart_view():
    cart = _get_or_create_cart()
    subtotal = sum((item.product.price * item.quantity for item in cart.items), Decimal("0"))
    return render_template("customer/cart.html", cart=cart, subtotal=subtotal)


@customer_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = max(int(request.form.get("quantity", 1)), 1)

    cart = _get_or_create_cart()
    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
        db.session.add(item)
    db.session.commit()
    flash(f"Added {product.name} to cart.", "success")
    return redirect(url_for("customer.product_detail", product_id=product.id))


@customer_bp.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def cart_update(item_id):
    item = CartItem.query.get_or_404(item_id)
    cart = _get_or_create_cart()
    if item.cart_id != cart.id:
        abort(403)
    quantity = int(request.form.get("quantity", 1))
    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = quantity
    db.session.commit()
    return redirect(url_for("customer.cart_view"))


@customer_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def cart_remove(item_id):
    item = CartItem.query.get_or_404(item_id)
    cart = _get_or_create_cart()
    if item.cart_id != cart.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("customer.cart_view"))


@customer_bp.route("/checkout")
@login_required
def checkout():
    cart = _get_or_create_cart()
    if not cart.items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("customer.cart_view"))
    subtotal = sum((item.product.price * item.quantity for item in cart.items), Decimal("0"))
    return render_template("customer/checkout.html", cart=cart, subtotal=subtotal, user=current_user)


@customer_bp.route("/checkout/place-order", methods=["POST"])
@login_required
def place_order():
    cart = _get_or_create_cart()
    if not cart.items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("customer.cart_view"))

    service_code = request.form.get("service_code")
    service_name = request.form.get("service_name")
    shipping_cost = Decimal(request.form.get("shipping_cost", "0"))

    subtotal = sum((item.product.price * item.quantity for item in cart.items), Decimal("0"))
    total = subtotal + shipping_cost

    order = Order(
        customer_id=current_user.id,
        ship_name=request.form["ship_name"],
        ship_address=request.form["ship_address"],
        ship_city=request.form["ship_city"],
        ship_state=request.form["ship_state"],
        ship_zip=request.form["ship_zip"],
        ship_country="US",
        ups_service_code=service_code,
        ups_service_name=service_name,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        total=total,
    )
    db.session.add(order)
    db.session.flush()

    for item in cart.items:
        if item.product.stock_qty < item.quantity:
            db.session.rollback()
            flash(f"Not enough stock for {item.product.name}.", "danger")
            return redirect(url_for("customer.cart_view"))
        item.product.stock_qty -= item.quantity
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product.id,
                store_id=item.product.store_id,
                quantity=item.quantity,
                unit_price=item.product.price,
                status="pending",
            )
        )
        db.session.delete(item)

    db.session.commit()
    flash("Order placed! (Payment simulated for this demo.)", "success")
    return redirect(url_for("customer.order_detail", order_id=order.id))


@customer_bp.route("/orders")
@login_required
def order_history():
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("customer/orders.html", orders=orders)


@customer_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
    return render_template("customer/order_detail.html", order=order)


@customer_bp.route("/orders/item/<int:item_id>/cancel", methods=["POST"])
@login_required
def cancel_item(item_id):
    item = OrderItem.query.get_or_404(item_id)
    if item.order.customer_id != current_user.id:
        abort(403)
    if item.status != "pending":
        flash("Only pending items can be cancelled.", "warning")
        return redirect(url_for("customer.order_detail", order_id=item.order_id))
    item.status = "cancelled"
    item.product.stock_qty += item.quantity
    db.session.commit()
    flash("Item cancelled.", "success")
    return redirect(url_for("customer.order_detail", order_id=item.order_id))


@customer_bp.route("/orders/item/<int:item_id>/return", methods=["POST"])
@login_required
def request_return(item_id):
    item = OrderItem.query.get_or_404(item_id)
    if item.order.customer_id != current_user.id:
        abort(403)
    if item.status != "delivered":
        flash("Only delivered items can be returned.", "warning")
        return redirect(url_for("customer.order_detail", order_id=item.order_id))
    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Please provide a reason for the return.", "danger")
        return redirect(url_for("customer.order_detail", order_id=item.order_id))

    item.status = "return_requested"
    db.session.add(ReturnRequest(order_item_id=item.id, reason=reason))
    db.session.commit()
    flash("Return request submitted.", "success")
    return redirect(url_for("customer.order_detail", order_id=item.order_id))


@customer_bp.route("/messages")
@login_required
def inbox():
    threads = (
        Message.query.filter(
            (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
        )
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template("customer/inbox.html", threads=threads)


@customer_bp.route("/messages/send/<int:recipient_id>", methods=["POST"])
@login_required
def send_message(recipient_id):
    recipient = User.query.get_or_404(recipient_id)
    body = request.form.get("body", "").strip()
    if not body:
        flash("Message cannot be empty.", "danger")
        return redirect(request.referrer or url_for("customer.home"))

    msg = Message(
        sender_id=current_user.id,
        recipient_id=recipient.id,
        product_id=request.form.get("product_id", type=int),
        order_id=request.form.get("order_id", type=int),
        body=body,
    )
    db.session.add(msg)
    db.session.commit()
    flash("Message sent to seller.", "success")
    return redirect(request.referrer or url_for("customer.home"))
