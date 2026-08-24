from flask import Blueprint, jsonify, request

from app.config import Config
from app.utils.sanitize import sanitize_search, sanitize_text

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/shipping/quote", methods=["POST"])
def shipping_quote():
    payload = request.get_json(silent=True) or {}
    zip_code = sanitize_text(payload.get("zip_code", ""), max_length=10)
    weight = payload.get("weight_kg", 0)
    distance = payload.get("distance_miles", 0)

    if not zip_code or not isinstance(weight, (int, float)) or not isinstance(distance, (int, float)):
        return jsonify({"error": "Invalid shipping payload"}), 400

    base_rate = 8.95
    weight_cost = max(0.0, float(weight) * 1.15)
    distance_cost = max(0.0, float(distance) * 0.09)
    total = round(base_rate + weight_cost + distance_cost, 2)

    return jsonify(
        {
            "origin": Config.UPS_ORIGIN_ADDRESS,
            "destination_zip": zip_code,
            "rate": total,
            "currency": "USD",
            "service": "UPS Ground",
        }
    )


@api_bp.route("/chatbot", methods=["POST"])
def chatbot_response():
    payload = request.get_json(silent=True) or {}
    message = sanitize_text(payload.get("message", ""), max_length=500)
    if not message:
        return jsonify({"reply": "Please enter a question about a product or order."}), 400

    lowered = message.lower()
    if "order" in lowered:
        reply = "I can help with an order question. Please message the seller directly through the app to review shipment status or order details."
    elif "product" in lowered or "size" in lowered or "color" in lowered:
        reply = "For product questions, message the seller directly through the app to confirm details before you buy."
    else:
        reply = "I can help you browse products or connect with a seller directly through the app for more detail."

    return jsonify({"reply": reply})
