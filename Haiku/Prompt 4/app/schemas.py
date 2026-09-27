from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from app.models import UserRole, OrderStatus

class AddressBase(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "US"
    is_default: bool = False

class AddressCreate(AddressBase):
    pass

class Address(AddressBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

class User(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserWithAddresses(User):
    addresses: List[Address] = []

class ProductImageBase(BaseModel):
    image_url: str
    is_primary: bool = False

class ProductImage(ProductImageBase):
    id: int
    product_id: int

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    quantity_available: int
    sku: str
    weight_oz: float = 0

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity_available: Optional[int] = None
    weight_oz: Optional[float] = None

class Product(ProductBase):
    id: int
    store_id: int
    is_active: bool
    created_at: datetime
    images: List[ProductImage] = []

    class Config:
        from_attributes = True

class ReviewBase(BaseModel):
    rating: int
    comment: str

class Review(ReviewBase):
    id: int
    product_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ProductWithReviews(Product):
    reviews: List[Review] = []

class StoreBase(BaseModel):
    name: str
    description: str

class StoreCreate(StoreBase):
    pass

class Store(StoreBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CartItemBase(BaseModel):
    product_id: int
    quantity: int

class CartItem(CartItemBase):
    id: int
    user_id: int
    product: Product
    added_at: datetime

    class Config:
        from_attributes = True

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int

class OrderItem(OrderItemBase):
    id: int
    order_id: int
    price_at_purchase: float
    product: Product

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    shipping_address_id: int
    total_amount: float = 0
    shipping_cost: float = 0

class OrderCreate(BaseModel):
    shipping_address_id: int

class Order(OrderBase):
    id: int
    customer_id: int
    store_id: int
    status: OrderStatus
    tracking_number: Optional[str]
    stripe_payment_id: Optional[str]
    items: List[OrderItem] = []
    created_at: datetime

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    content: str

class Message(MessageBase):
    id: int
    user_id: int
    order_id: Optional[int]
    sender_role: UserRole
    is_from_chatbot: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ShippingRateRequest(BaseModel):
    destination_zip: str
    weight_oz: float

class ShippingRateResponse(BaseModel):
    rate: float
    carrier: str
    estimated_days: int

class CheckoutRequest(BaseModel):
    shipping_address_id: int
    payment_method_id: str
