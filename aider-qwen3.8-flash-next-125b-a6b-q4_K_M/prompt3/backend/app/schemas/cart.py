import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel


class CartItemCreate(BaseModel):
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int = 1


class CartItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None
    quantity: int
    product_title: str | None = None
    product_price: Decimal | None = None
    added_at: datetime

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    items: list[CartItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
