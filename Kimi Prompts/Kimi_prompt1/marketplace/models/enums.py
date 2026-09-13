"""Closed vocabularies used across the marketplace.

Values are stored as short strings rather than native database enums so that a
new state can be added with a code deploy instead of a migration, and so the
same schema works on SQLite and PostgreSQL.

``Choices`` subclasses carry both the stored value and a human label, which
keeps template copy and validation in one place.
"""

from __future__ import annotations


class Choices:
    """A validated, labelled value set backed by a ``value -> label`` mapping."""

    _LABELS: dict[str, str] = {}

    @classmethod
    def values(cls) -> list[str]:
        return list(cls._LABELS)

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return list(cls._LABELS.items())

    @classmethod
    def labels(cls) -> dict[str, str]:
        return dict(cls._LABELS)

    @classmethod
    def is_valid(cls, value: object) -> bool:
        return isinstance(value, str) and value in cls._LABELS

    @classmethod
    def label(cls, value: object) -> str:
        if value is None:
            return "Unknown"
        return cls._LABELS.get(str(value), str(value).replace("_", " ").title())

    @classmethod
    def default(cls) -> str:
        return next(iter(cls._LABELS))


class UserRole(Choices):
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"

    _LABELS = {
        CUSTOMER: "Customer",
        SELLER: "Seller",
        ADMIN: "Administrator",
    }


class UserStatus(Choices):
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"

    _LABELS = {
        ACTIVE: "Active",
        PENDING: "Pending verification",
        SUSPENDED: "Suspended",
        DEACTIVATED: "Deactivated",
    }


class StoreStatus(Choices):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"

    _LABELS = {
        PENDING: "Awaiting review",
        ACTIVE: "Active",
        SUSPENDED: "Suspended",
        CLOSED: "Closed",
    }


class ProductStatus(Choices):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"

    _LABELS = {
        DRAFT: "Draft",
        ACTIVE: "Active",
        ARCHIVED: "Archived",
        SUSPENDED: "Suspended by admin",
    }


class ProductCondition(Choices):
    NEW = "new"
    LIKE_NEW = "like_new"
    REFURBISHED = "refurbished"
    USED = "used"

    _LABELS = {
        NEW: "New",
        LIKE_NEW: "Like new",
        REFURBISHED: "Refurbished",
        USED: "Used",
    }


class CartStatus(Choices):
    ACTIVE = "active"
    CONVERTED = "converted"
    ABANDONED = "abandoned"
    MERGED = "merged"

    _LABELS = {
        ACTIVE: "Active",
        CONVERTED: "Converted to order",
        ABANDONED: "Abandoned",
        MERGED: "Merged into customer cart",
    }


class OrderStatus(Choices):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    PARTIALLY_SHIPPED = "partially_shipped"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURN_REQUESTED = "return_requested"
    RETURNED = "returned"
    REFUNDED = "refunded"

    _LABELS = {
        PENDING_PAYMENT: "Awaiting payment",
        PAID: "Paid",
        PROCESSING: "Preparing for shipment",
        PARTIALLY_SHIPPED: "Partially shipped",
        SHIPPED: "Shipped",
        DELIVERED: "Delivered",
        CANCELLED: "Cancelled",
        RETURN_REQUESTED: "Return requested",
        RETURNED: "Returned",
        REFUNDED: "Refunded",
    }

    TERMINAL = {CANCELLED, REFUNDED}
    OPEN = {PENDING_PAYMENT, PAID, PROCESSING, PARTIALLY_SHIPPED, SHIPPED}
    FULFILLED = {DELIVERED, SHIPPED, PARTIALLY_SHIPPED}


class PaymentStatus(Choices):
    UNPAID = "unpaid"
    AUTHORIZED = "authorized"
    PAID = "paid"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"
    FAILED = "failed"
    VOIDED = "voided"

    _LABELS = {
        UNPAID: "Unpaid",
        AUTHORIZED: "Authorized",
        PAID: "Paid",
        PARTIALLY_REFUNDED: "Partially refunded",
        REFUNDED: "Refunded",
        FAILED: "Payment failed",
        VOIDED: "Voided",
    }


class FulfillmentStatus(Choices):
    UNFULFILLED = "unfulfilled"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"

    _LABELS = {
        UNFULFILLED: "Unfulfilled",
        PARTIALLY_FULFILLED: "Partially fulfilled",
        FULFILLED: "Fulfilled",
        CANCELLED: "Cancelled",
    }


class ReturnStatus(Choices):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

    _LABELS = {
        REQUESTED: "Request submitted",
        APPROVED: "Approved - ship it back",
        REJECTED: "Rejected",
        IN_TRANSIT: "Return in transit",
        RECEIVED: "Item received",
        REFUNDED: "Refunded",
        CANCELLED: "Cancelled",
    }

    OPEN = {REQUESTED, APPROVED, IN_TRANSIT, RECEIVED}


class ReturnReason(Choices):
    DAMAGED = "damaged"
    DEFECTIVE = "defective"
    WRONG_ITEM = "wrong_item"
    NOT_AS_DESCRIBED = "not_as_described"
    CHANGED_MIND = "changed_mind"
    ARRIVED_LATE = "arrived_late"
    OTHER = "other"

    _LABELS = {
        DAMAGED: "Arrived damaged",
        DEFECTIVE: "Defective or does not work",
        WRONG_ITEM: "Wrong item shipped",
        NOT_AS_DESCRIBED: "Not as described",
        CHANGED_MIND: "Changed my mind",
        ARRIVED_LATE: "Arrived later than promised",
        OTHER: "Something else",
    }

    SELLER_FAULT = {DAMAGED, DEFECTIVE, WRONG_ITEM, NOT_AS_DESCRIBED}


class ReturnResolution(Choices):
    REFUND = "refund"
    REPLACEMENT = "replacement"
    STORE_CREDIT = "store_credit"

    _LABELS = {
        REFUND: "Refund to original payment method",
        REPLACEMENT: "Replacement item",
        STORE_CREDIT: "Marketplace store credit",
    }


class ConversationStatus(Choices):
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"

    _LABELS = {
        OPEN: "Open",
        CLOSED: "Closed",
        ARCHIVED: "Archived",
    }


class MessageRole(Choices):
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    _LABELS = {
        CUSTOMER: "Customer",
        SELLER: "Seller",
        ADMIN: "Marketplace support",
        ASSISTANT: "Mercado Assistant",
        SYSTEM: "System",
    }


class ReviewStatus(Choices):
    PUBLISHED = "published"
    HIDDEN = "hidden"
    FLAGGED = "flagged"

    _LABELS = {
        PUBLISHED: "Published",
        HIDDEN: "Hidden by admin",
        FLAGGED: "Flagged for review",
    }


class DiscountType(Choices):
    PERCENT = "percent"
    FIXED = "fixed"
    FREE_SHIPPING = "free_shipping"

    _LABELS = {
        PERCENT: "Percentage off",
        FIXED: "Fixed amount off",
        FREE_SHIPPING: "Free shipping",
    }


class NotificationKind(Choices):
    ORDER = "order"
    SHIPMENT = "shipment"
    MESSAGE = "message"
    REVIEW = "review"
    RETURN = "return"
    SYSTEM = "system"

    _LABELS = {
        ORDER: "Order",
        SHIPMENT: "Shipment",
        MESSAGE: "Message",
        REVIEW: "Review",
        RETURN: "Return",
        SYSTEM: "System",
    }

    ICONS = {
        ORDER: "receipt",
        SHIPMENT: "truck",
        MESSAGE: "chat",
        REVIEW: "star",
        RETURN: "arrow-uturn",
        SYSTEM: "bell",
    }


class SettingValueType(Choices):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    JSON = "json"

    _LABELS = {
        STRING: "Text",
        INTEGER: "Whole number",
        DECIMAL: "Decimal number",
        BOOLEAN: "On / off",
        JSON: "JSON document",
    }


class ChatRole(Choices):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    _LABELS = {
        USER: "Shopper",
        ASSISTANT: "Mercado Assistant",
        SYSTEM: "System",
    }


class ChatIntent(Choices):
    GREETING = "greeting"
    PRODUCT_QUESTION = "product_question"
    ORDER_STATUS = "order_status"
    SHIPPING_ESTIMATE = "shipping_estimate"
    RETURNS = "returns"
    PAYMENT = "payment"
    SELLER_CONTACT = "seller_contact"
    ACCOUNT = "account"
    PRICING = "pricing"
    COMPLAINT = "complaint"
    HUMAN_HANDOFF = "human_handoff"
    SMALL_TALK = "small_talk"
    FALLBACK = "fallback"

    _LABELS = {
        GREETING: "Greeting",
        PRODUCT_QUESTION: "Product question",
        ORDER_STATUS: "Order status",
        SHIPPING_ESTIMATE: "Shipping estimate",
        RETURNS: "Returns",
        PAYMENT: "Payment",
        SELLER_CONTACT: "Contact seller",
        ACCOUNT: "Account",
        PRICING: "Pricing",
        COMPLAINT: "Complaint",
        HUMAN_HANDOFF: "Human handoff",
        SMALL_TALK: "Small talk",
        FALLBACK: "Unclassified",
    }


class OrderEventType(Choices):
    CREATED = "created"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    NOTE = "note"
    RETURN_REQUESTED = "return_requested"
    RETURN_APPROVED = "return_approved"
    RETURN_REJECTED = "return_rejected"
    RETURN_RECEIVED = "return_received"
    RETURN_REFUNDED = "return_refunded"
    ADMIN_OVERRIDE = "admin_override"

    _LABELS = {
        CREATED: "Order placed",
        PAID: "Payment captured",
        PROCESSING: "Seller started preparing the order",
        SHIPPED: "Shipped",
        DELIVERED: "Delivered",
        CANCELLED: "Cancelled",
        REFUNDED: "Refunded",
        NOTE: "Note added",
        RETURN_REQUESTED: "Return requested",
        RETURN_APPROVED: "Return approved",
        RETURN_REJECTED: "Return rejected",
        RETURN_RECEIVED: "Returned item received",
        RETURN_REFUNDED: "Return refunded",
        ADMIN_OVERRIDE: "Administrator override",
    }


class ShippingService(Choices):
    """UPS service codes supported by the rating engine."""

    GROUND = "03"
    THREE_DAY_SELECT = "12"
    SECOND_DAY_AIR = "02"
    NEXT_DAY_AIR_SAVER = "13"
    NEXT_DAY_AIR = "01"
    STANDARD = "11"

    _LABELS = {
        GROUND: "UPS Ground",
        THREE_DAY_SELECT: "UPS 3 Day Select",
        SECOND_DAY_AIR: "UPS 2nd Day Air",
        NEXT_DAY_AIR_SAVER: "UPS Next Day Air Saver",
        NEXT_DAY_AIR: "UPS Next Day Air",
        STANDARD: "UPS Standard",
    }

    GROUND_SERVICES = {GROUND, STANDARD}
    AIR_SERVICES = {THREE_DAY_SELECT, SECOND_DAY_AIR, NEXT_DAY_AIR_SAVER, NEXT_DAY_AIR}


PRODUCT_SORT_OPTIONS = [
    ("relevance", "Most relevant"),
    ("newest", "Newest arrivals"),
    ("price_asc", "Price: low to high"),
    ("price_desc", "Price: high to low"),
    ("rating", "Top rated"),
    ("best_selling", "Best selling"),
]

PRODUCT_SORT_VALUES = {value for value, _ in PRODUCT_SORT_OPTIONS}


def label_for(choices_cls: type[Choices], value: object) -> str:
    return choices_cls.label(value)
