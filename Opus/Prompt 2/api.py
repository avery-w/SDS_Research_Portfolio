"""JSON API. Errors follow the contract in core.py: 400 validation_failed, 401, 403, 404, 409, 415, 429."""
from flask import Blueprint, abort, g, jsonify, request, url_for

import chatbot
import shipping
from core import Form, cart_lines, json_body, rate_limit, require, set_item_status, shipping_quote
from models import CATEGORIES, Order, db, setting
from shop import SORTS, add_to_cart, catalog, change_item, order_for_viewer, place_order, set_cart_qty, visible_product

bp = Blueprint("api", __name__, url_prefix="/api")


def product_json(p):
    return {"id": p.id, "name": p.name, "description": p.description, "category": p.category,
            "price": p.price_cents / 100, "stock": p.stock, "store": {"id": p.store.id, "name": p.store.name,
                                                                         "slug": p.store.slug},
            "weight_lb": p.weight_lb, "dimensions_in": [p.length_in, p.width_in, p.height_in],
            "image_url": url_for("upload", name=p.image) if p.image else None,
            "url": url_for("shop.product", pid=p.id)}


def order_json(o, items=None):
    return {"id": o.id, "status": o.status, "created_at": o.created_at.isoformat() + "Z",
            "subtotal": o.subtotal_cents / 100, "shipping": o.shipping_cents / 100, "tax": o.tax_cents / 100,
            "total": o.total_cents / 100, "shipping_service": o.shipping_service,
            "ship_to": {k: getattr(o, f"ship_{k}") for k in ("name", "street", "city", "state", "zip")},
            "items": [{"id": i.id, "product_id": i.product_id, "store_id": i.store_id, "name": i.name,
                       "qty": i.qty, "unit_price": i.unit_price_cents / 100, "status": i.status,
                       "tracking": i.tracking or None} for i in (items if items is not None else o.items)]}


def cart_json(user):
    lines = cart_lines(user)
    return {"items": [{"product": product_json(c.product), "qty": c.qty,
                       "line_total": c.qty * c.product.price_cents / 100} for c in lines],
            "subtotal": sum(c.qty * c.product.price_cents for c in lines) / 100}


@bp.get("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return {"status": "ok"}


# ---------- catalog (public) ----------

@bp.get("/products")
def products():
    f = Form(request.args)
    q = f.str("q", "Search", required=False, max_len=100)
    cat = f.choice("category", CATEGORIES, "Category", required=False)
    lo = f.money("min_price", "Minimum price", lo=0, required=False)
    hi = f.money("max_price", "Maximum price", lo=0, required=False)
    sort = f.choice("sort", list(SORTS), "Sort", required=False, default="new")
    page = f.int("page", "Page", lo=1, hi=10000, required=False, default=1)
    per = f.int("per_page", "Per page", lo=1, hi=50, required=False, default=20)
    f.done()
    result = catalog(q, cat, lo, hi, sort).paginate(page=page, per_page=per, error_out=False)
    return {"items": [product_json(p) for p in result.items], "page": page, "pages": result.pages,
            "total": result.total}


@bp.get("/products/<int:pid>")
def product(pid):
    return product_json(visible_product(pid))


# ---------- cart (customer) ----------

@bp.get("/cart")
@require("customer")
def cart():
    return cart_json(g.user)


@bp.post("/cart")
@require("customer")
def cart_add():
    f = Form(json_body())
    pid, qty = f.int("product_id", "Product", lo=1), f.int("qty", "Quantity", lo=1, hi=99)
    f.done()
    add_to_cart(g.user, pid, qty)
    return cart_json(g.user), 201


@bp.patch("/cart/<int:pid>")
@require("customer")
def cart_set(pid):
    f = Form(json_body())
    qty = f.int("qty", "Quantity", lo=0, hi=99)
    f.done()
    set_cart_qty(g.user, pid, qty)
    return cart_json(g.user)


@bp.delete("/cart/<int:pid>")
@require("customer")
def cart_remove(pid):
    set_cart_qty(g.user, pid, 0)
    return "", 204


# ---------- shipping & checkout ----------

@bp.post("/shipping/rates")
def rates():
    """Quote UPS rates from 110 Inner Campus Drive, Austin, TX 78705.

    Body: {"zip": "10001", "residential": true, "items": [{"product_id": 1, "qty": 2}]}
    `items` is optional for signed-in customers (defaults to their cart); anonymous callers must send it.
    """
    body = json_body()
    f = Form(body)
    zip_code = f.zip()
    residential = body.get("residential", True)
    if not isinstance(residential, bool):
        f.errors["residential"] = "Residential must be true or false."
    items = body.get("items")
    if items is not None and (not isinstance(items, list) or not 1 <= len(items) <= 50):
        f.errors["items"] = "Items must be a list of 1-50 {product_id, qty} objects."
        items = None
    lines = []
    for n, it in enumerate(items or []):
        sub = Form(it if isinstance(it, dict) else {})
        pid, qty = sub.int("product_id", "Product", lo=1), sub.int("qty", "Quantity", lo=1, hi=99)
        if sub.errors:
            f.errors[f"items[{n}]"] = " ".join(sub.errors.values())
        else:
            lines.append((pid, qty))
    f.done()
    if items is None:
        if g.user is None:
            abort(401, "Sign in to quote your cart, or send an explicit `items` list.")
        if g.user.role != "customer":
            abort(403, "Only customers have carts; send an explicit `items` list.")
        pairs = [(c.product, c.qty) for c in cart_lines(g.user)]
        if not pairs:
            abort(409, "Your cart is empty.")
    else:
        pairs = [(visible_product(pid), qty) for pid, qty in lines]
    quote = shipping_quote(zip_code, pairs, residential)
    subtotal = sum(p.price_cents * q for p, q in pairs)
    quote["subtotal"] = subtotal / 100
    quote["tax"] = round(subtotal * setting("tax_rate_pct") / 100) / 100
    quote["fuel_surcharge_pct"] = setting("fuel_surcharge_pct")
    return quote


@bp.post("/checkout")
@require("customer")
def checkout():
    """Body: {"name", "street", "city", "state", "zip", "service": "GND"|"3DS"|"2DA"|"1DA"}."""
    f = Form(json_body())
    addr = f.address()
    service = f.choice("service", list(shipping.RATES), "Shipping service")
    f.done()
    order = place_order(g.user, addr, service)
    return order_json(order), 201


# ---------- orders ----------

@bp.get("/orders")
@require("customer")
def orders():
    rows = Order.query.filter_by(user_id=g.user.id).order_by(Order.id.desc()).limit(100).all()
    return {"items": [order_json(o) for o in rows]}


@bp.get("/orders/<int:oid>")
@require()
def order(oid):
    return order_json(*order_for_viewer(oid))


@bp.post("/orders/<int:oid>/cancel")
@require("customer")
def cancel(oid):
    o, _ = order_for_viewer(oid)
    if not o.cancellable:
        abort(409, "This order has shipped items and can't be cancelled; request a return instead.")
    for i in o.items:
        if i.status == "pending":
            set_item_status(i, "cancelled", "customer")
    db.session.commit()
    return order_json(o)


@bp.post("/order-items/<int:iid>/return")
@require("customer")
def request_return(iid):
    """Body: {"reason": "..."}; item must be delivered and inside the return window."""
    item = change_item(iid, "return_requested", json_body())
    return order_json(item.order)


# ---------- assistant ----------

@bp.post("/chat")
def chat():
    """Body: {"messages": [{"role": "user"|"assistant", "content": "..."}]} (last must be the user's)."""
    rate_limit("chat", 20, 60)
    msgs = json_body().get("messages")
    ok = (isinstance(msgs, list) and 1 <= len(msgs) <= 30
          and all(isinstance(m, dict) and m.get("role") in ("user", "assistant")
                  and isinstance(m.get("content"), str) and 0 < len(m["content"].strip()) <= 2000 for m in msgs)
          and msgs[0]["role"] == msgs[-1]["role"] == "user"
          and all(a["role"] != b["role"] for a, b in zip(msgs, msgs[1:])))
    if not ok:
        return jsonify(error="validation_failed", fields={"messages": (
            "Send 1-30 alternating user/assistant messages of 1-2000 characters, ending with a user message.")}), 400
    return chatbot.reply([{"role": m["role"], "content": m["content"].strip()} for m in msgs], g.user)

