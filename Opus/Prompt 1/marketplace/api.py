from flask import Blueprint, jsonify, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import delete, update

from .chatbot import reply
from .models import CartItem, Order, OrderItem, Product, db
from .shipping import ShippingError, pack, quote
from .shop import cart_by_store

bp = Blueprint("api", __name__, url_prefix="/api")


def shipping_quote(groups, dest):
    stores = list(groups)
    return stores, quote([pack(groups[s]) for s in stores], dest)


@bp.errorhandler(ShippingError)
def shipping_error(exc):
    return jsonify(error=str(exc)), 400


@bp.route("/shipping/rates", methods=["POST"])
@login_required
def shipping_rates():
    """Body: {street, city, state, zip}. Rates for the current cart, shipped from Austin, TX 78705."""
    groups = cart_by_store(current_user)
    if not groups:
        return jsonify(error="Your cart is empty."), 400
    _, result = shipping_quote(groups, request.get_json(silent=True) or {})
    return jsonify(result)


@bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    """Body: {name, street, city, state, zip, service_code}. Rates are recomputed server-side, never trusted from the client."""
    data = request.get_json(silent=True) or {}
    for field in ("name", "street", "city"):
        if not str(data.get(field, "")).strip():
            return jsonify(error=f"Shipping {field} is required."), 400
    groups = cart_by_store(current_user)
    if not groups:
        return jsonify(error="Your cart is empty."), 400
    stores, rates = shipping_quote(groups, data)
    service = next((s for s in rates["services"] if s["code"] == data.get("service_code")), None)
    if not service:
        return jsonify(error="Choose an available shipping service."), 400

    orders = []
    for store, shipping_cents in zip(stores, service["per_shipment_cents"]):
        order = Order(
            customer_id=current_user.id,
            store_id=store.id,
            subtotal_cents=sum(p.price_cents * q for p, q in groups[store]),
            shipping_cents=shipping_cents,
            shipping_service=service["name"],
            ship_name=data["name"].strip()[:120],
            ship_street=data["street"].strip()[:200],
            ship_city=data["city"].strip()[:100],
            ship_state=data["state"].strip().upper(),
            ship_zip=data["zip"].strip(),
        )
        for p, qty in groups[store]:
            # Conditional decrement so two simultaneous checkouts can't oversell.
            taken = db.session.execute(
                update(Product).where(Product.id == p.id, Product.stock >= qty).values(stock=Product.stock - qty)
            ).rowcount
            if not taken:
                db.session.rollback()
                return jsonify(error=f"Only {db.session.get(Product, p.id).stock} of {p.name} left. Update your cart."), 409
            order.items.append(OrderItem(product_id=p.id, product_name=p.name, unit_price_cents=p.price_cents, quantity=qty))
        db.session.add(order)
        orders.append(order)
    db.session.execute(delete(CartItem).where(CartItem.user_id == current_user.id))
    db.session.commit()
    return jsonify(
        order_ids=[o.id for o in orders],
        total_cents=sum(o.total_cents for o in orders),
        redirect=url_for("shop.orders"),
    ), 201


@bp.route("/chat", methods=["POST"])
def chat():
    """Body: {messages: [{role: "user"|"assistant", content: str}, ...]}, ending with a user turn."""
    if not current_user.is_authenticated:  # keeps anonymous traffic off the paid model
        return jsonify(error="Log in to chat with the assistant."), 401
    history = (request.get_json(silent=True) or {}).get("messages")
    if not isinstance(history, list) or not history or len(history) > 20:
        return jsonify(error="Send 1-20 messages."), 400
    clean = []
    for i, m in enumerate(history):
        role = "user" if i % 2 == 0 else "assistant"
        if not isinstance(m, dict) or m.get("role") != role or not isinstance(m.get("content"), str) or not m["content"].strip():
            return jsonify(error="Messages must alternate user/assistant, starting and ending with user."), 400
        clean.append({"role": role, "content": m["content"][:2000]})
    if clean[-1]["role"] != "user":
        return jsonify(error="The last message must be from the user."), 400
    return jsonify(reply(clean, current_user))
