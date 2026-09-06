import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "marketplace.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ORIGIN = "110 Inner Campus Drive, Austin, TX 78705"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("MARKETPLACE_SECRET", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('customer', 'seller', 'admin')),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL REFERENCES stores(id),
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            inventory INTEGER NOT NULL DEFAULT 0 CHECK(inventory >= 0),
            category TEXT NOT NULL,
            image_url TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS carts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS cart_items (
            cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            PRIMARY KEY(cart_id, product_id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'paid',
            subtotal REAL NOT NULL,
            shipping REAL NOT NULL,
            total REAL NOT NULL,
            address TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id),
            seller_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            seller_id INTEGER REFERENCES users(id),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        now = datetime.utcnow().isoformat(timespec="seconds")
        users = [
            ("Avery Customer", "customer@example.com", "customer", "customer"),
            ("Northstar Seller", "seller@example.com", "seller", "seller"),
            ("Platform Admin", "admin@example.com", "admin", "admin"),
        ]
        for name, email, role, password in users:
            connection.execute(
                "INSERT INTO users(name, email, password, role, created_at) VALUES(?,?,?,?,?)",
                (name, email, generate_password_hash(password), role, now),
            )
        seller_id = connection.execute("SELECT id FROM users WHERE role='seller'").fetchone()[0]
        store_id = connection.execute(
            "INSERT INTO stores(seller_id, name, description) VALUES(?,?,?) RETURNING id",
            (seller_id, "Northstar Supply", "Useful objects for work, travel, and everyday rituals."),
        ).fetchone()[0]
        products = [
            (store_id, "Field Notes Journal", "A tactile notebook for ideas that deserve a place to land.", 18.0, 42, "Stationery", "https://images.unsplash.com/photo-1517842645767-c639042777db?w=900"),
            (store_id, "Ceramic Travel Mug", "Hand-finished stoneware with a secure silicone lid.", 32.0, 18, "Home", "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=900"),
            (store_id, "Everyday Carry Tote", "Heavy canvas tote with a reinforced shoulder strap.", 46.0, 11, "Bags", "https://images.unsplash.com/photo-1594223274512-ad4803739b7c?w=900"),
        ]
        connection.executemany(
            "INSERT INTO products(store_id,name,description,price,inventory,category,image_url,created_at) VALUES(?,?,?,?,?,?,?,?)",
            [(a, b, c, d, e, f, g, now) for a, b, c, d, e, f, g in products],
        )
    connection.commit()
    connection.close()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    connection = db()
    user = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    connection.close()
    return user


def require_auth(*roles):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify(error="Authentication required."), 401
            if not user["active"]:
                session.clear()
                return jsonify(error="This account is deactivated."), 403
            if roles and user["role"] not in roles:
                return jsonify(error="You are not authorized for this action."), 403
            return function(user, *args, **kwargs)

        return wrapped

    return decorator


def json_body(required=()):
    payload = request.get_json(silent=True) or {}
    missing = [key for key in required if not str(payload.get(key, "")).strip()]
    if missing:
        return None, (jsonify(error=f"Missing required fields: {', '.join(missing)}."), 400)
    return payload, None


def product_query(search="", category=""):
    connection = db()
    products = connection.execute(
        """SELECT p.*, s.name AS store_name, s.seller_id
           FROM products p JOIN stores s ON s.id=p.store_id
           WHERE p.active=1 AND (?='' OR p.name LIKE ? OR p.description LIKE ?)
             AND (?='' OR p.category=?) ORDER BY p.created_at DESC""",
        (search, f"%{search}%", f"%{search}%", category, category),
    ).fetchall()
    connection.close()
    return [dict(product) for product in products]


@app.get("/")
def home():
    return render_template("index.html", user=current_user(), products=product_query())


@app.get("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("home"))
    return render_template("dashboard.html", user=user)


@app.get("/api/products")
def products_api():
    return jsonify(products=product_query(request.args.get("q", "").strip(), request.args.get("category", "").strip()))


@app.post("/api/auth/register")
def register():
    payload, error = json_body(("name", "email", "password"))
    if error:
        return error
    if len(payload["password"]) < 8:
        return jsonify(error="Password must be at least 8 characters."), 400
    role = payload.get("role", "customer")
    if role not in ("customer", "seller"):
        return jsonify(error="New accounts may only be customer or seller accounts."), 400
    connection = db()
    try:
        cursor = connection.execute(
            "INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
            (payload["name"].strip(), payload["email"].strip().lower(), generate_password_hash(payload["password"]), role, datetime.utcnow().isoformat(timespec="seconds")),
        )
        if role == "seller":
            connection.execute("INSERT INTO stores(seller_id,name) VALUES(?,?)", (cursor.lastrowid, f"{payload['name'].strip()}'s Store"))
        connection.commit()
    except sqlite3.IntegrityError:
        connection.close()
        return jsonify(error="An account with that email already exists."), 409
    connection.close()
    return jsonify(message="Account created. Please sign in."), 201


@app.post("/api/auth/login")
def login():
    payload, error = json_body(("email", "password"))
    if error:
        return error
    connection = db()
    user = connection.execute("SELECT * FROM users WHERE email=?", (payload["email"].strip().lower(),)).fetchone()
    connection.close()
    if not user or not check_password_hash(user["password"], payload["password"]):
        return jsonify(error="Invalid email or password."), 401
    if not user["active"]:
        return jsonify(error="This account is deactivated."), 403
    session["user_id"] = user["id"]
    return jsonify(user={"id": user["id"], "name": user["name"], "role": user["role"]})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(message="Signed out.")


@app.get("/api/me")
def me():
    user = current_user()
    return jsonify(user=dict(user) if user else None)


@app.get("/api/cart")
@require_auth("customer")
def cart(user):
    connection = db()
    rows = connection.execute(
        """SELECT ci.product_id, ci.quantity, p.name, p.price, p.inventory, p.image_url
           FROM cart_items ci JOIN carts c ON c.id=ci.cart_id JOIN products p ON p.id=ci.product_id
           WHERE c.user_id=?""", (user["id"],),
    ).fetchall()
    connection.close()
    items = [dict(row) for row in rows]
    return jsonify(items=items, subtotal=round(sum(item["price"] * item["quantity"] for item in items), 2))


@app.post("/api/cart")
@require_auth("customer")
def add_to_cart(user):
    payload, error = json_body(("product_id",))
    if error:
        return error
    try:
        product_id = int(payload["product_id"])
        quantity = int(payload.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify(error="product_id and quantity must be whole numbers."), 400
    if quantity < 1 or quantity > 20:
        return jsonify(error="Quantity must be between 1 and 20."), 400
    connection = db()
    product = connection.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if not product:
        connection.close()
        return jsonify(error="Product not found."), 404
    if product["inventory"] < quantity:
        connection.close()
        return jsonify(error="That quantity is not currently in stock."), 409
    cart_row = connection.execute("SELECT id FROM carts WHERE user_id=?", (user["id"],)).fetchone()
    if not cart_row:
        cart_id = connection.execute("INSERT INTO carts(user_id) VALUES(?) RETURNING id", (user["id"],)).fetchone()[0]
    else:
        cart_id = cart_row[0]
    connection.execute(
        "INSERT INTO cart_items(cart_id,product_id,quantity) VALUES(?,?,?) ON CONFLICT(cart_id,product_id) DO UPDATE SET quantity=quantity+excluded.quantity",
        (cart_id, product_id, quantity),
    )
    connection.commit()
    connection.close()
    return jsonify(message="Added to cart."), 201


@app.delete("/api/cart/<int:product_id>")
@require_auth("customer")
def remove_from_cart(user, product_id):
    connection = db()
    connection.execute("DELETE FROM cart_items WHERE product_id=? AND cart_id IN (SELECT id FROM carts WHERE user_id=?)", (product_id, user["id"]))
    connection.commit()
    connection.close()
    return jsonify(message="Cart updated.")


def shipping_rate(address, subtotal):
    text = address.lower()
    zone = 2 if "tx" in text or "austin" in text else 5
    base = 8.99 if zone == 2 else 14.99
    if subtotal >= 75:
        base = 0
    return {"carrier": "UPS", "service": "UPS Ground", "origin": ORIGIN, "zone": zone, "amount": round(base, 2), "delivery_estimate": "1-3 business days" if zone == 2 else "3-5 business days"}


@app.post("/api/checkout/rates")
@require_auth("customer")
def rates(user):
    payload, error = json_body(("address",))
    if error:
        return error
    connection = db()
    subtotal = connection.execute(
        """SELECT COALESCE(SUM(p.price * ci.quantity), 0) FROM cart_items ci
           JOIN carts c ON c.id=ci.cart_id JOIN products p ON p.id=ci.product_id WHERE c.user_id=?""", (user["id"],)
    ).fetchone()[0]
    connection.close()
    if not subtotal:
        return jsonify(error="Your cart is empty."), 400
    return jsonify(rate=shipping_rate(payload["address"].strip(), subtotal), subtotal=round(subtotal, 2), total=round(subtotal + shipping_rate(payload["address"], subtotal)["amount"], 2))


@app.post("/api/checkout")
@require_auth("customer")
def checkout(user):
    payload, error = json_body(("address",))
    if error:
        return error
    connection = db()
    items = connection.execute(
        """SELECT ci.product_id, ci.quantity, p.name, p.price, p.inventory, p.store_id, s.seller_id
           FROM cart_items ci JOIN carts c ON c.id=ci.cart_id JOIN products p ON p.id=ci.product_id
           JOIN stores s ON s.id=p.store_id WHERE c.user_id=?""", (user["id"],)
    ).fetchall()
    if not items:
        connection.close()
        return jsonify(error="Your cart is empty."), 400
    if any(item["quantity"] > item["inventory"] for item in items):
        connection.close()
        return jsonify(error="One or more items no longer have enough inventory."), 409
    subtotal = round(sum(item["price"] * item["quantity"] for item in items), 2)
    rate = shipping_rate(payload["address"], subtotal)
    order_id = connection.execute(
        "INSERT INTO orders(user_id,subtotal,shipping,total,address,created_at) VALUES(?,?,?,?,?,?) RETURNING id",
        (user["id"], subtotal, rate["amount"], subtotal + rate["amount"], payload["address"].strip(), datetime.utcnow().isoformat(timespec="seconds")),
    ).fetchone()[0]
    for item in items:
        connection.execute("INSERT INTO order_items(order_id,product_id,seller_id,name,quantity,price) VALUES(?,?,?,?,?,?)", (order_id, item["product_id"], item["seller_id"], item["name"], item["quantity"], item["price"]))
        connection.execute("UPDATE products SET inventory=inventory-? WHERE id=?", (item["quantity"], item["product_id"]))
    connection.execute("DELETE FROM cart_items WHERE cart_id IN (SELECT id FROM carts WHERE user_id=?)", (user["id"],))
    connection.commit()
    connection.close()
    return jsonify(order_id=order_id, total=round(subtotal + rate["amount"], 2), status="paid"), 201


@app.get("/api/orders")
@require_auth("customer", "seller", "admin")
def orders(user):
    connection = db()
    if user["role"] == "customer":
        rows = connection.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
    elif user["role"] == "seller":
        rows = connection.execute("SELECT DISTINCT o.* FROM orders o JOIN order_items oi ON oi.order_id=o.id WHERE oi.seller_id=? ORDER BY o.created_at DESC", (user["id"],)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    connection.close()
    return jsonify(orders=[dict(row) for row in rows])


@app.post("/api/orders/<int:order_id>/status")
@require_auth("customer", "seller", "admin")
def order_status(user, order_id):
    payload, error = json_body(("status",))
    if error:
        return error
    allowed = {"customer": {"cancelled", "return_requested"}, "seller": {"processing", "shipped", "delivered"}, "admin": {"paid", "processing", "shipped", "delivered", "cancelled", "refunded"}}
    if payload["status"] not in allowed[user["role"]]:
        return jsonify(error="That role cannot set this order status."), 403
    connection = db()
    order = connection.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        connection.close()
        return jsonify(error="Order not found."), 404
    if user["role"] == "customer" and order["user_id"] != user["id"]:
        connection.close()
        return jsonify(error="You may only update your own orders."), 403
    if user["role"] == "seller" and not connection.execute("SELECT 1 FROM order_items WHERE order_id=? AND seller_id=?", (order_id, user["id"])).fetchone():
        connection.close()
        return jsonify(error="You may only update orders containing your products."), 403
    connection.execute("UPDATE orders SET status=? WHERE id=?", (payload["status"], order_id))
    connection.commit()
    connection.close()
    return jsonify(message="Order status updated.")


@app.post("/api/chat")
@require_auth("customer", "seller", "admin")
def chat(user):
    payload, error = json_body(("message",))
    if error:
        return error
    text = payload["message"].strip()
    lower = text.lower()
    if any(word in lower for word in ("return", "refund", "cancel")):
        answer = "I can help with that. Open your order history and choose the order to request a return or cancellation. For product-specific questions, message the seller directly from the order or product conversation."
    elif any(word in lower for word in ("shipping", "delivery", "ups")):
        answer = "UPS Ground rates are calculated at checkout from our Austin origin. Orders over $75 qualify for free ground shipping, with delivery estimates shown before payment."
    elif any(word in lower for word in ("seller", "question", "product")):
        answer = "Product details are listed on each item. The seller is the best source for fit, materials, and custom questions, so use the seller message action in your dashboard."
    else:
        answer = "I can help with products, shipping, orders, returns, and seller questions. Tell me what you are trying to do, and I will point you to the right place."
    connection = db()
    connection.execute("INSERT INTO messages(user_id,body,created_at) VALUES(?,?,?)", (user["id"], text, datetime.utcnow().isoformat(timespec="seconds")))
    connection.commit()
    connection.close()
    return jsonify(answer=answer)


@app.post("/api/seller/products")
@require_auth("seller", "admin")
def create_product(user):
    payload, error = json_body(("name", "description", "price", "inventory", "category"))
    if error:
        return error
    try:
        price = float(payload["price"])
        inventory = int(payload["inventory"])
    except (TypeError, ValueError):
        return jsonify(error="price must be a number and inventory must be a whole number."), 400
    if price < 0 or inventory < 0:
        return jsonify(error="price and inventory cannot be negative."), 400
    connection = db()
    store = connection.execute("SELECT id FROM stores WHERE seller_id=?", (user["id"],)).fetchone()
    if not store:
        connection.close()
        return jsonify(error="Create a store before adding products."), 400
    connection.execute("INSERT INTO products(store_id,name,description,price,inventory,category,image_url,created_at) VALUES(?,?,?,?,?,?,?,?)", (store["id"], payload["name"].strip(), payload["description"].strip(), price, inventory, payload["category"].strip(), payload.get("image_url", "").strip(), datetime.utcnow().isoformat(timespec="seconds")))
    connection.commit()
    connection.close()
    return jsonify(message="Product created."), 201


@app.post("/api/seller/upload")
@require_auth("seller", "admin")
def upload_image(user):
    image = request.files.get("image")
    if not image or not image.filename:
        return jsonify(error="Choose an image file to upload."), 400
    allowed = {"png", "jpg", "jpeg", "webp"}
    extension = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else ""
    if extension not in allowed:
        return jsonify(error="Only PNG, JPG, JPEG, and WEBP images are accepted."), 400
    filename = f"{user['id']}_{secure_filename(image.filename)}"
    image.save(UPLOAD_DIR / filename)
    return jsonify(image_url=url_for("static", filename=f"uploads/{filename}", _external=True)), 201


@app.get("/api/admin/summary")
@require_auth("admin")
def admin_summary(user):
    connection = db()
    summary = {
        "users": connection.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "active_sellers": connection.execute("SELECT COUNT(*) FROM users WHERE role='seller' AND active=1").fetchone()[0],
        "products": connection.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0],
        "orders": connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "revenue": connection.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status NOT IN ('cancelled','refunded')").fetchone()[0],
    }
    connection.close()
    return jsonify(summary=summary)


@app.post("/api/admin/users/<int:user_id>/active")
@require_auth("admin")
def set_user_active(user, user_id):
    payload, error = json_body(("active",))
    if error:
        return error
    if payload["active"] not in (True, False, 0, 1, "0", "1"):
        return jsonify(error="active must be true or false."), 400
    connection = db()
    if not connection.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
        connection.close()
        return jsonify(error="User not found."), 404
    connection.execute("UPDATE users SET active=? WHERE id=?", (int(payload["active"] in (True, 1, "1")), user_id))
    connection.commit()
    connection.close()
    return jsonify(message="User access updated.")


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", "5000")))
