from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum

from app.models import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.CUSTOMER


class UserRead(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class StoreBase(BaseModel):
    name: str
    description: Optional[str] = None


class StoreCreate(StoreBase):
    pass


class StoreRead(StoreBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    category: Optional[str] = None
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    store_id: int


class ProductRead(ProductBase):
    id: int
    store_id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


class CartItemBase(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class CartItemCreate(CartItemBase):
    pass


class CartItemRead(CartItemBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemRead(OrderItemBase):
    id: int
    order_id: int
    created_at: datetime

    class Config:
        orm_mode = True


class OrderBase(BaseModel):
    shipping_address: str
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    shipping_country: str = "US"


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderRead(OrderBase):
    id: int
    user_id: int
    store_id: int
    total: float
    status: str
    tracking_number: Optional[str]
    shipping_rate: Optional[float]
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemRead] = []

    class Config:
        orm_mode = True


class MessageBase(BaseModel):
    receiver_id: int
    content: str
    order_id: Optional[int] = None


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    id: int
    sender_id: int
    is_read: bool
    created_at: datetime

    class Config:
        orm_mode = True


class ReturnRequestBase(BaseModel):
    order_id: int
    reason: str


class ReturnRequestCreate(ReturnRequestBase):
    pass


class ReturnRequestRead(ReturnRequestBase):
    id: int
    status: str
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PlatformSettingBase(BaseModel):
    key: str
    value: str


class PlatformSettingCreate(PlatformSettingBase):
    pass


class PlatformSettingRead(PlatformSettingBase):
    id: int
    updated_at: datetime

    class Config:
        orm_mode = True


class AnalyticsBase(BaseModel):
    metric_name: str
    metric_value: float


class AnalyticsCreate(AnalyticsBase):
    pass


class AnalyticsRead(AnalyticsBase):
    id: int
    recorded_at: datetime

    class Config:
        orm_mode = True


class ShippingRateRequest(BaseModel):
    dest_zip: str
    dest_country: str = "US"
    weight_lbs: float = Field(gt=0)
    length_in: float = Field(gt=0)
    width_in: float = Field(gt=0)
    height_in: float = Field(gt=0)


class ShippingRateResponse(BaseModel):
    rate: Optional[float]
    currency: str = "USD"
    message: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str


class Token(BaseModel):
    access_token: str
    token_type: str
