"""AI shopping assistant.

Uses the Anthropic API when ANTHROPIC_API_KEY is set. Otherwise falls back to
a small keyword-based responder so the feature still works without a key.
Always nudges the customer to message the seller directly for
product/order-specific questions instead of answering on the seller's behalf.
"""

from flask import current_app

SYSTEM_PROMPT = (
    "You are a friendly shopping assistant for an online marketplace. Help "
    "customers with general questions: how to search, how checkout and "
    "shipping work, how to track or return an order, and how the site "
    "works. You do NOT know specifics about any individual product's real "
    "condition, availability nuances, or a seller's personal policies. "
    "Whenever a customer asks something only the seller would know "
    "(condition details, customization, order-specific problems, "
    "negotiating price, shipping delays), tell them to use the 'Message "
    "Seller' button on the product or order page to ask the seller "
    "directly. Keep answers short."
)


def _fallback_reply(message):
    text = message.lower()
    if any(word in text for word in ["return", "refund", "cancel"]):
        return (
            "You can request a return or cancellation from Order History > "
            "select the order > Request Return/Cancel. For anything specific "
            "about your item, the seller can help fastest, use the "
            "'Message Seller' button on the order page."
        )
    if any(word in text for word in ["ship", "delivery", "track", "arrive"]):
        return (
            "Shipping rates are calculated live at checkout using UPS "
            "service levels. For a specific delay or tracking question, "
            "message the seller directly from your order page, they can "
            "see the fulfillment status."
        )
    if any(word in text for word in ["condition", "size", "color", "material", "fit", "custom"]):
        return (
            "Great question for the seller, they know the item best. Use "
            "the 'Message Seller' button on the product page and they'll "
            "get back to you directly."
        )
    return (
        "I can help with general questions about browsing, checkout, and "
        "orders. For anything specific to a product or a seller's item, "
        "please use the 'Message Seller' button so they can answer directly."
    )


def get_chatbot_reply(message, history=None):
    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_reply(message)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        messages = list(history or [])
        messages.append({"role": "user", "content": message})
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text
    except Exception:
        current_app.logger.exception("Anthropic API call failed, using fallback")
        return _fallback_reply(message)
