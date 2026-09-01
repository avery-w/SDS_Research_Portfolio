from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, Numeric, ForeignKey, Enum, Boolean
import enum
from app.db.base import Base

class Category(str, enum.Enum):
    general = "general"
    electronics = "electronics"
    apparel = "apparel"
    home = "home"

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    price_cents: Mapped[int] = mapped_column(Integer)  # store in cents
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    category: Mapped[Category] = mapped_column(Enum(Category), default=Category.general, index=True)
    weight_lbs: Mapped[float] = mapped_column(Numeric(10, 2))  # used for UPS
    length_in: Mapped[float] = mapped_column(Numeric(10, 2))
    width_in: Mapped[float] = mapped_column(Numeric(10, 2))
    height_in: Mapped[float] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    images: Mapped[list["ProductImage"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    inventory: Mapped["Inventory"] = relationship(back_populates="product", uselist=False, cascade="all, delete-orphan")

class ProductImage(Base):
    __tablename__ = "product_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    alt: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product: Mapped["Product"] = relationship(back_populates="images")

class Inventory(Base):
    __tablename__ = "inventory"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, index=True)
    product: Mapped["Product"] = relationship(back_populates="inventory")
