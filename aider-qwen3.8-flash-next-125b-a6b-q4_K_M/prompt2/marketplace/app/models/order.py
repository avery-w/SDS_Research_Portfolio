from app.extensions import db
from datetime import datetime

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.Enum("pending", "confirmed", "shipped", "delivered", "cancelled", "returned", name="order_status"), default="pending")
    shipping_address = db.Column(db.String(500), nullable=False)
    shipping_cost = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    tracking_number = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    customer = db.relationship("User", foreign_keys=[customer_id], backref="customer_orders")
    seller = db.relationship("User", foreign_keys=[seller_id], backref="seller_orders")

class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    order = db.relationship("Order", backref="items")
    product = db.relationship("Product", backref="order_items")

class ReturnRequest(db.Model):
    __tablename__ = "return_requests"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum("pending", "approved", "rejected", "completed", name="return_status"), default="pending")
    admin_override = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.relationship("Order", backref="return_requests")
    customer = db.relationship("User", backref="return_requests")
