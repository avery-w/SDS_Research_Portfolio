"""Verified-purchase product reviews.

A review is tied to a single ``OrderItem``, which is what makes it a *verified*
review: the author cannot review a product they never bought, and cannot review
the same purchase twice (enforced by a unique constraint).
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
from ..ids import new_public_id
from .enums import ReviewStatus
from .mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .catalog import Product
    from .order import OrderItem
    from .user import User

MIN_RATING = 1
MAX_RATING = 5


class Review(TimestampMixin, db.Model):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("rev")
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_items.id", ondelete="SET NULL"), index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )

    rating: Mapped[int] = mapped_column(Integer, default=MAX_RATING)
    title: Mapped[str | None] = mapped_column(String(160))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), default=ReviewStatus.PUBLISHED, nullable=False, index=True
    )
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)

    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    reported_count: Mapped[int] = mapped_column(Integer, default=0)

    seller_reply: Mapped[str | None] = mapped_column(Text)
    seller_replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    moderation_note: Mapped[str | None] = mapped_column(Text)
    moderated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
    author: Mapped["User"] = relationship(
        "User", back_populates="reviews", foreign_keys=[author_id]
    )
    order_item: Mapped["OrderItem | None"] = relationship("OrderItem")

    __table_args__ = (
        UniqueConstraint("order_item_id", name="uq_reviews_order_item"),
        Index("ix_reviews_product_status", "product_id", "status"),
        Index("ix_reviews_author_product", "author_id", "product_id"),
    )

    # -- presentation ------------------------------------------------------
    @property
    def status_label(self) -> str:
        return ReviewStatus.label(self.status)

    @property
    def is_published(self) -> bool:
        return self.status == ReviewStatus.PUBLISHED

    @property
    def stars(self) -> str:
        return "*" * int(self.rating or 0)

    @property
    def author_name(self) -> str:
        if not self.author:
            return "A shopper"
        first = (self.author.first_name or "").strip()
        last_initial = (self.author.last_name or "").strip()[:1]
        if first and last_initial:
            return f"{first} {last_initial}."
        return first or "A shopper"

    @property
    def is_replied(self) -> bool:
        return bool(self.seller_reply)

    @classmethod
    def clamp_rating(cls, value: int | str | None) -> int:
        try:
            number = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return MAX_RATING
        return max(MIN_RATING, min(MAX_RATING, number))

    # -- actions -----------------------------------------------------------
    def hide(self, moderator=None, note: str | None = None) -> None:
        self.status = ReviewStatus.HIDDEN
        self.moderation_note = note
        self.moderated_by_id = getattr(moderator, "id", None)

    def publish(self, moderator=None, note: str | None = None) -> None:
        self.status = ReviewStatus.PUBLISHED
        self.moderation_note = note
        self.moderated_by_id = getattr(moderator, "id", None)

    def flag(self, note: str | None = None) -> None:
        self.status = ReviewStatus.FLAGGED
        self.is_flagged = True
        self.reported_count = (self.reported_count or 0) + 1
        if note:
            self.moderation_note = note

    def reply(self, body: str) -> None:
        self.seller_reply = body
        self.seller_replied_at = utcnow()

    def mark_helpful(self) -> None:
        self.helpful_count = (self.helpful_count or 0) + 1

    def to_dict(self, include_body: bool = True) -> dict:
        payload = {
            "id": self.public_id,
            "rating": self.rating,
            "title": self.title,
            "author": self.author_name,
            "status": self.status,
            "is_verified_purchase": self.is_verified_purchase,
            "helpful_count": self.helpful_count,
            "seller_reply": self.seller_reply,
            "seller_replied_at": (
                self.seller_replied_at.isoformat() if self.seller_replied_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "product_id": self.product.public_id if self.product else None,
        }
        if include_body:
            payload["body"] = self.body
        return payload

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Review {self.public_id} {self.rating}/5>"
