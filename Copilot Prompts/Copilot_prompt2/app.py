from __future__ import annotations

import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import Flask, g, jsonify, render_template, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "marketplace.db"))
UPLOAD_FOLDER = BASE_DIR / os.environ.get("UPLOAD_FOLDER", "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_TEXT = 500
UPS_ORIGIN = "110 Inner Campus Drive, Austin, TX 78705"

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "development-only-change-me"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    UPLOAD_FOLDER=str(UPLOAD_FOLDER),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None) -> None:
    database = g.pop("db", None)
    if database is not None:
        database.close()


def query_one(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    return get_db().execute(sql, params).fetchone()


def query_all(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return get_db().execute(sql, params).fetchall()


def parse_id(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Expected a positive integer") from exc
    if parsed <= 0:
        raise ValueError("Expected a positive integer")
    return parsed


def text_value(value: Any, *, required: bool = True, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        if required:
            raise ValueError("Expected text")
        return ""
    cleaned = value.strip()
    if required and not cleaned:
        raise ValueError("This field is required")
    if len(cleaned) > limit:
        raise ValueError(f"Text must be {limit} characters or fewer")
    return cleaned


def json_body() -> dict[str, Any]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValueError("A JSON object is required")
    return body


def row_json(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def current_user() -> sqlite3.Row | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return query_one("SELECT id, name, email, role, active FROM users WHERE id = ?", (user_id,))


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        user = current_user()
        if not user or not user["active"]:
            return jsonify(error="Authentication required"), 401
        g.user = user
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        @login_required
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if g.user["role"] not in roles:
                return jsonify(error="Insufficient permissions"), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def commit() -> None:
    get_db().commit()


def initialize_database() -> None:
    with app.app_context():
        db = get_db()
        schema = (BASE_DIR / "schema.sql").read_text(encoding="utf-8")
        db.executescript(schema)
        if query_one("SELECT id FROM users LIMIT 1"):
            return
        users = [
            ("Demo Customer", "customer@example.com", "customer", "password123"),
            ("Demo Seller", "seller@example.com", "seller", "password123"),
            ("Platform Admin", "admin@example.com", "admin", "password123"),
        ]
        for name, email, role, password in users:
            db.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(password), role),
            )
        seller_id = query_one("SELECT id FROM users WHERE email = ?", ("seller@example.com",))["id"]
        db.execute(
            "INSERT INTO stores (seller_id, name, description) VALUES (?, ?, ?)",
            (seller_id, "Field & Found", "Useful objects for desks, kitchens, and daily rituals."),
        )
        store_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        products = [
            (store_id, "Brass Desk Lamp", "A warm, adjustable light for late work and slow mornings.", "Home", 8900, 24, 36),
            (store_id, "Canvas Market Tote", "Heavyweight cotton tote with an inside pocket.", "Bags", 3200, 48, 12),
            (store_id, "Ceramic Pour-Over Set", "Hand-finished dripper and matching cup.", "Kitchen", 5400, 15, 28),
        ]
        db.executemany(
            "INSERT INTO products (store_id, name, description, category, price_cents, inventory, weight_oz) VALUES (?, ?, ?, ?, ?, ?, ?)",
            products,
        )
        commit()


def product_payload(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["price"] = item["price_cents"] / 100
    item["image_url"] = f"/uploads/{item['image_path']}" if item.get("image_path") else None
    return item


def shipping_estimate(weight_oz: float, address: str) -> dict[str, Any]:
    # Transparent UPS-style ground estimate: billable half-pound units plus a destination zone.
    normalized = address.upper()
    zone = 8 if any(state in normalized for state in ("AK", "HI")) else 5
    billable_units = max(1, int((weight_oz + 7) // 8))
    base = 8.95 + (billable_units - 1) * 0.85
    zone_fee = (zone - 2) * 0.65
    shipping_cents = round((base + zone_fee) * 100)
    return {"carrier": "UPS", "service": "Ground estimate", "origin": UPS_ORIGIN, "zone": zone, "weight_oz": round(weight_oz, 1), "shipping_cents": shipping_cents}


@app.errorhandler(413)
def too_large(_error: Any) -> tuple[Any, int]:
    return jsonify(error="Upload exceeds the 5 MiB limit"), 413


@app.errorhandler(ValueError)
def invalid_input(error: ValueError) -> tuple[Any, int]:
    return jsonify(error=str(error)), 400


@app.get("/")
def home() -> str:
    return render_template("index.html")


@app.get("/uploads/<path:filename>")
def uploaded_file(filename: str) -> Any:
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.get("/api/me")
def me() -> Any:
    return jsonify(user=row_json(current_user()))


@app.post("/api/auth/register")
def register() -> Any:
    body = json_body()
    name = text_value(body.get("name"), limit=80)
    email = text_value(body.get("email"), limit=254).lower()
    password = text_value(body.get("password"), limit=128)
    if len(password) < 8 or "@" not in email:
        raise ValueError("Use a valid email and a password of at least 8 characters")
    try:
        get_db().execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'customer')",
            (name, email, generate_password_hash(password)),
        )
        commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("An account with that email already exists") from exc
    user = query_one("SELECT id, name, email, role, active FROM users WHERE email = ?", (email,))
    session["user_id"] = user["id"]
    return jsonify(user=row_json(user)), 201


@app.post("/api/auth/login")
def login() -> Any:
    body = json_body()
    email = text_value(body.get("email"), limit=254).lower()
    password = text_value(body.get("password"), limit=128)
    user = query_one("SELECT * FROM users WHERE email = ?", (email,))
    if not user or not user["active"] or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Invalid email or password"), 401
    session.clear()
    session["user_id"] = user["id"]
    return jsonify(user={"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"], "active": user["active"]})


@app.post("/api/auth/logout")
def logout() -> Any:
    session.clear()
    return jsonify(ok=True)


@app.get("/api/products")
def products() -> Any:
    term = text_value(request.args.get("q", ""), required=False, limit=80)
    category = text_value(request.args.get("category", ""), required=False, limit=40)
    escaped = term.replace("%", "\\%").replace("_", "\\_")
    clauses = ["p.active = 1", "p.inventory > 0"]
    params: list[Any] = []
    if term:
        clauses.append("(p.name LIKE ? ESCAPE '\\' OR p.description LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%"])
    if category:
        clauses.append("p.category = ?")
        params.append(category)
    rows = query_all(
        f"SELECT p.*, s.name AS store_name, s.seller_id FROM products p JOIN stores s ON s.id = p.store_id WHERE {' AND '.join(clauses)} ORDER BY p.created_at DESC",
        tuple(params),
    )
    return jsonify(products=[product_payload(row) for row in rows])


@app.get("/api/categories")
def categories() -> Any:
    rows = query_all("SELECT DISTINCT category FROM products WHERE active = 1 ORDER BY category")
    return jsonify(categories=[row["category"] for row in rows])


@app.get("/api/cart")
@roles_required("customer")
def get_cart() -> Any:
    rows = query_all(
        "SELECT c.product_id, c.quantity, p.name, p.price_cents, p.inventory, p.weight_oz, p.image_path FROM carts c JOIN products p ON p.id = c.product_id WHERE c.user_id = ?",
        (g.user["id"],),
    )
    items = []
    for row in rows:
        item = dict(row)
        item["line_total_cents"] = item["quantity"] * item["price_cents"]
        item["image_url"] = f"/uploads/{item['image_path']}" if item.get("image_path") else None
        items.append(item)
    return jsonify(items=items)


@app.post("/api/cart")
@roles_required("customer")
def add_cart() -> Any:
    body = json_body()
    product_id = parse_id(body.get("product_id"))
    quantity = parse_id(body.get("quantity", 1))
    product = query_one("SELECT id, inventory, active FROM products WHERE id = ?", (product_id,))
    if not product or not product["active"]:
        return jsonify(error="Product not found"), 404
    existing = query_one("SELECT quantity FROM carts WHERE user_id = ? AND product_id = ?", (g.user["id"], product_id))
    new_quantity = quantity + (existing["quantity"] if existing else 0)
    if new_quantity > product["inventory"]:
        raise ValueError("Requested quantity exceeds inventory")
    get_db().execute(
        "INSERT INTO carts (user_id, product_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = excluded.quantity",
        (g.user["id"], product_id, new_quantity),
    )
    commit()
    return get_cart()


@app.patch("/api/cart")
@roles_required("customer")
def update_cart() -> Any:
    body = json_body()
    product_id = parse_id(body.get("product_id"))
    quantity = parse_id(body.get("quantity"))
    product = query_one("SELECT inventory FROM products WHERE id = ?", (product_id,))
    if not product or quantity > product["inventory"]:
        raise ValueError("Requested quantity exceeds inventory")
    get_db().execute("UPDATE carts SET quantity = ? WHERE user_id = ? AND product_id = ?", (quantity, g.user["id"], product_id))
    commit()
    return get_cart()


@app.delete("/api/cart/<int:product_id>")
@roles_required("customer")
def delete_cart(product_id: int) -> Any:
    get_db().execute("DELETE FROM carts WHERE user_id = ? AND product_id = ?", (g.user["id"], product_id))
    commit()
    return get_cart()


@app.post("/api/checkout")
@roles_required("customer")
def checkout() -> Any:
    body = json_body()
    address = text_value(body.get("shipping_address"), limit=300)
    rows = query_all(
        "SELECT c.product_id, c.quantity, p.name, p.price_cents, p.inventory, p.weight_oz, p.store_id, s.seller_id FROM carts c JOIN products p ON p.id = c.product_id JOIN stores s ON s.id = p.store_id WHERE c.user_id = ?",
        (g.user["id"],),
    )
    if not rows:
        raise ValueError("Your cart is empty")
    if any(row["quantity"] > row["inventory"] for row in rows):
        raise ValueError("One or more products no longer have enough inventory")
    subtotal = sum(row["quantity"] * row["price_cents"] for row in rows)
    weight = sum(row["quantity"] * row["weight_oz"] for row in rows)
    shipping = shipping_estimate(weight, address)
    db = get_db()
    try:
        order_cursor = db.execute(
            "INSERT INTO orders (user_id, subtotal_cents, shipping_cents, total_cents, shipping_address) VALUES (?, ?, ?, ?, ?)",
            (g.user["id"], subtotal, shipping["shipping_cents"], subtotal + shipping["shipping_cents"], address),
        )
        order_id = order_cursor.lastrowid
        for row in rows:
            db.execute(
                "INSERT INTO order_items (order_id, product_id, seller_id, name, quantity, unit_price_cents) VALUES (?, ?, ?, ?, ?, ?)",
                (order_id, row["product_id"], row["seller_id"], row["name"], row["quantity"], row["price_cents"]),
            )
            db.execute("UPDATE products SET inventory = inventory - ? WHERE id = ?", (row["quantity"], row["product_id"]))
        db.execute("DELETE FROM carts WHERE user_id = ?", (g.user["id"],))
        commit()
    except sqlite3.Error:
        db.rollback()
        raise
    return jsonify(order={"id": order_id, "subtotal_cents": subtotal, "shipping": shipping, "total_cents": subtotal + shipping["shipping_cents"]}), 201


@app.get("/api/orders")
@roles_required("customer", "admin")
def orders() -> Any:
    owner_id = g.user["id"] if g.user["role"] == "customer" else request.args.get("user_id")
    params: tuple[Any, ...] = (owner_id,) if owner_id else ()
    where = "WHERE o.user_id = ?" if owner_id else ""
    rows = query_all(f"SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id = o.user_id {where} ORDER BY o.created_at DESC", params)
    result = []
    for row in rows:
        item = dict(row)
        item["items"] = [dict(i) for i in query_all("SELECT name, quantity, unit_price_cents, seller_id FROM order_items WHERE order_id = ?", (row["id"],))]
        result.append(item)
    return jsonify(orders=result)


@app.post("/api/orders/<int:order_id>/service-request")
@roles_required("customer", "admin")
def service_request(order_id: int) -> Any:
    body = json_body()
    kind = text_value(body.get("kind"), limit=20)
    reason = text_value(body.get("reason"), limit=500)
    if kind not in {"cancellation", "return"}:
        raise ValueError("Request type must be cancellation or return")
    order = query_one("SELECT id, user_id, status FROM orders WHERE id = ?", (order_id,))
    if not order or (g.user["role"] == "customer" and order["user_id"] != g.user["id"]):
        return jsonify(error="Order not found"), 404
    get_db().execute("INSERT INTO service_requests (order_id, user_id, kind, reason) VALUES (?, ?, ?, ?)", (order_id, order["user_id"], kind, reason))
    commit()
    return jsonify(ok=True), 201


@app.get("/api/seller/products")
@roles_required("seller", "admin")
def seller_products() -> Any:
    seller_id = g.user["id"] if g.user["role"] == "seller" else request.args.get("seller_id")
    rows = query_all("SELECT p.*, s.name AS store_name FROM products p JOIN stores s ON s.id = p.store_id WHERE s.seller_id = ? ORDER BY p.created_at DESC", (seller_id,))
    return jsonify(products=[product_payload(row) for row in rows])


@app.post("/api/seller/products")
@roles_required("seller")
def create_product() -> Any:
    body = json_body()
    name = text_value(body.get("name"), limit=120)
    description = text_value(body.get("description", ""), required=False)
    category = text_value(body.get("category", "General"), limit=40)
    price_cents = parse_id(body.get("price_cents"))
    inventory = int(body.get("inventory", 0))
    weight_oz = float(body.get("weight_oz", 16))
    if inventory < 0 or weight_oz <= 0:
        raise ValueError("Inventory and weight must be valid positive values")
    store = query_one("SELECT id FROM stores WHERE seller_id = ?", (g.user["id"],))
    if not store:
        get_db().execute("INSERT INTO stores (seller_id, name) VALUES (?, ?)", (g.user["id"], f"{g.user['name']}'s store"))
        commit()
        store = query_one("SELECT id FROM stores WHERE seller_id = ?", (g.user["id"],))
    image_path = None
    upload = request.files.get("image")
    if upload and upload.filename:
        safe_name = secure_filename(upload.filename)
        extension = Path(safe_name).suffix.lower().lstrip(".")
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError("Unsupported image type")
        image_path = f"{secrets.token_hex(16)}.{extension}"
        upload.save(UPLOAD_FOLDER / image_path)
    cursor = get_db().execute(
        "INSERT INTO products (store_id, name, description, category, price_cents, inventory, weight_oz, image_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (store["id"], name, description, category, price_cents, inventory, weight_oz, image_path),
    )
    commit()
    return jsonify(product=row_json(query_one("SELECT * FROM products WHERE id = ?", (cursor.lastrowid,)))), 201


@app.patch("/api/seller/products/<int:product_id>")
@roles_required("seller", "admin")
def update_product(product_id: int) -> Any:
    body = json_body()
    product = query_one("SELECT p.id FROM products p JOIN stores s ON s.id = p.store_id WHERE p.id = ? AND s.seller_id = ?", (product_id, g.user["id"]))
    if not product and g.user["role"] != "admin":
        return jsonify(error="Product not found"), 404
    allowed = {"name": 120, "description": MAX_TEXT, "category": 40}
    updates: list[str] = []
    params: list[Any] = []
    for field, limit in allowed.items():
        if field in body:
            updates.append(f"{field} = ?")
            params.append(text_value(body[field], required=False, limit=limit))
    for field in ("price_cents", "inventory"):
        if field in body:
            value = parse_id(body[field])
            updates.append(f"{field} = ?")
            params.append(value)
    if not updates:
        raise ValueError("No editable fields supplied")
    params.append(product_id)
    get_db().execute(f"UPDATE products SET {', '.join(updates)} WHERE id = ?", tuple(params))
    commit()
    return jsonify(ok=True)


@app.get("/api/seller/orders")
@roles_required("seller", "admin")
def seller_orders() -> Any:
    seller_id = g.user["id"] if g.user["role"] == "seller" else request.args.get("seller_id")
    rows = query_all(
        "SELECT DISTINCT o.id, o.status, o.created_at, o.shipping_address, u.name AS customer_name FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN users u ON u.id = o.user_id WHERE oi.seller_id = ? ORDER BY o.created_at DESC",
        (seller_id,),
    )
    return jsonify(orders=[dict(row) for row in rows])


@app.patch("/api/seller/orders/<int:order_id>")
@roles_required("seller", "admin")
def fulfill_order(order_id: int) -> Any:
    body = json_body()
    status = text_value(body.get("status"), limit=30)
    if status not in {"processing", "shipped", "delivered", "cancelled"}:
        raise ValueError("Unsupported order status")
    owns = query_one("SELECT 1 FROM order_items WHERE order_id = ? AND seller_id = ?", (order_id, g.user["id"]))
    if not owns and g.user["role"] != "admin":
        return jsonify(error="Order not found"), 404
    get_db().execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    commit()
    return jsonify(ok=True)


@app.get("/api/messages")
@login_required
def get_messages() -> Any:
    rows = query_all(
        "SELECT m.*, sender.name AS sender_name, recipient.name AS recipient_name, p.name AS product_name FROM messages m JOIN users sender ON sender.id = m.sender_id JOIN users recipient ON recipient.id = m.recipient_id LEFT JOIN products p ON p.id = m.product_id WHERE m.sender_id = ? OR m.recipient_id = ? ORDER BY m.created_at DESC",
        (g.user["id"], g.user["id"]),
    )
    return jsonify(messages=[dict(row) for row in rows])


@app.post("/api/messages")
@login_required
def send_message() -> Any:
    body = json_body()
    recipient_id = parse_id(body.get("recipient_id"))
    message = text_value(body.get("body"), limit=1000)
    recipient = query_one("SELECT id FROM users WHERE id = ? AND active = 1", (recipient_id,))
    if not recipient:
        return jsonify(error="Recipient not found"), 404
    product_id = parse_id(body["product_id"]) if body.get("product_id") else None
    get_db().execute("INSERT INTO messages (sender_id, recipient_id, product_id, body) VALUES (?, ?, ?, ?)", (g.user["id"], recipient_id, product_id, message))
    commit()
    return jsonify(ok=True), 201


@app.post("/api/chatbot")
def chatbot() -> Any:
    body = json_body()
    message = text_value(body.get("message"), limit=600).lower()
    if any(word in message for word in ("order", "track", "shipping")):
        reply = "For order-specific help, sign in and check Order history. You can also message the seller directly from the marketplace."
    elif any(word in message for word in ("return", "refund", "cancel")):
        reply = "Open Order history to request a cancellation or return. Include the reason so the seller or admin can review it."
    elif any(word in message for word in ("seller", "merchant", "question")):
        reply = "Product questions are best answered by the seller. Sign in, open Messages, and send them the product name and your question."
    else:
        reply = "I can help with products, orders, shipping, returns, and seller messages. What would you like to know?"
    return jsonify(reply=reply)


@app.get("/api/admin/overview")
@roles_required("admin")
def admin_overview() -> Any:
    counts = {
        "users": query_one("SELECT COUNT(*) AS count FROM users")["count"],
        "sellers": query_one("SELECT COUNT(*) AS count FROM users WHERE role = 'seller'")["count"],
        "products": query_one("SELECT COUNT(*) AS count FROM products WHERE active = 1")["count"],
        "orders": query_one("SELECT COUNT(*) AS count FROM orders")["count"],
        "revenue_cents": query_one("SELECT COALESCE(SUM(total_cents), 0) AS total FROM orders WHERE status != 'cancelled'")["total"],
    }
    counts["revenue"] = counts["revenue_cents"] / 100
    return jsonify(metrics=counts, recent_orders=[dict(row) for row in query_all("SELECT id, status, total_cents, created_at FROM orders ORDER BY created_at DESC LIMIT 8")])


@app.patch("/api/admin/users/<int:user_id>")
@roles_required("admin")
def admin_user(user_id: int) -> Any:
    body = json_body()
    active = body.get("active")
    if not isinstance(active, bool):
        raise ValueError("active must be boolean")
    get_db().execute("UPDATE users SET active = ? WHERE id = ?", (int(active), user_id))
    commit()
    return jsonify(ok=True)


initialize_database()

if __name__ == "__main__":
    app.run(debug=True)
