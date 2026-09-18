"""
Marketplace AI assistant.
User messages are never used in SQL, file paths, or shell commands.
Optional OpenAI path sends the message only as a chat-completion payload.
"""
from .config import get_settings

settings = get_settings()

SYSTEM_PROMPT = (
    "You are a helpful marketplace assistant. "
    "Always encourage customers to message the seller directly through the application "
    "for product-specific or order questions. Never invent order statuses or inventory. "
    "Keep answers short and friendly."
)


def simple_rule_bot(message: str) -> str:
    msg = message.lower().strip()
    if any(w in msg for w in ("shipping", "delivery", "when will", "track", "arrive")):
        return (
            "Shipping is calculated at checkout using UPS-style guidelines "
            "from our Austin warehouse (110 Inner Campus Drive, TX 78705). "
            "For tracking a specific order, message the seller directly in the app."
        )
    if any(w in msg for w in ("return", "cancel", "refund", "exchange")):
        return (
            "Request a cancellation or return from Order History. "
            "Sellers usually respond within 24–48 hours. "
            "Message the seller for the fastest help."
        )
    if any(w in msg for w in ("stock", "available", "inventory", "in stock")):
        return (
            "Inventory is managed by each seller. "
            "Message the seller from the product page for current availability."
        )
    if any(w in msg for w in ("hello", "hi", "hey", "help")):
        return (
            "Hi! I answer general questions about the marketplace. "
            "For product or order specifics, please message the seller directly in the app."
        )
    return (
        "I can help with general questions. "
        "For product or order details, message the seller directly through the application."
    )


async def get_chat_response(user_message: str) -> str:
    if settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=180,
                temperature=0.6,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass
    return simple_rule_bot(user_message)
