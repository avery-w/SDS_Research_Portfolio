"""
Lightweight AI assistant for the marketplace.
Always steers customers toward messaging sellers directly inside the app
for product- or order-specific questions.
"""
from .config import get_settings

settings = get_settings()

SYSTEM_PROMPT = (
    "You are a helpful marketplace assistant. "
    "Always encourage customers to message the seller directly through the application "
    "for any product-specific or order questions. "
    "Never invent order statuses, inventory levels, or shipping dates. "
    "Keep answers short, friendly, and actionable."
)


def simple_rule_bot(message: str) -> str:
    msg = message.lower().strip()

    if any(w in msg for w in ["shipping", "delivery", "when will", "track"]):
        return (
            "Shipping rates are calculated at checkout using UPS-style guidelines "
            "from our Austin, TX warehouse (110 Inner Campus Drive). "
            "For order-specific tracking, please message the seller directly through the app."
        )

    if any(w in msg for w in ["return", "cancel", "refund", "exchange"]):
        return (
            "You can request a cancellation or return from your Order History page. "
            "Sellers usually respond within 24–48 hours. "
            "Message the seller directly for the fastest help."
        )

    if any(w in msg for w in ["stock", "available", "inventory", "in stock"]):
        return (
            "Inventory is managed by each individual seller. "
            "Message the seller from the product page for the latest availability."
        )

    if any(w in msg for w in ["hello", "hi", "hey", "help"]):
        return (
            "Hi! I can answer general questions about how the marketplace works. "
            "For anything about a specific product or your order, "
            "please message the seller directly inside the application — that's the fastest way."
        )

    if any(w in msg for w in ["price", "cost", "discount", "sale"]):
        return (
            "Product prices are set by the sellers. "
            "Check the product page for the current price, or message the seller "
            "if you have questions about bulk pricing or promotions."
        )

    return (
        "I'm here to help with general marketplace questions! "
        "For detailed product questions or order issues, the fastest and most accurate way "
        "is to message the seller directly through the application. "
        "You can also browse products, manage your cart, or check your order history from the menu."
    )


async def get_chat_response(user_message: str, context: dict | None = None) -> str:
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
            pass  # fall back to rules

    return simple_rule_bot(user_message)
