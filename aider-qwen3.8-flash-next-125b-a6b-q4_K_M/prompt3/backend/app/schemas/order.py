import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    shipping_address: dict
    shipping_method: str | None = None


class OrderResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    store_id: uuid.UUID
    status: str
    shipping_address: dict
    shipping_method: str | None
    shipping_cost: Decimal
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    tracking_number: str | None
    cancellation_reason: str | None
    return_reason: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    class Config:
        from_attributes = True
