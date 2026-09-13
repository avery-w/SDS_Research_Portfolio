"""Pydantic schemas (DTOs) for request/response validation."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.models import OrderStatus, PaymentStatus, ReturnStatus, UserRole


# ── Helpers ──
def _decimal_to_float(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    return v


class BaseResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: float},
    )


# ──────────────────────────── Auth ────────────────────────────
class TokenPayload(BaseModel):
    sub: int
    exp: int
    role: str
    type: str = "access"


class TokenResponse(BaseResponse):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.CUSTOMER

    @field_validator("password")
    @classmethod
    def _pwd_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserRead(BaseResponse):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_email_verified: bool
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=30)
    address_line1: Optional[str] = Field(default=None, max_length=255)
    address_line2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None, max_length=50)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, max_length=50)


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ──────────────────────────── Store ────────────────────────────
class StoreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    address_line1: Optional[str] = Field(default=None, max_length=255)
    address_line2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None, max_length=50)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default="US", max_length=50)


class StoreUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = None
    logo_image: Optional[str] = None
    address_line1: Optional[str] = Field(default=None, max_length=255)
    address_line2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None, max_length=50)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None


class StoreRead(BaseResponse):
    id: int
    seller_id: int
    name: str
    slug: str
    description: Optional[str] = None
    logo_image: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    seller: "UserMiniRead" = None


# ──────────────────────────── Category ────────────────────────────
class CategoryRead(BaseResponse):
    id: int
    name: str
    slug: str
    parent_id: Optional[int] = None


# ──────────────────────────── Product ────────────────────────────
class ProductImageRead(BaseResponse):
    id: int
    image_url: str
    alt_text: Optional[str] = None
    is_primary: bool
    position: int


class ProductRead(BaseResponse):
    id: int
    store_id: int
    category_id: Optional[int] = None
    category: Optional[CategoryRead] = None
    name: str
    slug: str
    description: Optional[str] = None
    price: float
    cost_price: Optional[float] = None
    sku: Optional[str] = None
    stock_quantity: int
    is_active: bool
    is_featured: bool
    weight: Optional[float] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageRead] = []
    average_rating: Optional[float] = None
    review_count: int = 0


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    cost_price: Optional[float] = Field(default=None, ge=0)
    sku: Optional[str] = Field(default=None, max_length=100)
    category_id: Optional[int] = None
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True
    is_featured: bool = False
    weight: Optional[float] = Field(default=None, ge=0)
    length: Optional[float] = Field(default=None, ge=0)
    width: Optional[float] = Field(default=None, ge=0)
    height: Optional[float] = Field(default=None, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    sku: Optional[str] = Field(default=None, max_length=100)
    category_id: Optional[int] = None
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    weight: Optional[float] = Field(default=None, ge=0)
    length: Optional[float] = Field(default=None, ge=0)
    width: Optional[float] = Field(default=None, ge=0)
    height: Optional[float] = Field(default=None, ge=0)


class ProductPage(BaseResponse):
    items: list[ProductRead]
    total: int
    page: int
    per_page: int
    pages: int


class ProductImageCreate(BaseModel):
    image_url: str
    alt_text: Optional[str] = None
    is_primary: bool = False
    position: int = 0


class ProductImageUpdate(BaseModel):
    alt_text: Optional[str] = None
    is_primary: Optional[bool] = None
    position: Optional[int] = None


# ──────────────────────────── Cart ────────────────────────────
class CartItemRead(BaseResponse):
    id: int
    cart_id: int
    product_id: int
    quantity: int
    price_at_add: float
    product: Optional[ProductRead] = None


class CartRead(BaseResponse):
    id: int
    user_id: int
    items: list[CartItemRead] = []
    total_items: int = 0
    subtotal: float = 0.0


class CartItemAdd(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(default=1, gt=0, le=999)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., gt=0, le=999)


# ──────────────────────────── Orders ────────────────────────────
class OrderItemRead(BaseResponse):
    id: int
    order_id: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: int
    unit_price: float
    total_price: float


class OrderStatusHistoryRead(BaseResponse):
    id: int
    order_id: int
    status: str
    note: Optional[str] = None
    created_at: datetime
    created_by_id: Optional[int] = None


class OrderRead(BaseResponse):
    id: int
    order_number: str
    user_id: int
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    status: OrderStatus
    total_amount: float
    shipping_cost: float
    tax_amount: float
    grand_total: float
    shipping_address: str
    billing_address: str
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    payment_status: PaymentStatus
    payment_method: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead] = []
    status_history: list[OrderStatusHistoryRead] = []


class CheckoutRequest(BaseModel):
    shipping_address_line1: str = Field(..., min_length=1, max_length=255)
    shipping_address_line2: Optional[str] = Field(default=None, max_length=255)
    shipping_city: str = Field(..., min_length=1, max_length=100)
    shipping_state: str = Field(..., min_length=1, max_length=50)
    shipping_postal_code: str = Field(..., min_length=1, max_length=20)
    shipping_country: str = Field(default="US", max_length=50)
    billing_same_as_shipping: bool = True
    billing_address_line1: Optional[str] = Field(default=None, max_length=255)
    billing_address_line2: Optional[str] = Field(default=None, max_length=255)
    billing_city: Optional[str] = Field(default=None, max_length=100)
    billing_state: Optional[str] = Field(default=None, max_length=50)
    billing_postal_code: Optional[str] = Field(default=None, max_length=20)
    billing_country: Optional[str] = Field(default="US", max_length=50)
    phone: Optional[str] = Field(default=None, max_length=30)
    note: Optional[str] = Field(default=None, max_length=1000)
    shipping_service: str = Field(
        default="ups_ground",
        description="Service key: ups_ground, ups_3day, ups_2day, ups_next_day",
    )


class CancelOrder(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None
    tracking_number: Optional[str] = None


class OrderPage(BaseResponse):
    items: list[OrderRead]
    total: int
    page: int
    per_page: int
    pages: int


# ──────────────────────────── Returns ────────────────────────────
class ReturnCreate(BaseModel):
    order_id: int = Field(..., gt=0)
    order_item_id: Optional[int] = None
    reason: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)


class ReturnRead(BaseResponse):
    id: int
    return_number: str
    order_id: int
    order_item_id: Optional[int] = None
    reason: str
    description: Optional[str] = None
    status: ReturnStatus
    admin_note: Optional[str] = None
    requested_at: datetime
    resolved_at: Optional[datetime] = None


class ReturnProcess(BaseModel):
    status: ReturnStatus
    admin_note: Optional[str] = None


# ──────────────────────────── Reviews ────────────────────────────
class ReviewCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewRead(BaseResponse):
    id: int
    product_id: int
    product_name: Optional[str] = None
    user_id: int
    user_name: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ──────────────────────────── Messages ────────────────────────────
class MessageSend(BaseModel):
    recipient_id: int = Field(..., gt=0)
    order_id: Optional[int] = None
    product_id: Optional[int] = None
    subject: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=10000)


class MessageRead(BaseResponse):
    id: int
    order_id: Optional[int] = None
    product_id: Optional[int] = None
    sender_id: int
    recipient_id: int
    sender_name: Optional[str] = None
    subject: str
    body: str
    is_read: bool
    sent_at: datetime
    read_at: Optional[datetime] = None


class ConversationRead(BaseResponse):
    id: int
    order_id: Optional[int] = None
    product_id: Optional[int] = None
    sender_id: int
    recipient_id: int
    sender_name: Optional[str] = None
    recipient_name: Optional[str] = None
    subject: str
    is_read: bool
    latest_body: Optional[str] = None
    latest_sent: Optional[datetime] = None


# ──────────────────────────── Chatbot ────────────────────────────
class ChatbotMessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    product_id: Optional[int] = None
    order_id: Optional[int] = None


class ChatbotMessageRead(BaseResponse):
    sender: str
    message: str
    created_at: datetime


class ChatbotConversationRead(BaseResponse):
    id: int
    session_id: str
    messages: list[ChatbotMessageRead] = []


# ──────────────────────────── Shipping ────────────────────────────
class ShippingRate(BaseResponse):
    service: str
    service_name: str
    rate: float
    estimated_days: int
    currency: str = "USD"


class ShippingEstimateResponse(BaseResponse):
    origin: str
    destination_zip: str
    rates: list[ShippingRate]
    package: dict[str, Any]


# ──────────────────────────── Analytics ────────────────────────────
class AnalyticsOverview(BaseResponse):
    total_users: int
    total_sellers: int
    total_products: int
    total_orders: int
    total_revenue: float
    total_orders_today: int
    total_revenue_today: float
    top_products: list[dict[str, Any]] = []


class SellerAnalytics(BaseResponse):
    total_orders: int
    total_revenue: float
    pending_orders: int
    shipped_orders: int
    cancelled_orders: int
    revenue_by_day: list[dict[str, Any]] = []
    top_products: list[dict[str, Any]] = []


class AdminAnalytics(BaseResponse):
    total_users: int
    total_sellers: int
    total_products: int
    total_orders: int
    total_revenue: float
    gross_profit: float
    orders_by_status: dict[str, int] = {}
    revenue_by_day: list[dict[str, Any]] = []
    top_products: list[dict[str, Any]] = []


class ErrorResponse(BaseResponse):
    detail: str
    code: Optional[str] = None


class UserMiniRead(BaseResponse):
    id: int
    email: str
    full_name: str
    role: UserRole


StoreRead.model_rebuild()
ProductRead.model_rebuild()
ProductPage.model_rebuild()
CartItemRead.model_rebuild()
CartRead.model_rebuild()
