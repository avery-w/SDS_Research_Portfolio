"""Storefronts.

Every seller owns exactly one store. The store carries the ship-from address
that the UPS rating engine uses as the origin for that seller's orders, which
is why the address lives here rather than on the product.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..clock import utcnow
from ..extensions import db
from ..ids import new_public_id, slugify, unique_slug
from .enums import StoreStatus
from .mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .catalog import Product
    from .messaging import Conversation
    from .order import Order
    from .user import User


class Store(TimestampMixin, db.Model):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("str")
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    name: Mapped[str] = mapped_column(String(140))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    tagline: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    logo_path: Mapped[str | None] = mapped_column(String(255))
    banner_path: Mapped[str | None] = mapped_column(String(255))
    accent_color: Mapped[str] = mapped_column(String(9), default="#c2410c")

    status: Mapped[str] = mapped_column(
        String(16), default=StoreStatus.PENDING, nullable=False, index=True
    )
    status_reason: Mapped[str | None] = mapped_column(Text)

    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    website_url: Mapped[str | None] = mapped_column(String(255))
    return_policy: Mapped[str | None] = mapped_column(Text)
    shipping_policy: Mapped[str | None] = mapped_column(Text)

    # -- ship-from address (UPS rating origin for this store) --------------
    ship_from_name: Mapped[str | None] = mapped_column(String(160))
    ship_from_street1: Mapped[str | None] = mapped_column(String(200))
    ship_from_street2: Mapped[str | None] = mapped_column(String(200))
    ship_from_city: Mapped[str | None] = mapped_column(String(120))
    ship_from_state: Mapped[str | None] = mapped_column(String(40))
    ship_from_postal_code: Mapped[str | None] = mapped_column(String(20))
    ship_from_country: Mapped[str] = mapped_column(String(2), default="US")
    ship_from_phone: Mapped[str | None] = mapped_column(String(32))

    # -- commercial terms --------------------------------------------------
    handling_days: Mapped[int] = mapped_column(Integer, default=1)
    default_item_weight_oz: Mapped[int] = mapped_column(Integer, default=16)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.08)
    free_shipping_threshold_cents: Mapped[int | None] = mapped_column(Integer)

    # -- denormalised stats ------------------------------------------------
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    product_count: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_sales_cents: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_order_count: Mapped[int] = mapped_column(Integer, default=0)

    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    owner: Mapped["User"] = relationship(
        "User", back_populates="store", foreign_keys=[owner_id]
    )
    approved_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[approved_by_id]
    )
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="store", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="store")
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="store"
    )

    __table_args__ = (
        Index("ix_stores_status_featured", "status", "is_featured"),
        Index("ix_stores_postal_code", "ship_from_postal_code"),
    )

    # -- presentation ------------------------------------------------------
    @property
    def status_label(self) -> str:
        return StoreStatus.label(self.status)

    @property
    def is_active(self) -> bool:
        return self.status == StoreStatus.ACTIVE

    @property
    def can_list_products(self) -> bool:
        return self.status == StoreStatus.ACTIVE

    @property
    def initials(self) -> str:
        words = [word for word in self.name.split() if word]
        return "".join(word[0] for word in words[:2]).upper() or "ST"

    @property
    def ship_from_line(self) -> str:
        parts = [self.ship_from_city, self.ship_from_state]
        city_state = ", ".join(part for part in parts if part)
        return f"{city_state} {self.ship_from_postal_code or ''}".strip()

    @property
    def has_ship_from(self) -> bool:
        return bool(
            self.ship_from_street1
            and self.ship_from_city
            and self.ship_from_state
            and self.ship_from_postal_code
        )

    def apply_rating(self, review_count: int, rating_total: int) -> None:
        """Recompute the cached rating from aggregate review data."""

        self.rating_count = int(review_count or 0)
        self.rating_avg = (
            round(float(rating_total) / review_count, 2) if review_count else 0.0
        )

    def record_sale(self, amount_cents: int) -> None:
        self.lifetime_sales_cents = (self.lifetime_sales_cents or 0) + int(amount_cents)
        self.lifetime_order_count = (self.lifetime_order_count or 0) + 1

    @classmethod
    def make_slug(cls, name: str) -> str:
        """Generate a store slug, ignoring nothing but existing rows.

        Slugs are globally unique, so a collision gets a numeric suffix.
        """

        base = slugify(name) or "store"
        taken = {
            row[0]
            for row in db.session.query(Store.slug)
            .filter(Store.slug.like(f"{base}%"))
            .all()
        }
        return unique_slug(base, taken)

    def approve(self, admin_user) -> None:
        self.status = StoreStatus.ACTIVE
        self.status_reason = None
        self.approved_at = utcnow()
        self.approved_by_id = getattr(admin_user, "id", None)

    def suspend(self, reason: str) -> None:
        self.status = StoreStatus.SUSPENDED
        self.status_reason = reason

    def reopen(self) -> None:
        self.status = StoreStatus.ACTIVE
        self.status_reason = None

    def close(self, reason: str | None = None) -> None:
        self.status = StoreStatus.CLOSED
        self.status_reason = reason

    def as_origin(self) -> dict:
        """The origin address handed to the UPS rating engine."""

        return {
            "name": self.ship_from_name or self.name,
            "street1": self.ship_from_street1,
            "street2": self.ship_from_street2,
            "city": self.ship_from_city,
            "state": self.ship_from_state,
            "postal_code": self.ship_from_postal_code,
            "country": self.ship_from_country or "US",
            "phone": self.ship_from_phone,
            "residential": False,
        }

    def to_dict(self, include_owner: bool = False) -> dict:
        payload = {
            "id": self.public_id,
            "name": self.name,
            "slug": self.slug,
            "tagline": self.tagline,
            "description": self.description,
            "logo_url": self.logo_path,
            "banner_url": self.banner_path,
            "accent_color": self.accent_color,
            "status": self.status,
            "handling_days": self.handling_days,
            "rating": {"average": self.rating_avg, "count": self.rating_count},
            "product_count": self.product_count,
            "ships_from": {
                "city": self.ship_from_city,
                "state": self.ship_from_state,
                "postal_code": self.ship_from_postal_code,
                "country": self.ship_from_country,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_owner and self.owner:
            payload["owner"] = self.owner.to_summary()
        return payload

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Store {self.public_id} {self.slug}>"
