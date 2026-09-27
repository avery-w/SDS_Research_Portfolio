"""Every ORM model, exported from one place.

Importing this package registers all mappers, so it must be imported before
``db.create_all()`` runs.
"""

from __future__ import annotations

from .account import API_TOKEN_SCOPES, Address, ApiToken, Notification, hash_api_secret
from .cart import MAX_LINE_QUANTITY, Cart, CartItem, Coupon
from .catalog import Category, InventoryAdjustment, Product, ProductImage
from .enums import (
    PRODUCT_SORT_OPTIONS,
    CartStatus,
    ChatIntent,
    ChatRole,
    Choices,
    ConversationStatus,
    DiscountType,
    FulfillmentStatus,
    MessageRole,
    NotificationKind,
    OrderEventType,
    OrderStatus,
    PaymentStatus,
    ProductCondition,
    ProductStatus,
    ReturnReason,
    ReturnResolution,
    ReturnStatus,
    ReviewStatus,
    SettingValueType,
    ShippingService,
    StoreStatus,
    UserRole,
    UserStatus,
)
from .messaging import Conversation, Message
from .order import RETURN_WINDOW_DAYS, Order, OrderItem
from .order_events import OrderEvent, ReturnRequest
from .review import MAX_RATING, MIN_RATING, Review
from .store import Store
from .support import AuditLog, ChatMessage, ChatSession, PlatformSetting, ShippingQuote
from .user import User

__all__ = [
    # enums / constants
    "Choices",
    "PRODUCT_SORT_OPTIONS",
    "CartStatus",
    "ChatIntent",
    "ChatRole",
    "ConversationStatus",
    "DiscountType",
    "FulfillmentStatus",
    "MessageRole",
    "NotificationKind",
    "OrderEventType",
    "OrderStatus",
    "PaymentStatus",
    "ProductCondition",
    "ProductStatus",
    "ReturnReason",
    "ReturnResolution",
    "ReturnStatus",
    "ReviewStatus",
    "SettingValueType",
    "ShippingService",
    "StoreStatus",
    "UserRole",
    "UserStatus",
    # accounts
    "API_TOKEN_SCOPES",
    "Address",
    "ApiToken",
    "Notification",
    "User",
    "hash_api_secret",
    # storefronts
    "Store",
    # catalog
    "Category",
    "InventoryAdjustment",
    "Product",
    "ProductImage",
    # cart
    "MAX_LINE_QUANTITY",
    "Cart",
    "CartItem",
    "Coupon",
    # orders
    "RETURN_WINDOW_DAYS",
    "Order",
    "OrderItem",
    "OrderEvent",
    "ReturnRequest",
    # reviews
    "MAX_RATING",
    "MIN_RATING",
    "Review",
    # messaging
    "Conversation",
    "Message",
    # platform
    "AuditLog",
    "ChatMessage",
    "ChatSession",
    "PlatformSetting",
    "ShippingQuote",
]
