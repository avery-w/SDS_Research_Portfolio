from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.order import Order, OrderItem
from app.models.cart import CartItem
from app.models.product import Product
from app.services.shipping import calculate_ups_shipping
from app.utils.sanitizers import sanitize_string, sanitize_quantity
from app.utils.validators import validate_zip, validate_price
from app.config import Config
import stripe

bp = Blueprint("checkout", __name__, url_prefix="/api/checkout")

@bp.route("/calculate-shipping", methods=["POST"])
@login_required
def calculate_shipping():
    data = request.get_json(silent=True) or {}
    dest_zip = sanitize_string(data.get("destination_zip", ""))
    if not validate_zip(dest_zip):
        return jsonify({"error": "Invalid destination ZIP"}), 400
    weight = float(data.get("weight_lbs", 1))
    dims = tuple(int(x) for x in data.get("dimensions", [10, 10, 10]))
    result = calculate_ups_shipping(Config.UPS_ORIGIN_ZIP, dest_zip, weight, dims)
    return jsonify(result)

@bp.route("/place-order", methods=["POST"])
@login_required
def place_order():
    data = request.get_json(silent=True) or {}
    shipping_address = sanitize_string(data.get("shipping_address", ""))
    dest_zip = sanitize_string(data.get("destination_zip", ""))
    if not validate_zip(dest_zip):
        return jsonify({"error": "Invalid ZIP"}), 400

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400

    total = 0
    order_items = []
    for ci in cart_items:
        qty = sanitize_quantity(ci.quantity)
        subtotal = float(ci.product.price) * qty
        total += subtotal
        order_items.append((ci.product, qty, float(ci.product.price)))

    shipping = calculate_ups_shipping(Config.UPS_ORIGIN_ZIP, dest_zip, weight=1, dimensions=(10,10,10))
    total += shipping["cost"]

    order = Order(
        customer_id=current_user.id,
        seller_id=order_items[0][0].store.seller_id,
        shipping_address=shipping_address,
        shipping_cost=shipping["cost"],
        total_amount=total,
        status="pending"
    )
    db.session.add(order)
    db.session.flush()

    for product, qty, price in order_items:
        oi = OrderItem(order_id=order.id, product_id=product.id, quantity=qty, unit_price=price)
        db.session.add(oi)
        product.stock_quantity -= qty

    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"order_id": order.id, "total": float(order.total_amount)}), 201
