"""Shopping carts, cart lines and discount coupons.

A cart can belong to a signed-in user or to a guest session keyed by a cookie.
When a guest signs in the two are merged, which is why ``status`` exists rather
than simply deleting a converted cart.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..clock import utcnow
from ..extensions import db
from ..ids import new_public_id, new_reference
from .enums import CartStatus, DiscountType
from .mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .catalog import Product
    from .store import Store
    from .user import User

CART_GUEST_TTL_DAYS = 30
MAX_LINE_QUANTITY = 99


class Cart(TimestampMixin, db.Model):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("crt")
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    session_key: Mapped[str | None] = mapped_column(String(80), index=True)

    status: Mapped[str] = mapped_column(
        String(16), default=CartStatus.ACTIVE, nullable=False, index=True
    )
    coupon_code: Mapped[str | None] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(Text)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User | None"] = relationship("User", back_populates="carts")
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
        order_by="CartItem.id",
    )

    __table_args__ = (
        Index("ix_carts_user_status", "user_id", "status"),
        Index("ix_carts_session_status", "session_key", "status"),
    )

    # -- membership --------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.status == CartStatus.ACTIVE

    @property
    def is_guest(self) -> bool:
        return self.user_id is None

    def touch(self) -> None:
        self.last_activity_at = utcnow()

    def mark_converted(self) -> None:
        self.status = CartStatus.CONVERTED
        self.converted_at = utcnow()
        self.touch()

    def mark_abandoned(self) -> None:
        self.status = CartStatus.ABANDONED
        self.touch()

    # -- totals ------------------------------------------------------------
    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def line_count(self) -> int:
        return len(self.items)

    @property
    def subtotal_cents(self) -> int:
        return sum(item.line_total_cents for item in self.items)

    @property
    def total_weight_oz(self) -> int:
        return sum(item.line_weight_oz for item in self.items)

    @property
    def store_ids(self) -> list[int]:
        seen: list[int] = []
        for item in self.items:
            if item.store_id and item.store_id not in seen:
                seen.append(item.store_id)
        return seen

    def group_by_store(self) -> dict[int, list["CartItem"]]:
        """Split the cart into one bucket per store for order creation."""

        buckets: dict[int, list[CartItem]] = {}
        for item in self.items:
            buckets.setdefault(item.store_id, []).append(item)
        return buckets

    def find_item_for(self, product_id: int) -> "CartItem | None":
        for item in self.items:
            if item.product_id == product_id:
                return item
        return None

    def remove_store_items(self, store_id: int) -> int:
        removed = [item for item in self.items if item.store_id == store_id]
        for item in removed:
            self.items.remove(item)
        return len(removed)

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "status": self.status,
            "item_count": self.item_count,
            "line_count": self.line_count,
            "subtotal_cents": self.subtotal_cents,
            "coupon_code": self.coupon_code,
            "items": [item.to_dict() for item in self.items],
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Cart {self.public_id} items={self.line_count}>"


class CartItem(TimestampMixin, db.Model):
    """One product line in a cart.

    ``unit_price_cents`` is a snapshot: if the seller changes the price the
    shopper is told at checkout rather than silently charged a new amount.
    """

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("cit")
    )
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )

    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_cents: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(String(300))

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    product: Mapped["Product"] = relationship("Product")
    store: Mapped["Store"] = relationship("Store")

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_items_cart_product"),
    )

    @property
    def line_total_cents(self) -> int:
        return int(self.unit_price_cents or 0) * int(self.quantity or 0)

    @property
    def line_weight_oz(self) -> int:
        if not self.product:
            return 0
        return int(self.product.weight_oz or 0) * int(self.quantity or 0)

    @property
    def current_price_cents(self) -> int:
        return int(self.product.price_cents or 0) if self.product else 0

    @property
    def price_changed(self) -> bool:
        return self.current_price_cents != int(self.unit_price_cents or 0)

    @property
    def price_delta_cents(self) -> int:
        return self.current_price_cents - int(self.unit_price_cents or 0)

    @property
    def exceeds_stock(self) -> bool:
        if not self.product:
            return True
        return self.quantity > self.product.available_quantity

    def sync_price(self) -> None:
        """Adopt the product's current price (after the shopper is told)."""

        if self.product:
            self.unit_price_cents = int(self.product.price_cents or 0)

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "product_id": self.product.public_id if self.product else None,
            "title": self.product.title if self.product else "Unavailable item",
            "slug": self.product.slug if self.product else None,
            "store_id": self.store.public_id if self.store else None,
            "store_name": self.store.name if self.store else None,
            "quantity": self.quantity,
            "unit_price_cents": self.unit_price_cents,
            "line_total_cents": self.line_total_cents,
            "currency": self.product.currency if self.product else "USD",
            "thumbnail_url": self.product.thumbnail_url if self.product else None,
            "stock": self.product.available_quantity if self.product else 0,
            "in_stock": self.product.in_stock if self.product else False,
            "price_changed": self.price_changed,
            "current_price_cents": self.current_price_cents,
            "note": self.note,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<CartItem {self.public_id} qty={self.quantity}>"


class Coupon(TimestampMixin, db.Model):
    """A discount code, either platform-wide or scoped to one store."""

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("cpn")
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(300))
    discount_type: Mapped[str] = mapped_column(
        String(20), default=DiscountType.PERCENT
    )
    value: Mapped[int] = mapped_column(Integer, default=0)
    max_discount_cents: Mapped[int | None] = mapped_column(Integer)
    min_order_cents: Mapped[int] = mapped_column(Integer, default=0)

    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1)

    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    applies_to_shipping: Mapped[bool] = mapped_column(Boolean, default=False)

    store: Mapped["Store | None"] = relationship("Store")

    @property
    def is_platform_wide(self) -> bool:
        return self.store_id is None

    @property
    def discount_type_label(self) -> str:
        return DiscountType.label(self.discount_type)

    @property
    def value_label(self) -> str:
        if self.discount_type == DiscountType.PERCENT:
            return f"{self.value}% off"
        if self.discount_type == DiscountType.FIXED:
            return f"${self.value / 100:.2f} off"
        return "Free shipping"

    def is_redeemable(self, at: datetime | None = None) -> tuple[bool, str]:
        """Return ``(usable, reason)`` so callers can explain a rejection."""

        moment = at or utcnow()
        if not self.is_active:
            return False, "This code is no longer active."
        if self.starts_at and moment < self.starts_at:
            return False, "This code is not active yet."
        if self.expires_at and moment > self.expires_at:
            return False, "This code has expired."
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, "This code has reached its usage limit."
        return True, ""

    def applies_to_store(self, store_id: int | None) -> bool:
        return self.store_id is None or self.store_id == store_id

    def register_use(self) -> None:
        self.used_count = (self.used_count or 0) + 1

    @staticmethod
    def normalise_code(raw: str | None) -> str:
        return (raw or "").strip().upper().replace(" ", "")

    @classmethod
    def generate_code(cls, prefix: str = "SAVE") -> str:
        return f"{prefix}{new_reference(6)}"

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "code": self.code,
            "description": self.description,
            "type": self.discount_type,
            "value": self.value,
            "label": self.value_label,
            "min_order_cents": self.min_order_cents,
            "max_uses": self.max_uses,
            "used_count": self.used_count,
            "is_active": self.is_active,
            "store_id": self.store.public_id if self.store else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Coupon {self.code} {self.value_label}>"
