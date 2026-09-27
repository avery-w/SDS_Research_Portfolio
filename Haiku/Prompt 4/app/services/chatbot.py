from app.config import get_settings
import openai

settings = get_settings()
openai.api_key = settings.OPENAI_API_KEY

def get_chatbot_response(user_message: str) -> str:
    """
    Get chatbot response using OpenAI API.
    ponytail: rule-based fallback for test mode (no API key)
    """

    if settings.OPENAI_API_KEY == "sk-placeholder":
        return get_fallback_response(user_message)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful e-commerce customer support chatbot.
                    Assist customers with questions about products, orders, and the platform.
                    Be friendly and concise. Suggest contacting sellers directly for product-specific questions."""
                },
                {"role": "user", "content": user_message}
            ],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return get_fallback_response(user_message)

def get_fallback_response(message: str) -> str:
    """Rule-based responses for demo/test mode"""

    message_lower = message.lower()

    if any(word in message_lower for word in ["track", "tracking", "order status"]):
        return "You can track your order using the tracking number provided in your email. Visit the 'My Orders' section to view all your orders and their status."

    if any(word in message_lower for word in ["return", "refund", "money back"]):
        return "We offer returns within 30 days of delivery. For delivered orders, you can request a return from your order details. A seller will review and approve your request."

    if any(word in message_lower for word in ["shipping", "delivery", "when will"]):
        return "Standard shipping typically takes 5-7 business days. The exact timeframe depends on your location. You can see the estimated delivery date during checkout."

    if any(word in message_lower for word in ["contact", "message", "seller"]):
        return "You can message sellers directly through the order details page. This is great for product-specific questions or issues with your order."

    if any(word in message_lower for word in ["password", "reset", "forgot"]):
        return "You can reset your password by clicking 'Forgot Password' on the login page. Follow the instructions sent to your email."

    if any(word in message_lower for word in ["help", "support", "assist"]):
        return "I'm here to help! You can ask me about shipping, returns, tracking orders, or how to use the platform. For complex issues, please contact our support team."

    return "Thanks for your question! I can help with tracking orders, returns, shipping times, and more. What would you like to know?"
