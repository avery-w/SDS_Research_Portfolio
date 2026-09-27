from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.services.chatbot import ChatbotService

chatbot_bp = Blueprint("chatbot", __name__)

@chatbot_bp.route("/chat")
@login_required
def chat_page():
    return render_template("chatbot/chat.html")

@chatbot_bp.route("/chat/send", methods=["POST"])
@login_required
def chat_send():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    reply = ChatbotService.get_response(user_message, history)
    return jsonify({"reply": reply})
