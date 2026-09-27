from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

ROLES = ("customer", "seller", "admin")
ITEM_STATUSES = ("pending", "shipped", "delivered", "cancelled",
                 "return_requested", "returned", "return_rejected")
# Items in these states have had their stock put back on the shelf.
RESTOCKED = {"cancelled", "returned"}
# Items in these states count toward revenue.
REVENUE_STATUSES = ("pending", "shipped", "delivered", "return_requested", "return_rejected")
CATEGORIES = ("Electronics", "Home", "Apparel", "Books", "Outdoors", "Beauty", "Toys", "Grocery")


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="customer")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    street = db.Column(db.String(200), default="")
    city = db.Column(db.String(100), default="")
    state = db.Column(db.String(2), default="")
    zip = db.Column(db.String(10), default="")
    created_at = db.Column(db.DateTime, default=now, index=True)

    store = db.relationship("Store", back_populates="owner", uselist=False)
    __table_args__ = (CheckConstraint(f"role IN {ROLES}"),)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.ForeignKey("user.id"), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(90), unique=True, nullable=False, index=True)
    tagline = db.Column(db.String(140), default="")
    description = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=now)

    owner = db.relationship("User", back_populates="store")
    products = db.relationship("Product", back_populates="store")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.ForeignKey("store.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(30), nullable=False, index=True)
    price_cents = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    weight_lb = db.Column(db.Float, nullable=False, default=1.0)
    length_in = db.Column(db.Float, nullable=False, default=10)
    width_in = db.Column(db.Float, nullable=False, default=8)
    height_in = db.Column(db.Float, nullable=False, default=4)
    image = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    locked = db.Column(db.Boolean, nullable=False, default=False)  # admin takedown; seller can't re-list
    created_at = db.Column(db.DateTime, default=now)

    store = db.relationship("Store", back_populates="products")
    __table_args__ = (
        CheckConstraint("stock >= 0", name="stock_nonneg"),
        CheckConstraint("price_cents > 0", name="price_pos"),
    )

    @property
    def purchasable(self):
        return self.is_active and self.store.is_active and self.store.owner.is_active


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("user.id"), nullable=False, index=True)
    product_id = db.Column(db.ForeignKey("product.id"), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    product = db.relationship("Product")
    __table_args__ = (UniqueConstraint("user_id", "product_id"), CheckConstraint("qty > 0"))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("user.id"), nullable=False, index=True)
    subtotal_cents = db.Column(db.Integer, nullable=False)
    shipping_cents = db.Column(db.Integer, nullable=False)
    tax_cents = db.Column(db.Integer, nullable=False)
    total_cents = db.Column(db.Integer, nullable=False)
    shipping_service = db.Column(db.String(40), nullable=False)
    ship_name = db.Column(db.String(100), nullable=False)
    ship_street = db.Column(db.String(200), nullable=False)
    ship_city = db.Column(db.String(100), nullable=False)
    ship_state = db.Column(db.String(2), nullable=False)
    ship_zip = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=now, index=True)

    user = db.relationship("User")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    @property
    def status(self):
        """Order status is derived from its items so the two can never disagree."""
        s = {i.status for i in self.items}
        if s <= RESTOCKED:
            return "cancelled" if "cancelled" in s else "returned"
        for st in ("return_requested", "pending", "shipped"):
            if st in s:
                return "partially shipped" if st == "pending" and "shipped" in s else st
        return "delivered"

    @property
    def cancellable(self):
        live = [i for i in self.items if i.status != "cancelled"]
        return bool(live) and all(i.status == "pending" for i in live)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.ForeignKey("order.id"), nullable=False, index=True)
    product_id = db.Column(db.ForeignKey("product.id"), nullable=False)
    store_id = db.Column(db.ForeignKey("store.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    unit_price_cents = db.Column(db.Integer, nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    tracking = db.Column(db.String(40), default="")
    return_reason = db.Column(db.String(500), default="")
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")
    store = db.relationship("Store")
    __table_args__ = (CheckConstraint(f"status IN {ITEM_STATUSES}"),)

    @property
    def line_cents(self):
        return self.unit_price_cents * self.qty


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.ForeignKey("user.id"), nullable=False, index=True)
    store_id = db.Column(db.ForeignKey("store.id"), nullable=False, index=True)
    product_id = db.Column(db.ForeignKey("product.id"))
    order_id = db.Column(db.ForeignKey("order.id"))
    subject = db.Column(db.String(140), nullable=False)
    updated_at = db.Column(db.DateTime, default=now, index=True)

    customer = db.relationship("User")
    store = db.relationship("Store")
    product = db.relationship("Product")
    messages = db.relationship("Message", order_by="Message.id", cascade="all, delete-orphan")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.ForeignKey("conversation.id"), nullable=False, index=True)
    sender_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now)
    sender = db.relationship("User")


class Setting(db.Model):
    key = db.Column(db.String(40), primary_key=True)
    value = db.Column(db.String(500), nullable=False)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.ForeignKey("user.id"))
    action = db.Column(db.String(60), nullable=False)
    detail = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=now, index=True)
    actor = db.relationship("User")


# key: (default, type, label). Admins edit these on /admin/settings.
SETTINGS = {
    "platform_name": ("Longhorn Market", str, "Platform name"),
    "announcement": ("Free UPS Ground on orders over $75 this week!", str, "Site-wide announcement (blank to hide)"),
    "tax_rate_pct": ("8.25", float, "Sales tax rate (%)"),
    "commission_pct": ("10", float, "Platform commission on seller sales (%)"),
    "fuel_surcharge_pct": ("15.5", float, "UPS fuel surcharge (%)"),
    "free_shipping_over": ("75", float, "Free UPS Ground over this subtotal ($, 0 disables)"),
    "return_window_days": ("30", int, "Return window (days after delivery)"),
    "allow_seller_signup": ("1", int, "Allow new seller sign-ups (1 = yes, 0 = no)"),
}


def setting(key):
    default, typ, _ = SETTINGS[key]
    row = db.session.get(Setting, key)
    return typ(row.value if row else default)
