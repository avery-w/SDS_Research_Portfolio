"""Customer-facing AI chatbot. Uses the Claude API when ANTHROPIC_API_KEY is
set; otherwise falls back to a small rule-based responder so the app still
runs out of the box with no external key."""

import os

SYSTEM_PROMPT = (
    "You are the shopping assistant for an online marketplace. Help customers "
    "with general questions: how checkout, shipping, returns, and accounts work. "
    "You do NOT have real-time access to a specific seller's inventory, order "
    "details, or shipment status. Whenever a question is about a *specific* "
    "product's condition/availability or a *specific* order's status, tell the "
    "customer you can't see that and encourage them to message the seller "
    "directly through the app's messaging feature, that's the fastest way to "
    "get an accurate answer. Keep replies short and friendly."
)

SELLER_TRIGGER_KEYWORDS = (
    "my order", "order status", "where is my", "tracking", "arrived", "damaged",
    "wrong item", "does this come in", "is this in stock", "seller", "custom size",
    "when will it ship", "refund my", "exchange",
)

_client = None


def _get_client():
    global _client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _suggests_seller_contact(message: str) -> bool:
    lowered = message.lower()
    return any(kw in lowered for kw in SELLER_TRIGGER_KEYWORDS)


def _rule_based_reply(message: str) -> str:
    lowered = message.lower()
    if any(k in lowered for k in ("return", "refund", "exchange")):
        return (
            "You can request a return from Order History within 30 days of delivery. "
            "For specifics about a particular item's condition, message the seller directly, "
            "they handle their own returns and can move faster than I can."
        )
    if any(k in lowered for k in ("ship", "delivery", "tracking", "arrive")):
        return (
            "Shipping rates are calculated at checkout based on package weight/size and your "
            "zip code, with Ground, 3-Day, 2nd Day, and Next Day options. For tracking on an "
            "order you already placed, check Order History, or message the seller for the latest update."
        )
    if any(k in lowered for k in ("cart", "checkout", "payment")):
        return "Add items to your cart from any product page, then head to Checkout to enter your address and pick a shipping speed."
    if any(k in lowered for k in ("account", "password", "login", "sign up")):
        return "You can manage your account details from the Account page after logging in."
    if _suggests_seller_contact(message):
        return (
            "I don't have visibility into that specific product or order, the seller does. "
            "Use the \"Message Seller\" button on the product or order page, they can give you a direct answer."
        )
    return (
        "I can help with general questions about browsing, checkout, shipping, and returns. "
        "For anything specific to a product or an existing order, messaging the seller directly "
        "is the quickest way to get a real answer."
    )


def get_reply(message: str, history: list[dict]) -> tuple[str, bool]:
    """Returns (reply_text, suggest_contact_seller)."""
    suggest = _suggests_seller_contact(message)
    client = _get_client()
    if client is None:
        return _rule_based_reply(message), suggest

    messages = [{"role": h["role"], "content": h["content"]} for h in history]
    messages.append({"role": "user", "content": message})
    try:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = "".join(block.text for block in response.content if block.type == "text")
        return reply or _rule_based_reply(message), suggest
    except Exception:
        return _rule_based_reply(message), suggest
