"""MarketSquare: a secure Flask marketplace reference application."""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, func
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    name = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
    store = db.relationship("Store", back_populates="seller", uselist=False)


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    active = db.Column(db.Boolean, default=True, nullable=False)
    seller = db.relationship("User", back_populates="store")
    products = db.relationship("Product", back_populates="store", cascade="all,delete-orphan")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    price_cents = db.Column(db.Integer, nullable=False)
    inventory = db.Column(db.Integer, nullable=False, default=0)
    image_path = db.Column(db.String(255), default="")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
    store = db.relationship("Store", back_populates="products")
    __table_args__ = (CheckConstraint("price_cents >= 0"), CheckConstraint("inventory >= 0"))


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship("Product")
    __table_args__ = (db.UniqueConstraint("customer_id", "product_id"), CheckConstraint("quantity > 0"))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    status = db.Column(db.String(30), default="pending", nullable=False)
    subtotal_cents = db.Column(db.Integer, nullable=False)
    shipping_cents = db.Column(db.Integer, nullable=False)
    tax_cents = db.Column(db.Integer, nullable=False)
    total_cents = db.Column(db.Integer, nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
    items = db.relationship("OrderItem", cascade="all,delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_cents = db.Column(db.Integer, nullable=False)
    fulfillment_status = db.Column(db.String(30), default="unfulfilled", nullable=False)


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
    messages = db.relationship("Message", cascade="all,delete-orphan")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)


def money(cents):
    return f"${cents / 100:.2f}"


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", secrets.token_urlsafe(32)),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'marketplace.db'}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        UPLOAD_FOLDER=os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads")),
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    limiter = Limiter(key_func=get_remote_address, app=app, default_limits=["300 per hour"])

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:"
        return response

    @app.template_filter("money")
    def money_filter(cents):
        return money(cents)

    def current_user():
        user_id = session.get("user_id")
        return db.session.get(User, user_id) if user_id else None

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user or not user.active:
                return jsonify(error="authentication_required"), 401
            return view(user, *args, **kwargs)
        return wrapped

    def roles(*allowed):
        def decorator(view):
            @wraps(view)
            @login_required
            def wrapped(user, *args, **kwargs):
                if user.role not in allowed:
                    return jsonify(error="forbidden"), 403
                return view(user, *args, **kwargs)
            return wrapped
        return decorator

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/csrf")
    def csrf_token():
        session.setdefault("csrf", secrets.token_urlsafe(24))
        return jsonify(token=session["csrf"])

    @app.before_request
    def csrf_protection():
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.path.startswith("/api/"):
            if request.path in {"/api/auth/register", "/api/auth/login", "/api/shipping/quote", "/api/chatbot"}:
                return None
            if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), session.get("csrf", "")):
                return jsonify(error="csrf_failed"), 400
        return None

    @app.post("/api/auth/register")
    @limiter.limit("10 per hour")
    def register():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))
        name = str(data.get("name", "")).strip()
        role = data.get("role", "customer")
        if role not in {"customer", "seller"} or len(password) < 12 or "@" not in email or not name:
            return jsonify(error="valid name, email and a password of at least 12 characters are required"), 400
        if db.session.scalar(db.select(User).where(User.email == email)):
            return jsonify(error="email_unavailable"), 409
        user = User(email=email, name=name, role=role, password_hash=generate_password_hash(password))
        db.session.add(user)
        if role == "seller":
            user.store = Store(name=f"{name}'s Store")
        db.session.commit()
        session.clear()
        session["user_id"] = user.id
        session["csrf"] = secrets.token_urlsafe(24)
        return jsonify(user={"id": user.id, "name": user.name, "role": user.role}), 201

    @app.post("/api/auth/login")
    @limiter.limit("10 per minute")
    def login():
        data = request.get_json(silent=True) or {}
        user = db.session.scalar(db.select(User).where(User.email == str(data.get("email", "")).lower()))
        if not user or not user.active or not check_password_hash(user.password_hash, str(data.get("password", ""))):
            return jsonify(error="invalid_credentials"), 401
        session.clear()
        session["user_id"] = user.id
        session["csrf"] = secrets.token_urlsafe(24)
        return jsonify(user={"id": user.id, "name": user.name, "role": user.role}, csrf=session["csrf"])

    @app.post("/api/auth/logout")
    @login_required
    def logout(user):
        session.clear()
        return jsonify(ok=True)

    @app.get("/api/me")
    @login_required
    def me(user):
        return jsonify(id=user.id, email=user.email, name=user.name, role=user.role, active=user.active)

    @app.get("/api/products")
    def products():
        query = str(request.args.get("q", "")).strip()
        stmt = db.select(Product).join(Store).where(Product.active.is_(True), Store.active.is_(True))
        if query:
            stmt = stmt.where((Product.name.ilike(f"%{query}%")) | (Product.description.ilike(f"%{query}%")))
        result = db.session.scalars(stmt.order_by(Product.created_at.desc()).limit(100)).all()
        return jsonify(products=[product_json(p) for p in result])

    @app.post("/api/seller/products")
    @roles("seller", "admin")
    def create_product(user):
        store = user.store if user.role == "seller" else db.session.get(Store, request.json.get("store_id"))
        data = request.get_json(silent=True) or {}
        try:
            price = int(Decimal(str(data["price"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)
            inventory = int(data["inventory"])
        except (KeyError, ValueError, TypeError, ArithmeticError):
            return jsonify(error="price and integer inventory are required"), 400
        if not store or price < 0 or inventory < 0:
            return jsonify(error="invalid store or product values"), 400
        product = Product(store_id=store.id, name=str(data.get("name", "")).strip(), description=str(data.get("description", "")), price_cents=price, inventory=inventory)
        if not product.name:
            return jsonify(error="name_required"), 400
        db.session.add(product)
        db.session.commit()
        return jsonify(product=product_json(product)), 201

    @app.post("/api/seller/products/<int:product_id>/image")
    @roles("seller", "admin")
    def upload_image(user, product_id):
        product = db.session.get(Product, product_id)
        if not product or (user.role == "seller" and product.store.seller_id != user.id):
            return jsonify(error="not_found"), 404
        image = request.files.get("image")
        allowed = {"png", "jpg", "jpeg", "webp"}
        if not image or "." not in image.filename or image.filename.rsplit(".", 1)[1].lower() not in allowed:
            return jsonify(error="png, jpg, jpeg, or webp image required"), 400
        filename = f"{secrets.token_hex(16)}.{secure_filename(image.filename).rsplit('.', 1)[-1].lower()}"
        image.save(Path(app.config["UPLOAD_FOLDER"]) / filename)
        product.image_path = filename
        db.session.commit()
        return jsonify(image=filename)

    @app.post("/api/cart/items")
    @roles("customer")
    def add_cart_item(user):
        data = request.get_json(silent=True) or {}
        product = db.session.get(Product, data.get("product_id"))
        quantity = int(data.get("quantity", 0)) if str(data.get("quantity", "")).isdigit() else 0
        if not product or not product.active or quantity < 1 or quantity > product.inventory:
            return jsonify(error="product unavailable or quantity exceeds inventory"), 400
        item = db.session.scalar(db.select(CartItem).where(CartItem.customer_id == user.id, CartItem.product_id == product.id))
        if item:
            if item.quantity + quantity > product.inventory:
                return jsonify(error="quantity_exceeds_inventory"), 400
            item.quantity += quantity
        else:
            db.session.add(CartItem(customer_id=user.id, product_id=product.id, quantity=quantity))
        db.session.commit()
        return jsonify(ok=True)

    @app.get("/api/cart")
    @roles("customer")
    def get_cart(user):
        items = db.session.scalars(db.select(CartItem).where(CartItem.customer_id == user.id)).all()
        return jsonify(items=[{"id": i.id, "quantity": i.quantity, "product": product_json(i.product)} for i in items])

    @app.post("/api/shipping/quote")
    def shipping_quote():
        data = request.get_json(silent=True) or {}
        try:
            weight = max(1, float(data.get("weight_lb", 1)))
            length, width, height = [max(1, float(data.get(k, 10))) for k in ("length_in", "width_in", "height_in")]
            destination_zip = str(data["destination_zip"])
            if len(destination_zip) < 5 or not destination_zip[:5].isdigit():
                raise ValueError
        except (KeyError, ValueError, TypeError):
            return jsonify(error="weight, dimensions, and a destination ZIP code are required"), 400
        dimensional_weight = (length * width * height) / 139
        billable = max(weight, dimensional_weight)
        zone = 2 + min(6, abs(int(destination_zip[:3]) - 787) // 100)
        base = 850 + (zone * 115) + (max(0, billable - 1) * 70)
        return jsonify(origin="110 Inner Campus Drive, Austin, TX 78705", carrier="UPS", service="Ground", billable_weight_lb=round(billable, 2), zone=zone, shipping_cents=round(base), shipping=money(round(base)), note="Estimate based on UPS-style dimensional weight and zone rules; use UPS API credentials for a live quote.")

    @app.post("/api/checkout")
    @roles("customer")
    def checkout(user):
        data = request.get_json(silent=True) or {}
        address = str(data.get("shipping_address", "")).strip()
        if len(address) < 10:
            return jsonify(error="shipping_address_required"), 400
        items = db.session.scalars(db.select(CartItem).where(CartItem.customer_id == user.id)).all()
        if not items:
            return jsonify(error="cart_empty"), 400
        subtotal = 0
        for item in items:
            if not item.product.active or item.quantity > item.product.inventory:
                return jsonify(error=f"inventory_unavailable_for_{item.product.id}"), 409
            subtotal += item.product.price_cents * item.quantity
        shipping = int(data.get("shipping_cents", 1090))
        tax = round(subtotal * 0.0825)
        order = Order(customer_id=user.id, status="paid", subtotal_cents=subtotal, shipping_cents=shipping, tax_cents=tax, total_cents=subtotal + shipping + tax, shipping_address=address)
        db.session.add(order)
        for item in items:
            item.product.inventory -= item.quantity
            order.items.append(OrderItem(product_id=item.product_id, seller_id=item.product.store.seller_id, product_name=item.product.name, quantity=item.quantity, unit_price_cents=item.product.price_cents))
            db.session.delete(item)
        db.session.commit()
        return jsonify(order=order_json(order)), 201

    @app.get("/api/orders")
    @login_required
    def orders(user):
        if user.role == "admin":
            result = db.session.scalars(db.select(Order).order_by(Order.created_at.desc()).limit(200)).all()
        elif user.role == "seller":
            result = db.session.scalars(db.select(Order).join(OrderItem).where(OrderItem.seller_id == user.id).distinct()).all()
        else:
            result = db.session.scalars(db.select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc())).all()
        return jsonify(orders=[order_json(o, user) for o in result])

    @app.post("/api/orders/<int:order_id>/cancel")
    @roles("customer", "admin")
    def cancel_order(user, order_id):
        order = db.session.get(Order, order_id)
        if not order or (user.role == "customer" and order.customer_id != user.id):
            return jsonify(error="not_found"), 404
        if order.status not in {"pending", "paid"} and user.role != "admin":
            return jsonify(error="order_cannot_be_cancelled"), 409
        order.status = "cancelled"
        if user.role == "admin" or order.customer_id == user.id:
            for item in order.items:
                product = db.session.get(Product, item.product_id)
                if product:
                    product.inventory += item.quantity
        db.session.commit()
        return jsonify(order=order_json(order))

    @app.post("/api/seller/orders/<int:order_id>/fulfill")
    @roles("seller", "admin")
    def fulfill_order(user, order_id):
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify(error="not_found"), 404
        owned = [item for item in order.items if user.role == "admin" or item.seller_id == user.id]
        if not owned:
            return jsonify(error="forbidden"), 403
        for item in owned:
            item.fulfillment_status = "fulfilled"
        order.status = "fulfilled" if all(i.fulfillment_status == "fulfilled" for i in order.items) else "partially_fulfilled"
        db.session.commit()
        return jsonify(order=order_json(order))

    @app.post("/api/conversations")
    @roles("customer")
    def create_conversation(user):
        data = request.get_json(silent=True) or {}
        product = db.session.get(Product, data.get("product_id"))
        if not product:
            return jsonify(error="product_not_found"), 404
        conversation = Conversation(customer_id=user.id, seller_id=product.store.seller_id, product_id=product.id)
        db.session.add(conversation)
        db.session.commit()
        return jsonify(conversation_id=conversation.id, seller_id=conversation.seller_id), 201

    @app.post("/api/conversations/<int:conversation_id>/messages")
    @login_required
    def send_message(user, conversation_id):
        conversation = db.session.get(Conversation, conversation_id)
        if not conversation or user.id not in {conversation.customer_id, conversation.seller_id} and user.role != "admin":
            return jsonify(error="not_found"), 404
        body = str((request.get_json(silent=True) or {}).get("body", "")).strip()
        if not body or len(body) > 4000:
            return jsonify(error="message_must_be_1_to_4000_characters"), 400
        message = Message(conversation_id=conversation.id, sender_id=user.id, body=body)
        db.session.add(message)
        db.session.commit()
        return jsonify(message={"id": message.id, "body": message.body, "sender_id": message.sender_id}), 201

    @app.post("/api/chatbot")
    @limiter.limit("30 per minute")
    def chatbot():
        question = str((request.get_json(silent=True) or {}).get("message", "")).strip().lower()
        if not question:
            return jsonify(error="message_required"), 400
        if any(word in question for word in ("order", "shipping", "track")):
            reply = "For order-specific help, sign in and message the seller from your order. Shipping estimates are available at checkout."
        elif any(word in question for word in ("return", "refund", "cancel")):
            reply = "Open your order history to request a return or cancel an eligible order. A seller can answer product-specific questions directly."
        else:
            reply = "I can help with products, checkout, shipping, and returns. For details about an item, message its seller directly in the marketplace."
        return jsonify(reply=reply, escalation="Message the seller directly for product or order-specific assistance.")

    @app.get("/api/admin/analytics")
    @roles("admin")
    def analytics(user):
        revenue = db.session.scalar(db.select(func.coalesce(func.sum(Order.total_cents), 0)).where(Order.status != "cancelled")) or 0
        return jsonify(users=db.session.scalar(db.select(func.count(User.id))) or 0, sellers=db.session.scalar(db.select(func.count(User.id)).where(User.role == "seller")) or 0, products=db.session.scalar(db.select(func.count(Product.id))) or 0, orders=db.session.scalar(db.select(func.count(Order.id))) or 0, revenue_cents=revenue, revenue=money(revenue))

    @app.post("/api/admin/users/<int:user_id>/deactivate")
    @roles("admin")
    def deactivate_user(user, user_id):
        target = db.session.get(User, user_id)
        if not target or target.id == user.id:
            return jsonify(error="user_not_found_or_self"), 404
        target.active = False
        db.session.commit()
        return jsonify(ok=True)

    with app.app_context():
        db.create_all()
        seed_admin(app)
    return app


def product_json(product):
    return {"id": product.id, "store_id": product.store_id, "store": product.store.name, "name": product.name, "description": product.description, "price_cents": product.price_cents, "price": money(product.price_cents), "inventory": product.inventory, "image": product.image_path}


def order_json(order, viewer=None):
    items = order.items if not viewer or viewer.role != "seller" else [i for i in order.items if i.seller_id == viewer.id]
    return {"id": order.id, "status": order.status, "subtotal": money(order.subtotal_cents), "shipping": money(order.shipping_cents), "tax": money(order.tax_cents), "total": money(order.total_cents), "shipping_address": order.shipping_address, "items": [{"product": i.product_name, "quantity": i.quantity, "unit_price": money(i.unit_price_cents), "fulfillment_status": i.fulfillment_status} for i in items]}


def seed_admin(app):
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if email and password and not db.session.scalar(db.select(User).where(User.email == email.lower())):
        db.session.add(User(email=email.lower(), password_hash=generate_password_hash(password), name="Platform Admin", role="admin"))
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
