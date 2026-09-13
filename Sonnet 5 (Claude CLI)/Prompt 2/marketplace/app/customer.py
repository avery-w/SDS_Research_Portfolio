from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import CartItem, Message, Order, OrderItem, Product, Store
from app.shipping import calculate_shipping

customer_bp = Blueprint("customer", __name__)


@customer_bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    query = Product.query.filter_by(is_active=True)
    if q:
        # SQLAlchemy ORM: `like` value is bound as a parameter, not string-formatted into SQL.
        query = query.filter(Product.name.ilike(f"%{q}%"))
    products = query.order_by(Product.created_at.desc()).all()
    return render_template("index.html", products=products, q=q)


@customer_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    return render_template("product_detail.html", product=product)


@customer_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def cart_add(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    qty = max(1, request.form.get("quantity", 1, type=int))
    item = CartItem.query.filter_by(customer_id=current_user.id, product_id=product.id).first()
    if item:
        item.quantity += qty
    else:
        item = CartItem(customer_id=current_user.id, product_id=product.id, quantity=qty)
        db.session.add(item)
    db.session.commit()
    flash(f"Added {product.name} to cart.")
    return redirect(url_for("customer.cart"))


@customer_bp.route("/cart")
@login_required
def cart():
    items = CartItem.query.filter_by(customer_id=current_user.id).all()
    subtotal = sum(i.product.price * i.quantity for i in items)
    return render_template("cart.html", items=items, subtotal=subtotal)


@customer_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def cart_remove(item_id):
    item = CartItem.query.filter_by(id=item_id, customer_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("customer.cart"))


@customer_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items = CartItem.query.filter_by(customer_id=current_user.id).all()
    if not items:
        flash("Your cart is empty.")
        return redirect(url_for("customer.cart"))

    if request.method == "POST":
        ship_zip = request.form.get("zip", "").strip()
        service = request.form.get("service", "ground")
        weight_lbs = sum((i.product.weight_oz / 16.0) * i.quantity for i in items)

        try:
            shipping_cost, _zone = calculate_shipping(weight_lbs, ship_zip, service)
        except ValueError as exc:
            flash(str(exc))
            return render_template("checkout.html", items=items)

        subtotal_cents = sum(i.product.price_cents * i.quantity for i in items)
        order = Order(
            customer_id=current_user.id,
            status="paid",
            ship_name=request.form.get("name", "").strip(),
            ship_line1=request.form.get("line1", "").strip(),
            ship_city=request.form.get("city", "").strip(),
            ship_state=request.form.get("state", "").strip()[:2].upper(),
            ship_zip=ship_zip,
            shipping_service=service,
            shipping_cost_cents=round(shipping_cost * 100),
            subtotal_cents=subtotal_cents,
            total_cents=subtotal_cents + round(shipping_cost * 100),
        )
        db.session.add(order)
        db.session.flush()  # get order.id before adding items

        for i in items:
            if i.product.stock_qty < i.quantity:
                db.session.rollback()
                flash(f"Not enough stock for {i.product.name}.")
                return redirect(url_for("customer.cart"))
            i.product.stock_qty -= i.quantity
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=i.product.id,
                store_id=i.product.store_id,
                quantity=i.quantity,
                price_cents_at_purchase=i.product.price_cents,
            ))
            db.session.delete(i)

        db.session.commit()
        flash("Order placed!")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    return render_template("checkout.html", items=items)


@customer_bp.route("/orders")
@login_required
def orders():
    order_list = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("orders.html", orders=order_list)


@customer_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first_or_404()
    return render_template("order_detail.html", order=order)


@customer_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def order_cancel(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first_or_404()
    if order.status not in ("pending", "paid"):
        flash("This order can no longer be cancelled.")
        return redirect(url_for("customer.order_detail", order_id=order.id))
    order.status = "cancelled"
    for item in order.items:
        item.item_status = "cancelled"
        item.product.stock_qty += item.quantity
    db.session.commit()
    flash("Order cancelled.")
    return redirect(url_for("customer.order_detail", order_id=order.id))


@customer_bp.route("/orders/<int:order_id>/items/<int:item_id>/return", methods=["POST"])
@login_required
def request_return(order_id, item_id):
    order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first_or_404()
    item = next((i for i in order.items if i.id == item_id), None) or abort(404)
    if item.item_status != "fulfilled":
        flash("This item isn't eligible for a return request.")
    else:
        item.item_status = "return_requested"
        db.session.commit()
        flash("Return request submitted; the seller will review it.")
    return redirect(url_for("customer.order_detail", order_id=order.id))


@customer_bp.route("/message/<int:seller_id>", methods=["POST"])
@login_required
def message_seller(seller_id):
    store = Store.query.filter_by(seller_id=seller_id).first()
    if store is None:
        abort(404)
    body = request.form.get("body", "").strip()
    product_id = request.form.get("product_id", type=int)
    order_id = request.form.get("order_id", type=int)
    if not body:
        flash("Message cannot be empty.")
    else:
        db.session.add(Message(
            sender_id=current_user.id,
            recipient_id=seller_id,
            product_id=product_id,
            order_id=order_id,
            body=body,
        ))
        db.session.commit()
        flash("Message sent to seller.")
    return redirect(request.referrer or url_for("customer.index"))
