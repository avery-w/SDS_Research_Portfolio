from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str = "customer"

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AddressCreate(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    is_default: bool = False

class AddressResponse(BaseModel):
    id: int
    street: str
    city: str
    state: str
    zip_code: str
    is_default: bool

    class Config:
        from_attributes = True

class StoreCreate(BaseModel):
    name: str
    description: str
    logo_url: Optional[str] = None

class StoreResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str
    logo_url: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    name: str
    description: str
    price: Decimal
    stock: int
    sku: str
    category: str
    image_urls: str

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    stock: Optional[int] = None
    category: Optional[str] = None
    image_urls: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    store_id: int
    name: str
    description: str
    price: Decimal
    stock: int
    sku: str
    category: str
    image_urls: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductResponse

    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]

    class Config:
        from_attributes = True

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price_at_purchase: Decimal

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    delivery_address_id: int
    shipping_method: str
    payment_method: str

class OrderResponse(BaseModel):
    id: int
    customer_id: int
    status: str
    total_amount: Decimal
    shipping_cost: Decimal
    shipping_method: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    product_id: int
    rating: int
    comment: str

class ReviewResponse(BaseModel):
    id: int
    product_id: int
    customer_id: int
    rating: int
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReturnCreate(BaseModel):
    product_id: int
    reason: str

class ReturnResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    status: str
    refund_amount: Decimal
    requested_at: datetime

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    recipient_id: int
    product_id: Optional[int] = None
    content: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    content: str
    created_at: datetime
    is_read: bool

    class Config:
        from_attributes = True

class ChatbotQuery(BaseModel):
    query: str

class ChatbotResponse(BaseModel):
    response: str
    suggested_sellers: Optional[List[str]] = None

class ShippingRateRequest(BaseModel):
    destination_zip: str
    weight: float
    service_type: str = "ground"

class ShippingRateResponse(BaseModel):
    cost: Decimal
    estimated_days: int
    carrier: str

class Token(BaseModel):
    access_token: str
    token_type: str

class AnalyticsResponse(BaseModel):
    total_users: int
    total_sellers: int
    total_orders: int
    total_revenue: Decimal
    active_products: int
    avg_order_value: Decimal
