"""
Marketplace AI assistant.
Always steers customers toward in-app messaging with sellers for product/order questions.
"""
from .config import get_settings

settings = get_settings()

SYSTEM_PROMPT = (
    "You are a helpful assistant for an online marketplace. "
    "Always encourage customers to message the seller directly through the application "
    "for product-specific or order questions. Never invent order statuses or inventory. "
    "Keep answers short and friendly."
)


def simple_rule_bot(message: str) -> str:
    msg = message.lower().strip()

    if any(w in msg for w in ("shipping", "delivery", "when will", "track", "arrive")):
        return (
            "Shipping rates are calculated at checkout using UPS-style guidelines "
            "from our Austin warehouse (110 Inner Campus Drive, TX 78705). "
            "For tracking a specific order, message the seller directly in the app."
        )
    if any(w in msg for w in ("return", "cancel", "refund", "exchange")):
        return (
            "You can request a cancellation or return from Order History. "
            "Sellers typically respond within 24–48 hours. "
            "Message the seller for the fastest resolution."
        )
    if any(w in msg for w in ("stock", "available", "inventory", "in stock")):
        return (
            "Inventory is controlled by each seller. "
            "Open the product page and message the seller for the latest availability."
        )
    if any(w in msg for w in ("hello", "hi", "hey", "help")):
        return (
            "Hi! I can answer general questions about how the marketplace works. "
            "For anything about a specific product or your order, "
            "please message the seller directly — that's the fastest and most accurate way."
        )
    if any(w in msg for w in ("price", "cost", "discount", "sale", "promo")):
        return (
            "Prices are set by individual sellers. "
            "Check the product page or message the seller about bulk or promotional pricing."
        )
    return (
        "I'm happy to help with general questions! "
        "For detailed product or order issues, message the seller directly through the app. "
        "You can also browse products, manage your cart, or view order history from the menu."
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
