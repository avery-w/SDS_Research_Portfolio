from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

ROLES = ("customer", "seller", "admin")
ORDER_STATUSES = ("placed", "shipped", "delivered", "cancelled", "return_requested", "returned", "return_rejected")
RESTOCKED = {"cancelled", "returned"}  # statuses whose items are back in inventory
NOT_REVENUE = RESTOCKED
CUSTOMER_TRANSITIONS = {"placed": ("cancelled",), "shipped": ("return_requested",), "delivered": ("return_requested",)}
SELLER_TRANSITIONS = {
    "placed": ("shipped", "cancelled"),
    "shipped": ("delivered",),
    "return_requested": ("returned", "return_rejected"),
}
SETTING_DEFAULTS = {"site_name": "Longhorn Market", "commission_pct": "10", "announcement": ""}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __table_args__ = (CheckConstraint("role IN ('customer', 'seller', 'admin')", name="ck_user_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="customer")
    active: Mapped[bool] = mapped_column(default=True)
    street: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(2), default="")
    zip: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    store: Mapped["Store | None"] = relationship(back_populates="owner")

    @property
    def is_active(self):  # Flask-Login refuses to log in inactive users
        return self.active

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Store(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    owner: Mapped[User] = relationship(back_populates="store")
    products: Mapped[list["Product"]] = relationship(back_populates="store")


class Product(db.Model):
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="ck_product_price"),
        CheckConstraint("stock >= 0", name="ck_product_stock"),
        CheckConstraint("weight_lb > 0 AND length_in > 0 AND width_in > 0 AND height_in > 0", name="ck_product_dims"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("store.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(60), default="General", index=True)
    price_cents: Mapped[int]
    stock: Mapped[int] = mapped_column(default=0)
    weight_lb: Mapped[float] = mapped_column(default=1.0)
    length_in: Mapped[float] = mapped_column(default=10.0)
    width_in: Mapped[float] = mapped_column(default=8.0)
    height_in: Mapped[float] = mapped_column(default=4.0)
    image: Mapped[str | None] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    store: Mapped[Store] = relationship(back_populates="products")


class CartItem(db.Model):
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_cart_line"),
        CheckConstraint("quantity > 0", name="ck_cart_qty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    quantity: Mapped[int] = mapped_column(default=1)

    product: Mapped[Product] = relationship()


class Order(db.Model):
    """One order per store per checkout, so each seller fulfills and ships its own package."""

    __tablename__ = "orders"  # "order" is a reserved word in SQL
    __table_args__ = (
        CheckConstraint(
            "status IN ('placed', 'shipped', 'delivered', 'cancelled', 'return_requested', 'returned', 'return_rejected')",
            name="ck_order_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("store.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="placed", index=True)
    subtotal_cents: Mapped[int]
    shipping_cents: Mapped[int]
    shipping_service: Mapped[str] = mapped_column(String(60))
    ship_name: Mapped[str] = mapped_column(String(120))
    ship_street: Mapped[str] = mapped_column(String(200))
    ship_city: Mapped[str] = mapped_column(String(100))
    ship_state: Mapped[str] = mapped_column(String(2))
    ship_zip: Mapped[str] = mapped_column(String(10))
    tracking_number: Mapped[str] = mapped_column(String(60), default="")
    return_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    customer: Mapped[User] = relationship()
    store: Mapped[Store] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")

    @property
    def total_cents(self):
        return self.subtotal_cents + self.shipping_cents

    def set_status(self, status):
        """Change status, keeping inventory in sync. Raises ValueError on a bad status or missing stock."""
        if status not in ORDER_STATUSES:
            raise ValueError(f"Unknown status {status!r}")
        was, now = self.status in RESTOCKED, status in RESTOCKED
        if was != now:
            for item in self.items:
                if now:
                    item.product.stock += item.quantity
                elif item.product.stock < item.quantity:
                    raise ValueError(f"Not enough stock of {item.product_name} to reopen this order")
                else:
                    item.product.stock -= item.quantity
        self.status = status


class OrderItem(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    product_name: Mapped[str] = mapped_column(String(200))  # snapshot, product may be renamed later
    unit_price_cents: Mapped[int]
    quantity: Mapped[int]

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Message(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    body: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    sender: Mapped[User] = relationship(foreign_keys=[sender_id])
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id])
    product: Mapped[Product | None] = relationship()


class Setting(db.Model):
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


def get_setting(key):
    row = db.session.get(Setting, key)
    return row.value if row else SETTING_DEFAULTS.get(key, "")


def sales_summary(store_id=None, days=30):
    """Revenue analytics for the admin dashboard (all stores) or one seller's store."""
    counted = Order.status.not_in(NOT_REVENUE)
    scope = [counted] + ([Order.store_id == store_id] if store_id else [])
    since = utcnow() - timedelta(days=days - 1)

    subtotal, shipping, count = db.session.execute(
        select(func.coalesce(func.sum(Order.subtotal_cents), 0), func.coalesce(func.sum(Order.shipping_cents), 0), func.count())
        .where(*scope)
    ).one()
    by_day = {
        str(day): cents  # SQLite returns a string, PostgreSQL a date
        for day, cents in db.session.execute(
            select(func.date(Order.created_at), func.sum(Order.subtotal_cents))
            .where(*scope, Order.created_at >= since.replace(hour=0, minute=0, second=0))
            .group_by(func.date(Order.created_at))
        )
    }
    daily = []
    for i in range(days):
        day = (since + timedelta(days=i)).date().isoformat()
        daily.append((day, by_day.get(day, 0)))
    units = func.sum(OrderItem.quantity)
    top_products = db.session.execute(
        select(OrderItem.product_name, units, func.sum(OrderItem.quantity * OrderItem.unit_price_cents))
        .join(Order).where(*scope).group_by(OrderItem.product_id, OrderItem.product_name).order_by(units.desc()).limit(5)
    ).all()
    units_sold = db.session.scalar(select(func.coalesce(units, 0)).select_from(OrderItem).join(Order).where(*scope))
    by_status = dict(
        db.session.execute(
            select(Order.status, func.count()).where(*([Order.store_id == store_id] if store_id else [])).group_by(Order.status)
        ).all()
    )
    return {
        "revenue_cents": subtotal + shipping,
        "subtotal_cents": subtotal,
        "orders": count,
        "avg_order_cents": (subtotal + shipping) // count if count else 0,
        "units": units_sold,
        "daily": daily,
        "top_products": top_products,
        "by_status": by_status,
    }
