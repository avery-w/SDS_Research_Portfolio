from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.chatbot_service import chatbot_respond
from app.utils.sanitizers import sanitize_string

bp = Blueprint("chatbot", __name__, url_prefix="/api/chatbot")

@bp.route("/message", methods=["POST"])
@login_required
def send_message():
    data = request.get_json(silent=True) or {}
    user_message = sanitize_string(data.get("message", ""))
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    context = {"user_role": current_user.role, "user_id": current_user.id}
    reply = chatbot_respond(user_message, context)
    return jsonify({"reply": reply})
