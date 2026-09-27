from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from .models import UserRole, OrderStatus

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.customer

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool
    class Config:
        from_attributes = True

# Store Schemas
class StoreBase(BaseModel):
    store_name: str
    description: Optional[str] = None

class StoreCreate(StoreBase):
    pass

class StoreOut(StoreBase):
    id: int
    seller_id: int
    created_at: datetime
    class Config:
        from_attributes = True

# Product Schemas
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int

class ProductCreate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int
    store_id: int
    image_path: Optional[str] = None
    class Config:
        from_attributes = True

# Order Schemas
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    shipping_address: str
    items: List[OrderItemCreate]

class OrderOut(BaseModel):
    id: int
    total_price: float
    status: OrderStatus
    created_at: datetime
    class Config:
        from_attributes = True

# Chat Schemas
class ChatRequest(BaseModel):
    message: str
    product_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str

# Admin Schemas
class AnalyticsOut(BaseModel):
    total_revenue: float
    total_orders: int
