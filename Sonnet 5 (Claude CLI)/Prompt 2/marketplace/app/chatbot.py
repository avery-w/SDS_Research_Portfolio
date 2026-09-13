"""
Keyword-based assistant. It answers generic FAQ (shipping, returns, account)
and, for anything product- or order-specific, points the customer to the
in-app seller messaging (Message model) instead of guessing on the seller's
behalf.

ponytail: rule-based matching, not an LLM. Swap in a real LLM API call here
if free-form conversation quality matters more than zero-dependency/zero-cost.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.models import Order

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/api/chatbot")

FAQ = [
    (("shipping", "how long", "deliver"), "Shipping cost and speed are calculated at checkout based on your address and package weight. Ground is cheapest, Next Day is fastest."),
    (("return", "refund"), "You can request a return from your Order History page within 30 days of delivery. The seller reviews and approves return requests."),
    (("cancel",), "You can cancel an order from Order History as long as it hasn't shipped yet."),
    (("password", "account", "login"), "You can update your account details and password from the Account Settings page."),
    (("payment", "card", "charge"), "Payments are processed at checkout. If you see an unexpected charge, check your Order History first."),
]

SELLER_REDIRECT = (
    "That sounds like something specific to this product or order, best answered "
    "by the seller directly. Use the 'Message Seller' button on the product or "
    "order page and they'll get back to you."
)


def _match_faq(text):
    text = text.lower()
    for keywords, answer in FAQ:
        if any(k in text for k in keywords):
            return answer
    return None


@chatbot_bp.route("/ask", methods=["POST"])
@login_required
def ask():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify(error="message is required"), 400

    lowered = message.lower()

    if "order" in lowered and "status" in lowered:
        order_id = data.get("order_id")
        if order_id is not None:
            try:
                order_id = int(order_id)
            except (TypeError, ValueError):
                return jsonify(reply="That doesn't look like a valid order number."), 400
            order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first()
            if order:
                return jsonify(reply=f"Order #{order.id} is currently '{order.status}'.")
            return jsonify(reply="I couldn't find that order on your account.")
        return jsonify(reply="Which order number? Or check it directly on your Order History page.")

    faq_answer = _match_faq(lowered)
    if faq_answer:
        return jsonify(reply=faq_answer)

    if any(w in lowered for w in ("product", "item", "seller", "quality", "size", "color", "material", "when will")):
        return jsonify(reply=SELLER_REDIRECT)

    return jsonify(reply="I can help with shipping, returns, cancellations, and account questions. For anything about a specific product or order, message the seller directly.")
