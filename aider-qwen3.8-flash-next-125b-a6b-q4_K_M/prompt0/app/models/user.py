from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class UserRole:
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.CUSTOMER)
    is_active_account = db.Column(db.Boolean, default=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20))
    address_street = db.Column(db.String(200))
    address_city = db.Column(db.String(100))
    address_state = db.Column(db.String(2))
    address_zip = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    store = db.relationship("Store", backref="owner", uselist=False, lazy=True)
    cart = db.relationship("Cart", backref="user", uselist=False, lazy=True)
    orders = db.relationship("Order", backref="customer", lazy=True)
    messages_sent = db.relationship("Message", foreign_keys="Message.sender_id", backref="sender", lazy=True)
    messages_received = db.relationship("Message", foreign_keys="Message.recipient_id", backref="recipient", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_seller(self):
        return self.role == UserRole.SELLER

    @property
    def is_customer(self):
        return self.role == UserRole.CUSTOMER

    def __repr__(self):
        return f"<User {self.username} role={self.role}>"
