from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, update

db = SQLAlchemy()

ROLES = ("customer", "seller", "admin")
STATUSES = ("placed", "shipped", "delivered", "return_requested", "returned", "cancelled")
TERMINAL = ("returned", "cancelled")
REVENUE_STATUSES = ("placed", "shipped", "delivered", "return_requested")

# Who may move an order from one status to another. Admins may move any non-terminal order anywhere.
TRANSITIONS = {
    "customer": {"placed": {"cancelled"}, "delivered": {"return_requested"}},
    "seller": {
        "placed": {"shipped", "cancelled"},
        "shipped": {"delivered"},
        "return_requested": {"returned", "delivered"},  # delivered = return denied
    },
}


def now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="customer")
    active = db.Column(db.Boolean, nullable=False, default=True)
    street = db.Column(db.String(200), default="")
    city = db.Column(db.String(100), default="")
    state = db.Column(db.String(2), default="")
    zip = db.Column(db.String(5), default="")
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    store = db.relationship("Store", back_populates="owner", uselist=False)
    __table_args__ = (CheckConstraint(f"role IN {ROLES}"),)

    @property
    def is_active(self):
        return self.active


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    owner = db.relationship("User", back_populates="store")
    products = db.relationship("Product", back_populates="store")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    price_cents = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    weight_lb = db.Column(db.Float, nullable=False)
    length_in = db.Column(db.Float, nullable=False)
    width_in = db.Column(db.Float, nullable=False)
    height_in = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(64))  # generated filename in static/uploads, never user supplied
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    store = db.relationship("Store", back_populates="products")
    __table_args__ = (
        CheckConstraint("price_cents >= 0"),
        CheckConstraint("stock >= 0"),
        CheckConstraint("weight_lb > 0"),
    )

    @property
    def package(self):
        return (self.weight_lb, self.length_in, self.width_in, self.height_in)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="placed")
    subtotal_cents = db.Column(db.Integer, nullable=False)
    shipping_cents = db.Column(db.Integer, nullable=False)
    total_cents = db.Column(db.Integer, nullable=False)
    ship_service = db.Column(db.String(20), nullable=False)
    ship_name = db.Column(db.String(100), nullable=False)
    ship_street = db.Column(db.String(200), nullable=False)
    ship_city = db.Column(db.String(100), nullable=False)
    ship_state = db.Column(db.String(2), nullable=False)
    ship_zip = db.Column(db.String(5), nullable=False)
    tracking = db.Column(db.String(40), default="")
    return_reason = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime(timezone=True), default=now, index=True)
    customer = db.relationship("User")
    store = db.relationship("Store")
    items = db.relationship("OrderItem", back_populates="order")
    __table_args__ = (CheckConstraint(f"status IN {STATUSES}"),)

    def allowed_statuses(self, role):
        if role == "admin":
            return set() if self.status in TERMINAL else set(STATUSES) - {self.status}
        return TRANSITIONS.get(role, {}).get(self.status, set())

    def change_status(self, new, role):
        if new not in self.allowed_statuses(role):
            raise ValueError(f"Cannot change order from {self.status} to {new}.")
        if new in TERMINAL:  # put the units back on the shelf
            for item in self.items:
                db.session.execute(
                    update(Product).where(Product.id == item.product_id)
                    .values(stock=Product.stock + item.quantity)
                )
        self.status = new


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)  # snapshot at purchase time
    price_cents = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")
    __table_args__ = (CheckConstraint("quantity > 0"),)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))
    body = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])
    product = db.relationship("Product")


class Setting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), nullable=False)


DEFAULT_SETTINGS = {
    "site_name": "Longhorn Market",
    "commission_pct": "10",
    "fuel_surcharge_pct": "15",
    "chatbot_enabled": "1",
}


def get_setting(key):
    row = db.session.get(Setting, key)
    return row.value if row else DEFAULT_SETTINGS[key]
