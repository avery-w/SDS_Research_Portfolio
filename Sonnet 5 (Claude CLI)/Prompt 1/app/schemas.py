from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from .models import Role, OrderStatus, ItemStatus, ReturnStatus


# ---- Auth ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    role: Role = Role.customer  # admin accounts are never self-registered


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    role: Role
    is_active: bool
    created_at: datetime


# ---- Store ----
class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    name: str
    description: str
    is_active: bool


# ---- Product ----
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    category: str = "general"
    price_cents: int = Field(gt=0)
    stock_qty: int = Field(ge=0)
    weight_oz: float = Field(gt=0, default=8.0)
    length_in: float = Field(gt=0, default=6.0)
    width_in: float = Field(gt=0, default=6.0)
    height_in: float = Field(gt=0, default=6.0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    price_cents: int | None = Field(default=None, gt=0)
    stock_qty: int | None = Field(default=None, ge=0)
    weight_oz: float | None = Field(default=None, gt=0)
    length_in: float | None = Field(default=None, gt=0)
    width_in: float | None = Field(default=None, gt=0)
    height_in: float | None = Field(default=None, gt=0)
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_id: int
    name: str
    description: str
    category: str
    price_cents: int
    stock_qty: int
    weight_oz: float
    length_in: float
    width_in: float
    height_in: float
    is_active: bool
    images: list[str] = []


# ---- Cart ----
class CartAddRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, default=1)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    name: str
    price_cents: int
    quantity: int
    store_id: int


# ---- Shipping / checkout ----
class ShippingQuoteRequest(BaseModel):
    dest_zip: str = Field(min_length=5, max_length=10)


class ShippingOption(BaseModel):
    service: str
    label: str
    cost_cents: int
    est_business_days: str


class CheckoutRequest(BaseModel):
    ship_name: str = Field(min_length=1, max_length=255)
    ship_street: str = Field(min_length=1, max_length=255)
    ship_city: str = Field(min_length=1, max_length=100)
    ship_state: str = Field(min_length=2, max_length=2)
    ship_zip: str = Field(min_length=5, max_length=10)
    shipping_service: str = "ground"


# ---- Orders ----
class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    store_id: int
    quantity: int
    unit_price_cents: int
    status: ItemStatus


class OrderOut(BaseModel):
    id: int
    status: OrderStatus
    ship_name: str
    ship_street: str
    ship_city: str
    ship_state: str
    ship_zip: str
    shipping_service: str
    shipping_cost_cents: int
    subtotal_cents: int
    total_cents: int
    created_at: datetime
    items: list[OrderItemOut]


class ReturnRequestCreate(BaseModel):
    order_item_id: int
    reason: str = Field(min_length=1, max_length=2000)


class ReturnRequestOut(BaseModel):
    id: int
    order_item_id: int
    reason: str
    status: ReturnStatus
    created_at: datetime


class ReturnDecision(BaseModel):
    approve: bool


class ItemStatusUpdate(BaseModel):
    status: ItemStatus


# ---- Messaging ----
class MessageCreate(BaseModel):
    recipient_id: int
    body: str = Field(min_length=1, max_length=4000)
    product_id: int | None = None
    order_id: int | None = None


class MessageOut(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    product_id: int | None
    order_id: int | None
    body: str
    created_at: datetime


# ---- Chatbot ----
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    suggest_contact_seller: bool = False


# ---- Admin ----
class UserAdminUpdate(BaseModel):
    is_active: bool | None = None
    role: Role | None = None


class StoreAdminUpdate(BaseModel):
    is_active: bool | None = None


class PlatformSettingsUpdate(BaseModel):
    site_name: str | None = None
    commission_bps: int | None = Field(default=None, ge=0, le=10000)
    maintenance_mode: bool | None = None


class PlatformSettingsOut(BaseModel):
    site_name: str
    commission_bps: int
    maintenance_mode: bool


class AnalyticsOut(BaseModel):
    total_users: int
    total_customers: int
    total_sellers: int
    total_stores: int
    total_products: int
    total_orders: int
    total_revenue_cents: int
    commission_earned_cents: int
    orders_by_status: dict[str, int]
    top_products: list[dict]
