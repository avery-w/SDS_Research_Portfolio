"""Shopping assistant ("Bevo Bot"). Claude with store tools; falls back to a keyword helper offline.

The assistant answers catalog/shipping/order-status questions itself and hands anything only a seller
can answer (fit, custom requests, order problems) to in-app seller messaging via `contact_seller`.
"""
import json
import os

import anthropic
from anthropic import beta_tool
from flask import current_app, url_for

import shipping
from core import Invalid, shipping_quote
from models import Order, Product, Store, db, setting
from shop import catalog

MODEL = os.environ.get("CHAT_MODEL", "claude-opus-5")

SYSTEM = """You are Bevo Bot, the shopping assistant for {platform}, a multi-seller marketplace that ships \
every order by UPS from 110 Inner Campus Drive, Austin, TX 78705.

Help customers find products, compare options, estimate UPS shipping, and check their orders. Use the tools \
for anything factual (prices, stock, order status, shipping); never invent products, prices, policies or \
tracking numbers.

Sellers know their products and orders best. Whenever a question needs the seller (sizing or fit, materials \
beyond the listing, custom requests, bulk pricing, damaged or late items, anything about a specific order), \
call contact_seller so the customer gets a button to message that seller directly in the app, and say so. \
Returns and cancellations are started from the order page; mention that when relevant.

Keep replies short and friendly: 1-4 sentences or a tight list. Prices are USD. Returns are accepted within \
{window} days of delivery. Orders over ${free} get free UPS Ground."""


def reply(messages, user):
    actions = []
    if os.environ.get("CHATBOT_OFFLINE") == "1":
        return offline(messages[-1]["content"], actions)
    try:
        client = anthropic.Anthropic()
        runner = client.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=16000,
            max_iterations=6,
            system=SYSTEM.format(platform=setting("platform_name"), window=setting("return_window_days"),
                                 free=f"{setting('free_shipping_over'):g}"),
            tools=tools_for(user, actions),
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},  # chat is latency-sensitive; low effort holds up well here
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        final = None
        for message in runner:
            final = message
    except anthropic.AuthenticationError:
        current_app.logger.warning("Chatbot credentials were rejected; using offline helper.")
        return offline(messages[-1]["content"], actions)
    except TypeError as e:
        # The SDK raises TypeError when no credential source resolves at all (no key, token or profile).
        if "authentication" not in str(e):
            raise
        current_app.logger.warning("No Anthropic credentials configured; using offline helper.")
        return offline(messages[-1]["content"], actions)
    except anthropic.RateLimitError:
        return {"reply": "I'm getting a lot of questions right now. Give me a few seconds and ask again.",
                "actions": actions, "mode": "ai"}
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        current_app.logger.error("Chatbot API error: %s", e)
        return offline(messages[-1]["content"], actions)
    if final is None or final.stop_reason == "refusal":
        text = "I can't help with that one, but a seller or our support team can."
    else:
        text = "\n".join(b.text for b in final.content if b.type == "text").strip() or \
            "Could you tell me a bit more about what you're looking for?"
    return {"reply": text, "actions": actions, "mode": "ai"}


def tools_for(user, actions):
    """Tools are closures over the signed-in user so order lookups can never cross accounts."""
    def brief(p):
        return {"product_id": p.id, "name": p.name, "price": p.price_cents / 100, "category": p.category,
                "in_stock": p.stock, "store_id": p.store_id, "store": p.store.name,
                "url": url_for("shop.product", pid=p.id)}

    @beta_tool
    def search_products(query: str, category: str = "", max_price: float = 0) -> str:
        """Search the marketplace catalog.

        Args:
            query: Keywords, e.g. "hiking backpack". Use "" to browse a category.
            category: Optional exact category (Electronics, Home, Apparel, Books, Outdoors, Beauty, Toys, Grocery).
            max_price: Optional maximum price in USD; 0 means no limit.
        """
        hits = catalog(query[:100], category or None, None, int(max_price * 100) if max_price > 0 else None,
                       "price_asc").limit(8).all()
        return json.dumps([brief(p) for p in hits]) if hits else "No matching products."

    @beta_tool
    def get_product(product_id: int) -> str:
        """Full details for one product: description, stock, dimensions, seller.

        Args:
            product_id: The product's id.
        """
        p = db.session.get(Product, product_id)
        if not p or not p.purchasable:
            return "Error: product not found or not currently for sale."
        return json.dumps(brief(p) | {"description": p.description[:1500], "weight_lb": p.weight_lb,
                                      "dimensions_in": [p.length_in, p.width_in, p.height_in]})

    @beta_tool
    def estimate_shipping(product_id: int, zip_code: str, qty: int = 1) -> str:
        """Estimate UPS shipping options and costs for a product to a destination ZIP.

        Args:
            product_id: The product's id.
            zip_code: 5-digit US destination ZIP code.
            qty: Quantity, 1-20.
        """
        p = db.session.get(Product, product_id)
        if not p or not p.purchasable:
            return "Error: product not found."
        try:
            q = shipping_quote(zip_code, [(p, max(1, min(qty, 20)))])
        except Invalid as e:
            return "Error: " + " ".join(e.errors.values())
        return json.dumps({"zone": q["zone"], "origin": "Austin, TX 78705", "options": [
            {k: o[k] for k in ("name", "total", "transit_days", "free")} for o in q["options"]]})

    @beta_tool
    def list_my_orders() -> str:
        """List the signed-in customer's 10 most recent orders with status."""
        if not user or user.role != "customer":
            return "The customer isn't signed in. Ask them to sign in to see orders."
        rows = Order.query.filter_by(user_id=user.id).order_by(Order.id.desc()).limit(10).all()
        return json.dumps([{"order_id": o.id, "placed": o.created_at.strftime("%b %d, %Y"), "status": o.status,
                            "total": o.total_cents / 100, "items": [i.name for i in o.items]} for o in rows]) \
            or "No orders yet."

    @beta_tool
    def get_order(order_id: int) -> str:
        """Details and per-item status/tracking for one of the signed-in customer's orders.

        Args:
            order_id: The order number.
        """
        o = db.session.get(Order, order_id)
        if not user or not o or o.user_id != user.id:
            return "Error: no such order on this account."
        return json.dumps({"order_id": o.id, "status": o.status, "shipping": o.shipping_service,
                           "url": url_for("shop.order", oid=o.id), "items": [
                               {"name": i.name, "qty": i.qty, "status": i.status, "tracking": i.tracking or None,
                                "store_id": i.store_id} for i in o.items]})

    @beta_tool
    def contact_seller(store_id: int, reason: str, product_id: int = 0, order_id: int = 0) -> str:
        """Give the customer a button to message a seller directly in the app. Use for anything the seller
        must answer: product specifics not in the listing, custom requests, or problems with an order.

        Args:
            store_id: The seller's store id (from product or order data).
            reason: Short label for the button, e.g. "Ask about sizing".
            product_id: Optional related product id.
            order_id: Optional related order id (must belong to this customer).
        """
        s = db.session.get(Store, store_id)
        if not s or not s.is_active:
            return "Error: that store isn't accepting messages."
        params = {"store_id": s.id}
        if product_id:
            params["product_id"] = product_id
        if order_id and user and (o := db.session.get(Order, order_id)) and o.user_id == user.id:
            params["order_id"] = order_id
        actions.append({"label": f"{reason[:40]} · Message {s.name}", "url": url_for("shop.new_message", **params)})
        note = "" if user else " (they'll be asked to sign in first)"
        return f"Button added for messaging {s.name}{note}."

    return [search_products, get_product, estimate_shipping, list_my_orders, get_order, contact_seller]


def offline(text, actions):
    """No-API fallback: keyword search plus a nudge toward messaging the seller."""
    words = [w for w in text.lower().replace("?", " ").split() if len(w) > 3][:5]
    hits = []
    for w in words:
        hits += [p for p in catalog(w).limit(3).all() if p not in hits]
    if any(k in text.lower() for k in ("order", "return", "refund", "cancel", "track")):
        msg = ("You can track, cancel, or return items from Orders in the top menu. For anything else about an "
               "order, open it and tap \"Message seller\", since the seller can help fastest.")
    elif hits:
        msg = "Here's what I found:\n" + "\n".join(f"• {p.name}: ${p.price_cents / 100:,.2f} ({p.store.name})"
                                                   for p in hits[:4])
        p = hits[0]
        actions.append({"label": f"Ask {p.store.name} a question",
                        "url": url_for("shop.new_message", store_id=p.store_id, product_id=p.id)})
        actions += [{"label": f"View {p.name}", "url": url_for("shop.product", pid=p.id)} for p in hits[:2]]
    else:
        msg = ("I couldn't find a match. Try a product name or category, or message a seller directly "
               "from any product page. They know their items best!")
    return {"reply": msg + f"\n\n(UPS ships from {shipping.ORIGIN['city']}, {shipping.ORIGIN['state']}.)",
            "actions": actions, "mode": "offline"}
