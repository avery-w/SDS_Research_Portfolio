from pydantic import BaseModel, Field
from datetime import datetime


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    price: float = Field(gt=0)
    compare_at_price: float | None = None
    sku: str | None = None
    barcode: str | None = None
    category: str | None = None
    tags: list[str] = []
    images: list[str] = []
    stock_quantity: int = Field(ge=0, default=0)
    weight_oz: float | None = None
    dimensions: dict | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    compare_at_price: float | None = None
    sku: str | None = None
    barcode: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    images: list[str] | None = None
    stock_quantity: int | None = Field(default=None, ge=0)
    weight_oz: float | None = None
    dimensions: dict | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    slug: str | None
    description: str | None
    price: float
    compare_at_price: float | None
    sku: str | None
    barcode: str | None
    category: str | None
    tags: list[str]
    images: list[str]
    stock_quantity: int
    weight_oz: float | None
    dimensions: dict | None
    is_active: bool
    store_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
