"""Request/response schemas. First validation layer before any business logic."""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, field_validator
from .models import UserRole, OrderStatus


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=255)
    role: UserRole = UserRole.customer

    @field_validator("role")
    @classmethod
    def only_customer_or_seller(cls, v: UserRole) -> UserRole:
        if v not in (UserRole.customer, UserRole.seller):
            raise ValueError("Self-registration allowed only for customer or seller")
        return v


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StoreOut(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    owner_id: int

    class Config:
        from_attributes = True


class StoreUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)
    price: float = Field(gt=0, le=1_000_000)
    inventory: int = Field(ge=0, default=0)
    weight_lb: float = Field(gt=0, default=1.0)
    length_in: float = Field(gt=0, default=10.0)
    width_in: float = Field(gt=0, default=8.0)
    height_in: float = Field(gt=0, default=4.0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=10000)
    price: Optional[float] = Field(None, gt=0)
    inventory: Optional[int] = Field(None, ge=0)
    weight_lb: Optional[float] = Field(None, gt=0)
    length_in: Optional[float] = Field(None, gt=0)
    width_in: Optional[float] = Field(None, gt=0)
    height_in: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    store_id: int
    name: str
    description: str
    price: float
    inventory: int
    weight_lb: float
    length_in: float
    width_in: float
    height_in: float
    image_path: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CartItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=999)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductOut

    class Config:
        from_attributes = True


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    seller_id: int
    product: Optional[ProductOut] = None

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    customer_id: int
    status: OrderStatus
    subtotal: float
    shipping_cost: float
    total: float
    shipping_address: str
    shipping_zip: str
    created_at: datetime
    items: List[OrderItemOut] = []

    class Config:
        from_attributes = True


class CheckoutRequest(BaseModel):
    shipping_address: str = Field(min_length=5, max_length=500)
    shipping_zip: str = Field(min_length=5, max_length=10)


class ShippingRequest(BaseModel):
    dest_zip: str = Field(min_length=5, max_length=10)
    weight_lb: float = Field(gt=0, default=1.0)
    length_in: float = Field(gt=0, default=10.0)
    width_in: float = Field(gt=0, default=8.0)
    height_in: float = Field(gt=0, default=4.0)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    reply: str


class MessageCreate(BaseModel):
    receiver_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=2000)
    product_id: Optional[int] = None
    order_id: Optional[int] = None


class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    product_id: Optional[int]
    order_id: Optional[int]
    content: str
    created_at: datetime
    is_read: bool

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    key: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    value: str = Field(max_length=2000)


class AnalyticsOut(BaseModel):
    total_revenue: float
    order_count: int
    active_users: int
    active_stores: int
    active_products: int
    top_sellers: List[dict[str, Any]]
