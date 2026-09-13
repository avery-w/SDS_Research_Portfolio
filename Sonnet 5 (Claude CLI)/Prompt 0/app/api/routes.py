from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from app.extensions import db, csrf
from app.models import Cart
from app.shipping import get_shipping_rates
from app.chatbot import get_chatbot_reply

api_bp = Blueprint("api", __name__)


@api_bp.route("/checkout/shipping-rates", methods=["POST"])
@login_required
@csrf.exempt
def shipping_rates():
    data = request.get_json(force=True) or {}
    destination = {
        "address": data.get("address", ""),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "zip": data.get("zip", ""),
        "country": data.get("country", "US"),
    }
    if not all([destination["address"], destination["city"], destination["state"], destination["zip"]]):
        return jsonify({"error": "Missing destination address fields."}), 400

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        return jsonify({"error": "Cart is empty."}), 400

    total_oz = sum(item.product.weight_oz * item.quantity for item in cart.items)
    weight_lbs = max(total_oz / 16.0, 0.1)

    rates = get_shipping_rates(destination, weight_lbs)
    return jsonify({"rates": rates, "weight_lbs": round(weight_lbs, 2)})


@api_bp.route("/chatbot", methods=["POST"])
@login_required
@csrf.exempt
def chatbot():
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message required."}), 400
    reply = get_chatbot_reply(message)
    return jsonify({"reply": reply})
