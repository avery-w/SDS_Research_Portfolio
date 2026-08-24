from flask import Blueprint, jsonify, request

from app.config import Config
from app.utils.sanitize import sanitize_text

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/shipping/quote", methods=["POST"])
def shipping_quote():
    payload = request.get_json(silent=True) or {}
    zip_code = sanitize_text(payload.get("zip_code", ""), max_length=10)
    weight_kg = payload.get("weight_kg", 0)
    distance_miles = payload.get("distance_miles", 0)

    if not zip_code or not isinstance(weight_kg, (int, float)) or not isinstance(distance_miles, (int, float)):
        return jsonify({"error": "Invalid shipping payload."}), 400

    base = 8.95
    weight_cost = float(weight_kg) * 1.10
    distance_cost = float(distance_miles) * 0.08
    total = round(base + weight_cost + distance_cost, 2)

    return jsonify({
        "origin": Config.UPS_ORIGIN_ADDRESS,
        "destination_zip": zip_code,
        "service": "UPS Ground",
        "rate": total,
        "currency": "USD",
    })


@api_bp.route("/chatbot", methods=["POST"])
def chatbot_response():
    payload = request.get_json(silent=True) or {}
    message = sanitize_text(payload.get("message", ""), max_length=500)

    if not message:
        return jsonify({"reply": "Please ask a question about a product or order."}), 400

    lower = message.lower()
    if "order" in lower:
        reply = "I can help with your order question. Message the seller directly through the app for shipping, delivery, or fulfillment details."
    elif "product" in lower or "size" in lower or "color" in lower:
        reply = "For product questions, please message the seller directly through the app so they can answer details before you buy."
    else:
        reply = "I can help with shopping questions. For more detail, message the seller directly from the app."

    return jsonify({"reply": reply})
