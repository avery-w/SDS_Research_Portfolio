from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

ROLE_CUSTOMER = "customer"
ROLE_SELLER = "seller"
ROLE_ADMIN = "admin"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_CUSTOMER)
    is_active_user = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    address_line1 = db.Column(db.String(255))
    city = db.Column(db.String(120))
    state = db.Column(db.String(20))
    zip_code = db.Column(db.String(20))
    country = db.Column(db.String(60), default="US")

    store = db.relationship("Store", backref="owner", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login uses is_active as a property; we store it as is_active_user
    # to avoid clashing with UserMixin's default.
    @property
    def is_active(self):
        return self.is_active_user

    def is_admin(self):
        return self.role == ROLE_ADMIN

    def is_seller(self):
        return self.role == ROLE_SELLER

    def is_customer(self):
        return self.role == ROLE_CUSTOMER


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="store", lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    weight_oz = db.Column(db.Float, nullable=False, default=16.0)
    category = db.Column(db.String(80))
    sku = db.Column(db.String(64))
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    images = db.relationship(
        "ProductImage", backref="product", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def primary_image(self):
        for img in self.images:
            if img.is_primary:
                return img
        return self.images[0] if self.images else None


class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    items = db.relationship("CartItem", backref="cart", lazy=True, cascade="all, delete-orphan")


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    product = db.relationship("Product")


ORDER_ITEM_STATUSES = [
    "pending",
    "shipped",
    "delivered",
    "cancelled",
    "return_requested",
    "returned",
]


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    ship_name = db.Column(db.String(150))
    ship_address = db.Column(db.String(255))
    ship_city = db.Column(db.String(120))
    ship_state = db.Column(db.String(20))
    ship_zip = db.Column(db.String(20))
    ship_country = db.Column(db.String(60), default="US")

    ups_service_code = db.Column(db.String(10))
    ups_service_name = db.Column(db.String(80))
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    shipping_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")
    customer = db.relationship("User")

    @property
    def status(self):
        statuses = {item.status for item in self.items}
        if not statuses:
            return "pending"
        if statuses == {"cancelled"}:
            return "cancelled"
        if statuses == {"delivered"}:
            return "delivered"
        if statuses == {"returned"}:
            return "returned"
        if "return_requested" in statuses:
            return "return_requested"
        if "shipped" in statuses:
            return "shipped"
        return "pending"


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")

    product = db.relationship("Product")
    store = db.relationship("Store")


class ReturnRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey("order_item.id"), nullable=False, unique=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending/approved/rejected/refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order_item = db.relationship("OrderItem")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])
    product = db.relationship("Product")


class PlatformSetting(db.Model):
    """Singleton row (id=1) holding site-wide settings."""

    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(120), nullable=False, default="Marketplace")
    commission_rate_pct = db.Column(db.Float, nullable=False, default=10.0)

    @staticmethod
    def get():
        setting = PlatformSetting.query.get(1)
        if not setting:
            setting = PlatformSetting(id=1)
            db.session.add(setting)
            db.session.commit()
        return setting
