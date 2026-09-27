from datetime import datetime, timezone
from app import db

class OrderStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURN_REQUESTED = "return_requested"
    RETURNED = "returned"

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default=OrderStatus.PENDING)
    shipping_address_street = db.Column(db.String(200), nullable=False)
    shipping_address_city = db.Column(db.String(100), nullable=False)
    shipping_address_state = db.Column(db.String(2), nullable=False)
    shipping_address_zip = db.Column(db.String(10), nullable=False)
    shipping_method = db.Column(db.String(50), default="standard")
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    tracking_number = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")
    return_requests = db.relationship("ReturnRequest", backref="order", lazy=True)

    def __repr__(self):
        return f"<Order {self.order_number}>"

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    seller = db.relationship("User", foreign_keys=[seller_id])

class ReturnRequest(db.Model):
    __tablename__ = "return_requests"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending")
    admin_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime)

    customer = db.relationship("User", foreign_keys=[customer_id])
