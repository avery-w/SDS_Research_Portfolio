from openai import OpenAI
from app.config import OPENAI_API_KEY


chatbot_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def generate_chatbot_reply(user_message: str, context: Optional[str] = None) -> str:
    if not chatbot_client:
        return (
            "I'm here to help! For product questions, please message the seller directly through the app. "
            "For order issues, check your order history or contact support."
        )
    system_prompt = (
        "You are a helpful e-commerce assistant. Answer customer questions clearly and briefly. "
        "If a customer asks about a specific product, order, or seller detail, encourage them to message the seller directly through the application for the fastest help."
    )
    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "system", "content": f"Context: {context}"})
    messages.append({"role": "user", "content": user_message})
    try:
        response = chatbot_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return (
            "I'm having trouble connecting right now. For product questions, please message the seller directly through the app. "
            "For order issues, check your order history or contact support."
        )
