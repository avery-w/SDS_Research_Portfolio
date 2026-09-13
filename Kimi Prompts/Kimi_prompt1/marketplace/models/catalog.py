"""Catalog: categories, products, images and stock adjustments."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..clock import utcnow
from ..extensions import db
from ..ids import new_public_id, slugify, unique_slug
from .enums import ProductCondition, ProductStatus
from .mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .review import Review
    from .store import Store


class Category(TimestampMixin, db.Model):
    """A browsable product category. One level of nesting is supported."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("cat")
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(40), default="tag")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent", cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="category"
    )

    @property
    def display_name(self) -> str:
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name

    @classmethod
    def make_slug(cls, name: str) -> str:
        base = slugify(name) or "category"
        taken = {
            row[0]
            for row in db.session.query(Category.slug)
            .filter(Category.slug.like(f"{base}%"))
            .all()
        }
        return unique_slug(base, taken)

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "icon": self.icon,
            "parent": self.parent.slug if self.parent else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Category {self.slug}>"


class Product(TimestampMixin, SoftDeleteMixin, db.Model):
    """A listing owned by one store.

    Physical attributes (weight, dimensions) are stored in imperial units and
    are consumed directly by the UPS rating engine.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("prd")
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )

    title: Mapped[str] = mapped_column(String(200), index=True)
    slug: Mapped[str] = mapped_column(String(220), index=True)
    sku: Mapped[str] = mapped_column(String(64), index=True)
    short_description: Mapped[str | None] = mapped_column(String(400))
    description: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(120))
    tags: Mapped[list] = mapped_column(JSON, default=list)

    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    compare_at_price_cents: Mapped[int | None] = mapped_column(Integer)
    cost_cents: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    status: Mapped[str] = mapped_column(
        String(16), default=ProductStatus.DRAFT, nullable=False, index=True
    )
    condition: Mapped[str] = mapped_column(
        String(16), default=ProductCondition.NEW, nullable=False
    )
    suspension_reason: Mapped[str | None] = mapped_column(Text)

    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, index=True)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)
    max_per_order: Mapped[int] = mapped_column(Integer, default=10)
    allow_backorder: Mapped[bool] = mapped_column(Boolean, default=False)

    # -- physical attributes used for UPS rating ---------------------------
    weight_oz: Mapped[int] = mapped_column(Integer, default=16)
    length_in: Mapped[float] = mapped_column(Float, default=8.0)
    width_in: Mapped[float] = mapped_column(Float, default=6.0)
    height_in: Mapped[float] = mapped_column(Float, default=4.0)
    requires_signature: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_adult_signature: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fragile: Mapped[bool] = mapped_column(Boolean, default=False)
    ships_free: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hazmat: Mapped[bool] = mapped_column(Boolean, default=False)

    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    sold_count: Mapped[int] = mapped_column(Integer, default=0)

    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    store: Mapped["Store"] = relationship("Store", back_populates="products")
    category: Mapped["Category | None"] = relationship(
        "Category", back_populates="products"
    )
    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )
    adjustments: Mapped[list["InventoryAdjustment"]] = relationship(
        "InventoryAdjustment",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("store_id", "sku", name="uq_products_store_sku"),
        Index("ix_products_status_price", "status", "price_cents"),
        Index("ix_products_store_status", "store_id", "status"),
    )

    # -- presentation ------------------------------------------------------
    @property
    def status_label(self) -> str:
        return ProductStatus.label(self.status)

    @property
    def condition_label(self) -> str:
        return ProductCondition.label(self.condition)

    @property
    def is_published(self) -> bool:
        return self.status == ProductStatus.ACTIVE and not self.is_deleted

    @property
    def available_quantity(self) -> int:
        return max(0, (self.stock_quantity or 0) - (self.reserved_quantity or 0))

    @property
    def in_stock(self) -> bool:
        return self.available_quantity > 0 or self.allow_backorder

    @property
    def is_low_stock(self) -> bool:
        return self.available_quantity <= (self.low_stock_threshold or 0)

    @property
    def stock_label(self) -> str:
        if self.is_deleted:
            return "Removed"
        if self.available_quantity <= 0:
            return "Backorder" if self.allow_backorder else "Out of stock"
        if self.is_low_stock:
            return f"Only {self.available_quantity} left"
        return "In stock"

    @property
    def discount_percent(self) -> int:
        compare = self.compare_at_price_cents or 0
        if compare <= 0 or compare <= self.price_cents:
            return 0
        return int(round((compare - self.price_cents) / compare * 100))

    @property
    def cubic_inches(self) -> float:
        return float((self.length_in or 0) * (self.width_in or 0) * (self.height_in or 0))

    def dimensional_weight_oz(self, divisor: int = 139) -> int:
        """UPS dimensional weight in ounces for a single unit."""

        if divisor <= 0:
            return self.weight_oz or 0
        pounds = self.cubic_inches / float(divisor)
        return int(round(pounds * 16))

    def billable_weight_oz(self, numerator: int = 1, divisor: int = 139) -> int:
        """Greater of actual and dimensional weight, times ``numerator`` units."""

        units = max(1, int(numerator))
        actual = (self.weight_oz or 0) * units
        dimensional = self.dimensional_weight_oz(divisor) * units
        return max(actual, dimensional)

    # -- images ------------------------------------------------------------
    @property
    def primary_image(self) -> "ProductImage | None":
        for image in self.images:
            if image.is_primary:
                return image
        return self.images[0] if self.images else None

    @property
    def image_url(self) -> str | None:
        image = self.primary_image
        return image.path if image else None

    @property
    def thumbnail_url(self) -> str | None:
        image = self.primary_image
        if not image:
            return None
        return image.thumbnail_path or image.path

    # -- lifecycle ---------------------------------------------------------
    def publish(self) -> None:
        self.status = ProductStatus.ACTIVE
        self.suspension_reason = None
        if not self.published_at:
            self.published_at = utcnow()

    def unpublish(self) -> None:
        self.status = ProductStatus.DRAFT

    def archive(self) -> None:
        self.status = ProductStatus.ARCHIVED

    def suspend(self, reason: str) -> None:
        self.status = ProductStatus.SUSPENDED
        self.suspension_reason = reason

    @classmethod
    def make_slug(cls, title: str, store_id: int) -> str:
        base = slugify(title) or "product"
        taken = {
            row[0]
            for row in db.session.query(Product.slug)
            .filter(Product.slug.like(f"{base}%"))
            .all()
        }
        return unique_slug(base, taken)

    def to_summary(self) -> dict:
        return {
            "id": self.public_id,
            "title": self.title,
            "slug": self.slug,
            "sku": self.sku,
            "price_cents": self.price_cents,
            "currency": self.currency,
            "stock": self.available_quantity,
            "in_stock": self.in_stock,
            "thumbnail_url": self.thumbnail_url,
            "store": self.store.name if self.store else None,
        }

    def to_dict(self, include_description: bool = True) -> dict:
        payload = {
            "id": self.public_id,
            "title": self.title,
            "slug": self.slug,
            "sku": self.sku,
            "brand": self.brand,
            "status": self.status,
            "condition": self.condition,
            "price_cents": self.price_cents,
            "compare_at_price_cents": self.compare_at_price_cents,
            "currency": self.currency,
            "discount_percent": self.discount_percent,
            "stock": self.available_quantity,
            "in_stock": self.in_stock,
            "max_per_order": self.max_per_order,
            "rating": {"average": self.rating_avg, "count": self.rating_count},
            "images": [image.to_dict() for image in self.images],
            "thumbnail_url": self.thumbnail_url,
            "category": self.category.slug if self.category else None,
            "store": {
                "id": self.store.public_id,
                "name": self.store.name,
                "slug": self.store.slug,
            }
            if self.store
            else None,
            "shipping": {
                "weight_oz": self.weight_oz,
                "length_in": self.length_in,
                "width_in": self.width_in,
                "height_in": self.height_in,
                "ships_free": self.ships_free,
                "requires_signature": self.requires_signature,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_description:
            payload["short_description"] = self.short_description
            payload["description"] = self.description
            payload["tags"] = list(self.tags or [])
        return payload

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Product {self.public_id} {self.slug}>"


class ProductImage(TimestampMixin, db.Model):
    """An uploaded product photo plus its generated thumbnail."""

    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("img")
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )

    path: Mapped[str] = mapped_column(String(400))
    thumbnail_path: Mapped[str | None] = mapped_column(String(400))
    alt_text: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    content_type: Mapped[str | None] = mapped_column(String(60))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    size_bytes: Mapped[int | None] = mapped_column(Integer)

    product: Mapped["Product"] = relationship("Product", back_populates="images")

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "url": self.path,
            "thumbnail_url": self.thumbnail_path or self.path,
            "alt_text": self.alt_text,
            "position": self.position,
            "is_primary": self.is_primary,
            "width": self.width,
            "height": self.height,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ProductImage {self.public_id}>"


class InventoryAdjustment(TimestampMixin, db.Model):
    """Append-only ledger of every stock change, whoever made it."""

    __tablename__ = "inventory_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("inv")
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(40), default="manual")
    note: Mapped[str | None] = mapped_column(String(400))
    resulting_quantity: Mapped[int] = mapped_column(Integer, default=0)
    actor_role: Mapped[str | None] = mapped_column(String(16))

    product: Mapped["Product"] = relationship(
        "Product", back_populates="adjustments"
    )

    RECIPES = {
        "manual": "Manual correction",
        "restock": "Restock received",
        "order_placed": "Reserved for an order",
        "order_cancelled": "Released from a cancelled order",
        "return_received": "Returned item back in stock",
        "damage": "Damaged or written off",
        "admin_override": "Administrator override",
        "seed": "Imported",
    }

    @property
    def reason_label(self) -> str:
        return self.RECIPES.get(self.reason, self.reason.replace("_", " ").title())

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "delta": self.delta,
            "reason": self.reason,
            "reason_label": self.reason_label,
            "note": self.note,
            "resulting_quantity": self.resulting_quantity,
            "actor_role": self.actor_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<InventoryAdjustment {self.public_id} {self.delta:+d}>"
