from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Message, User, Product, Store
from app.services.chatbot import ChatbotService

chatbot_bp = Blueprint('chatbot', __name__)


@chatbot_bp.route('/')
@login_required
def chat():
    return render_template('chatbot/chat.html')


@chatbot_bp.route('/message', methods=['POST'])
@login_required
def chat_message():
    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    chatbot = ChatbotService()
    response = chatbot.get_response(user_message, current_user)

    return jsonify({
        'response': response['message'],
        'suggest_seller_contact': response.get('suggest_seller_contact', False),
        'seller_id': response.get('seller_id'),
        'product_id': response.get('product_id')
    })


@chatbot_bp.route('/suggest-seller/<int:product_id>')
@login_required
def suggest_seller(product_id):
    product = Product.query.get_or_404(product_id)
    seller = product.store.owner

    return jsonify({
        'seller_id': seller.id,
        'seller_name': seller.full_name,
        'store_name': product.store.name,
        'product_name': product.name,
        'message': f'Would you like to message {seller.full_name} from {product.store.name} about "{product.name}"?'
    })
