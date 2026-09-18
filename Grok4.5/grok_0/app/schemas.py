from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from .models import UserRole, OrderStatus


# ---------- Auth / User ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""
    role: UserRole = UserRole.customer


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


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# ---------- Store ----------
class StoreCreate(BaseModel):
    name: str
    description: str = ""


class StoreOut(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    owner_id: int

    class Config:
        from_attributes = True


# ---------- Product ----------
class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: float = Field(gt=0)
    inventory: int = Field(ge=0)
    weight_lb: float = 1.0
    length_in: float = 10.0
    width_in: float = 8.0
    height_in: float = 4.0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    inventory: Optional[int] = None
    weight_lb: Optional[float] = None
    length_in: Optional[float] = None
    width_in: Optional[float] = None
    height_in: Optional[float] = None
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


# ---------- Cart ----------
class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, default=1)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductOut

    class Config:
        from_attributes = True


# ---------- Order ----------
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
    shipping_address: str
    shipping_zip: str


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# ---------- Shipping ----------
class ShippingRequest(BaseModel):
    dest_zip: str
    weight_lb: float = 1.0
    length_in: float = 10.0
    width_in: float = 8.0
    height_in: float = 4.0


# ---------- Chat ----------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# ---------- Messages ----------
class MessageCreate(BaseModel):
    receiver_id: int
    content: str
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
