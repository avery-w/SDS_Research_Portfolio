from openai import OpenAI
from app.core.config import settings

SYSTEM_PROMPT = (
    "You are a helpful shopping assistant for a multi-seller marketplace. "
    "Answer briefly. For product- or order-specific questions, encourage the user "
    "to message the seller directly via the 'Message Seller' button on the product or order page. "
    "Avoid making binding promises; defer to seller policies and platform rules."
)

def ask_chatbot(messages: list[dict]) -> str:
    if not settings.OPENAI_API_KEY:
        return "Chat is unavailable right now. Please message the seller directly from the product or order page."
    client = OpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
    full = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=full, temperature=0.2, max_tokens=300)
    return resp.choices[0].message.content.strip()
