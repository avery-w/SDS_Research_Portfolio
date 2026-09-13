"""AI shopping-assistant chatbot.

Answers general product/order/policy questions, but is instructed to push
customers toward messaging the seller directly for anything specific to a
particular product or order (condition, customization, delay, etc.), since
sellers are the source of truth on their own inventory and orders.
"""

from anthropic import Anthropic

from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are the shopping assistant for an online marketplace.
Help customers with general questions: how checkout/shipping/returns work,
navigating the site, and comparing product categories.

You do NOT have real-time access to a specific seller's inventory, order
status, or product condition. Whenever a customer asks something that
depends on a specific product or order (availability, customization,
shipping delay, item condition, warranty, etc.), tell them clearly that the
seller can answer that directly and point them to the "Message Seller"
button on the product or order page. Keep answers short and friendly.
Never invent order or shipping details."""

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def get_chat_reply(history: list[dict]) -> str:
    """history: list of {"role": "user"|"assistant", "content": str}, oldest first."""
    if not settings.anthropic_api_key:
        return (
            "The AI assistant isn't configured yet. In the meantime, you can use the "
            "\"Message Seller\" button on any product or order for direct help."
        )

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=history,
    )
    return "".join(block.text for block in response.content if block.type == "text")
