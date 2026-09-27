from pydantic import BaseModel, Field
from datetime import datetime
from app.models.order import OrderStatus


class AddressSchema(BaseModel):
    street: str
    city: str
    state: str
    zip: str
    country: str = "US"


class CheckoutItem(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class CheckoutRequest(BaseModel):
    items: list[CheckoutItem]
    shipping_address: AddressSchema
    billing_address: AddressSchema | None = None


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    subtotal: float
    shipping_cost: float
    tax: float
    total: float
    shipping_address: dict
    billing_address: dict | None
    tracking_number: str | None
    carrier: str | None
    cancellation_reason: str | None
    return_reason: str | None
    customer_id: int
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    class Config:
        from_attributes = True
