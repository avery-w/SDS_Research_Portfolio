import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class ProductVariantCreate(BaseModel):
    variant_name: str
    variant_value: str
    price_override: Decimal | None = None
    stock_quantity: int = 0


class ProductVariantResponse(BaseModel):
    id: uuid.UUID
    variant_name: str
    variant_value: str
    price_override: Decimal | None
    stock_quantity: int

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    slug: str = Field(min_length=1, max_length=500)
    description: str | None = None
    price: Decimal
    currency: str = "USD"
    sku: str | None = None
    stock_quantity: int = 0
    category: str | None = None
    tags: list[str] | None = None
    images: list[str] | None = None
    variants: list[ProductVariantCreate] | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    title: str
    slug: str
    description: str | None
    price: Decimal
    currency: str
    sku: str | None
    stock_quantity: int
    category: str | None
    tags: list[str] | None
    images: list[str] | None
    is_active: bool
    created_at: datetime
    variants: list[ProductVariantResponse] = []

    class Config:
        from_attributes = True
