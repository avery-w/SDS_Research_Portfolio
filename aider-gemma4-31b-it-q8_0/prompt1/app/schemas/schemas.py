from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from app.models.models import UserRole, OrderStatus, ReturnStatus

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.CUSTOMER

class UserOut(UserBase):
    id: int
    role: UserRole
    is_active: bool
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class StoreBase(BaseModel):
    store_name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None

class StoreCreate(StoreBase):
    pass

class StoreOut(StoreBase):
    id: int
    seller_id: int
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int
    category: Optional[str] = None
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int
    store_id: int
    class Config:
        from_attributes = True

class ShippingRequest(BaseModel):
    destination_zip: str
    weight: float

class ShippingResponse(BaseModel):
    rate: float
    currency: str = "USD"
    service_level: str

class ChatRequest(BaseModel):
    message: str
    product_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str

class OrderCreate(BaseModel):
    shipping_address: str
    product_ids: List[int] # Simplified for initialization

class OrderOut(BaseModel):
    id: int
    total_price: float
    status: OrderStatus
    created_at: datetime
    class Config:
        from_attributes = True

class AnalyticsResponse(BaseModel):
    total_revenue: float
    top_selling_products: List[dict]
    seller_performance: List[dict]
