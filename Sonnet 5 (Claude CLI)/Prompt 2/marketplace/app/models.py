from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager

ROLES = ("customer", "seller", "admin")
ORDER_STATUSES = ("pending", "paid", "shipped", "delivered", "cancelled", "returned")
ITEM_STATUSES = ("fulfilled", "cancelled", "return_requested", "returned")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    store = db.relationship("Store", backref="seller", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login uses this to gate login for deactivated accounts
    @property
    def is_active(self):
        return self.is_active_account


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="store", cascade="all, delete-orphan")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    price_cents = db.Column(db.Integer, nullable=False)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    weight_oz = db.Column(db.Float, nullable=False, default=8.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    images = db.relationship("ProductImage", backref="product", cascade="all, delete-orphan")

    @property
    def price(self):
        return self.price_cents / 100


class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    product = db.relationship("Product")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")

    ship_name = db.Column(db.String(150), nullable=False)
    ship_line1 = db.Column(db.String(255), nullable=False)
    ship_city = db.Column(db.String(100), nullable=False)
    ship_state = db.Column(db.String(2), nullable=False)
    ship_zip = db.Column(db.String(10), nullable=False)

    shipping_service = db.Column(db.String(20), default="ground")
    shipping_cost_cents = db.Column(db.Integer, default=0)
    subtotal_cents = db.Column(db.Integer, default=0)
    total_cents = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    customer = db.relationship("User")

    @property
    def total(self):
        return self.total_cents / 100


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_cents_at_purchase = db.Column(db.Integer, nullable=False)
    item_status = db.Column(db.String(20), nullable=False, default="fulfilled")

    product = db.relationship("Product")
    store = db.relationship("Store")


class Message(db.Model):
    """Direct customer <-> seller messages (keeps buyers off the AI bot for real questions)."""

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])


class PlatformSetting(db.Model):
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(500), nullable=False)
