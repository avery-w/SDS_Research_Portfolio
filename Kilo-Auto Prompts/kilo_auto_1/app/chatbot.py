"""AI Chatbot engine with OpenAI integration and rules-based fallback.

If OPENAI_API_KEY is set, the chatbot delegates to GPT-4o-mini;
otherwise it falls back to a keyword-driven knowledge engine.
It also detects product/order inquiries and suggests contacting the
relevant seller directly through the platform's messaging system.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional

from app.config import settings

# ── Knowledge base (fallback) ────────────────────────────
HELPFUL_LINKS = {
    "shipping": "/shipping-info",
    "returns": "/returns-policy",
    "payment": "/payment-methods",
    "account": "/account",
    "tracking": "/orders",
    "contact": "/messages",
}

_RETURN_WINDOW_DAYS = 30
_MAX_RETURN_VALUE_USD = 5000

_SANDWICH_TEMPLATES = {
    "greeting": [
        "Hi there! 👋 Welcome to Kilo Marketplace. How can I help you today?",
        "Hello! I'm your shopping assistant. What can I do for you?",
    ],
    "farewell": [
        "Is there anything else I can help you with?",
        "Glad I could help! Have a great day.",
    ],
    "contact_seller": [
        "I'd recommend reaching out directly to the seller through our messaging system. "
        "Go to your order details and click 'Message Seller' — they typically reply within a few hours.",
        "The best way to get specific product questions answered is to message the seller "
        "directly from the product page or your order. They know their inventory best!",
    ],
    "order_status": [
        "You can check your order status anytime in your Order History under your dashboard. "
        "If you need more details, contacting the seller directly through the app is the fastest way.",
        "For real-time tracking, check your order details page. You can also message the seller "
        "for the latest update on your shipment.",
    ],
    "return_policy": [
        f"We offer a {_RETURN_WINDOW_DAYS}-day return policy on most items. Items must be "
        "unopened or in original condition. Would you like to start a return request?",
        "You can request a return from your order history. The seller typically processes "
        "refunds within 3-5 business days after receiving the item back.",
    ],
    "shipping_info": [
        "We ship via UPS with rates calculated based on destination and package dimensions. "
        "You'll see exact shipping costs at checkout.",
    ],
    "payment_methods": [
        "We accept all major credit cards, PayPal, and Apple Pay. Your payment is processed "
        "securely with encryption.",
    ],
    "account_help": [
        "You can update your profile, email, and address from your Account Settings page. "
        "Need help resetting your password? Use the 'Forgot Password' link on the login page.",
    ],
    "default": [
        "I'm still learning! For more specific questions about products, orders, or stores, "
        "I'd recommend messaging the seller directly — they can give you the most accurate info.",
        "Good question! Let me connect you with the right person. You can message the seller "
        "through our in-app messaging for detailed product or order questions.",
    ],
}


def _build_context_snippet(user_message: str, history: list[dict]) -> str:
    """Build a compact context string from recent history."""
    parts = []
    for msg in history[-6:]:
        role = msg.get("sender", "user")
        text = msg.get("message", "")[:200]
        parts.append(f"{role}: {text}")
    return "\n".join(parts)


def _classify_intent(message: str) -> Optional[str]:
    """Simple keyword-based intent classification."""
    lower = message.lower()
    if any(k in lower for k in ("hello", "hi ", "hey", "good morning", "good evening", "hi there")):
        return "greeting"
    if any(k in lower for k in ("thank", "appreciate", "thanks")):
        return "farewell"
    if any(k in lower for k in ("track", "where is my order", "order status", "shipping status", "delivery status", "when will")):
        return "order_status"
    if any(k in lower for k in ("return", "refund", "send back", "send it back")):
        return "return_policy"
    if any(k in lower for k in ("shipping", "delivery", "how long", "arrive", "transit", "ups ground")):
        return "shipping_info"
    if any(k in lower for k in ("payment", "pay", "credit card", "paypal", "apple pay", "billing")):
        return "payment_methods"
    if any(k in lower for k in ("password", "reset", "login", "account", "profile", "email change")):
        return "account_help"
    if any(k in lower for k in ("message", "contact", "talk to", "speak to", "seller", "reach out")):
        return "contact_seller"
    return None


def _rules_response(message: str, history: list[dict]) -> str:
    """Generate a response using the rules-based engine."""
    intent = _classify_intent(message)
    if intent is None:
        return _SANDWICH_TEMPLATES["default"][0]

    import random
    templates = _SANDWICH_TEMPLATES.get(intent, _SANDWICH_TEMPLATES["default"])

    # Check if the message seems product/order-specific and suggest seller contact
    product_related = any(
        k in message.lower()
        for k in ("this product", "the item", "this item", "product detail",
                   "color", "size", "fit", "quality", "material", "ingredient",
                   "in stock", "backorder", "out of stock", "preorder", "wait")
    )
    if product_related:
        return (
            random.choice(templates) + " " +
            "For specific details about this product, I'd recommend messaging the "
            "seller directly — they have the most up-to-date info on inventory and "
            "specifications."
        )
    if intent == "order_status" and len(history) > 0:
        return random.choice(templates)
    return random.choice(templates)


async def _llm_response(
    message: str,
    history: list[dict],
    product_id: Optional[int] = None,
    order_id: Optional[int] = None,
) -> str:
    """Generate a response via OpenAI API (if key is configured)."""
    if not settings.openai_api_key:
        return _rules_response(message, history)

    try:
        import httpx
        import json as _json

        system_prompt = (
            "You are Kilo Marketplace's shopping assistant. You help customers "
            "with product questions, order status, returns, shipping, payments, "
            "and account issues. When a question is about a specific product or "
            "order, encourage the customer to message the seller directly through "
            "the app's messaging feature for the most accurate and timely answer. "
            "Be friendly, concise, and helpful. Never fabricate product details "
            "or order information you don't have access to."
        )
        conversation = history + [{"role": "user", "content": message}]

        if product_id is not None:
            system_prompt += (
                f"\n[Context: This question references product ID {product_id}. "
                "If you can't confirm specifics, suggest the user message the seller.]"
            )
        if order_id is not None:
            system_prompt += (
                f"\n[Context: This question references order ID {order_id}. "
                "You don't have access to order data; suggest the user check their "
                "order page or message the seller.]"
            )

        body: dict[str, Any] = {
            "model": settings.chatbot_fallback_model,
            "messages": [{"role": "system", "content": system_prompt}]
            + conversation,
            "temperature": 0.6,
            "max_tokens": 300,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    except Exception:
        return _rules_response(message, history)


# ── Main public interface ────────────────────────────────
async def chatbot_respond(
    message: str,
    *,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    product_id: Optional[int] = None,
    order_id: Optional[int] = None,
    history: Optional[list[dict]] = None,
) -> dict:
    """Process a chatbot message and return a response + metadata.

    Returns
    -------
    dict
        {
            "response": str,
            "session_id": str,
            "suggest_seller": bool,
            "intent": Optional[str],
            "seller_id": Optional[int],  # suggested seller to message
            "product_id": Optional[int],
            "order_id": Optional[int],
        }
    """
    if history is None:
        history = []

    # Use session_id from param or generate one
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())

    response = await _llm_response(message, history, product_id, order_id)
    intent = _classify_intent(message)

    return {
        "response": response,
        "session_id": session_id,
        "suggest_seller": bool(
            intent in ("order_status", None)
            and (product_id is not None or order_id is not None)
        ) or (product_id is not None and intent is None),
        "intent": intent,
        "seller_id": None,
        "product_id": product_id,
        "order_id": order_id,
    }
