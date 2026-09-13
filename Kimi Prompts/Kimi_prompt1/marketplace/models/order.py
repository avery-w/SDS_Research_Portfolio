"""Orders and order lines.

Checkout creates one ``Order`` per store so each seller only ever sees their
own fulfilment work and their own money. Orders that came from the same basket
share a ``checkout_group_id`` so the customer can still see one purchase.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..clock import utcnow
from ..extensions import db
from ..ids import new_order_number, new_public_id
from .enums import FulfillmentStatus, OrderEventType, OrderStatus, PaymentStatus
from .mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .catalog import Product
    from .order_events import OrderEvent, ReturnRequest
    from .store import Store
    from .user import User

RETURN_WINDOW_DAYS = 30


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_number: Mapped[str] = mapped_column(
        String(24), unique=True, index=True, default=new_order_number
    )
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("ord")
    )
    checkout_group_id: Mapped[str] = mapped_column(String(32), index=True)

    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), index=True
    )

    status: Mapped[str] = mapped_column(
        String(24), default=OrderStatus.PENDING_PAYMENT, nullable=False, index=True
    )
    payment_status: Mapped[str] = mapped_column(
        String(24), default=PaymentStatus.UNPAID, nullable=False, index=True
    )
    fulfillment_status: Mapped[str] = mapped_column(
        String(24), default=FulfillmentStatus.UNFULFILLED, nullable=False
    )

    currency: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal_cents: Mapped[int] = mapped_column(Integer, default=0)
    shipping_cents: Mapped[int] = mapped_column(Integer, default=0)
    tax_cents: Mapped[int] = mapped_column(Integer, default=0)
    discount_cents: Mapped[int] = mapped_column(Integer, default=0)
    total_cents: Mapped[int] = mapped_column(Integer, default=0)
    refunded_cents: Mapped[int] = mapped_column(Integer, default=0)

    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.08)
    commission_cents: Mapped[int] = mapped_column(Integer, default=0)
    coupon_code: Mapped[str | None] = mapped_column(String(40))

    # -- destination -------------------------------------------------------
    ship_to_name: Mapped[str] = mapped_column(String(160), default="")
    ship_to_phone: Mapped[str | None] = mapped_column(String(32))
    ship_to_street1: Mapped[str] = mapped_column(String(200), default="")
    ship_to_street2: Mapped[str | None] = mapped_column(String(200))
    ship_to_city: Mapped[str] = mapped_column(String(120), default="")
    ship_to_state: Mapped[str] = mapped_column(String(40), default="")
    ship_to_postal_code: Mapped[str] = mapped_column(String(20), default="")
    ship_to_country: Mapped[str] = mapped_column(String(2), default="US")
    is_residential: Mapped[bool] = mapped_column(Boolean, default=True)

    # -- origin snapshot (store ship-from at the time of purchase) ---------
    ship_from_name: Mapped[str | None] = mapped_column(String(160))
    ship_from_city: Mapped[str | None] = mapped_column(String(120))
    ship_from_state: Mapped[str | None] = mapped_column(String(40))
    ship_from_postal_code: Mapped[str | None] = mapped_column(String(20))
    ship_from_country: Mapped[str] = mapped_column(String(2), default="US")

    # -- UPS rating result -------------------------------------------------
    shipping_carrier: Mapped[str] = mapped_column(String(20), default="UPS")
    shipping_service_code: Mapped[str | None] = mapped_column(String(8))
    shipping_service_name: Mapped[str | None] = mapped_column(String(80))
    shipping_quote_ref: Mapped[str | None] = mapped_column(String(32), index=True)
    shipping_quote_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    billable_weight_lb: Mapped[float] = mapped_column(Float, default=0.0)
    package_count: Mapped[int] = mapped_column(Integer, default=1)
    estimated_delivery_days: Mapped[int | None] = mapped_column(Integer)
    estimated_delivery_date: Mapped[datetime | None] = mapped_column(DateTime)
    requires_signature: Mapped[bool] = mapped_column(Boolean, default=False)

    tracking_number: Mapped[str | None] = mapped_column(String(64))
    tracking_url: Mapped[str | None] = mapped_column(String(400))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)

    placed_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, index=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    customer_note: Mapped[str | None] = mapped_column(Text)
    internal_note: Mapped[str | None] = mapped_column(Text)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    buyer: Mapped["User"] = relationship(
        "User", back_populates="orders", foreign_keys=[buyer_id]
    )
    cancelled_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[cancelled_by_id]
    )
    store: Mapped["Store"] = relationship("Store", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )
    events: Mapped[list["OrderEvent"]] = relationship(
        "OrderEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderEvent.id",
    )
    returns: Mapped[list["ReturnRequest"]] = relationship(
        "ReturnRequest", back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_orders_buyer_placed", "buyer_id", "placed_at"),
        Index("ix_orders_store_status", "store_id", "status"),
        Index("ix_orders_status_placed", "status", "placed_at"),
    )

    # -- presentation ------------------------------------------------------
    @property
    def reference(self) -> str:
        return self.order_number

    @property
    def status_label(self) -> str:
        return OrderStatus.label(self.status)

    @property
    def payment_status_label(self) -> str:
        return PaymentStatus.label(self.payment_status)

    @property
    def fulfillment_status_label(self) -> str:
        return FulfillmentStatus.label(self.fulfillment_status)

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def is_cancellable(self) -> bool:
        """A customer may cancel until the parcel is handed to the carrier."""

        return self.status in {
            OrderStatus.PENDING_PAYMENT,
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
        }

    @property
    def is_returnable(self) -> bool:
        if self.status not in {OrderStatus.DELIVERED, OrderStatus.SHIPPED}:
            return False
        if self.delivered_at is None:
            return self.status == OrderStatus.DELIVERED
        return utcnow() - self.delivered_at <= timedelta(days=RETURN_WINDOW_DAYS)

    @property
    def return_window_closes(self) -> datetime | None:
        if not self.delivered_at:
            return None
        return self.delivered_at + timedelta(days=RETURN_WINDOW_DAYS)

    @property
    def is_open(self) -> bool:
        return self.status in OrderStatus.OPEN

    @property
    def net_revenue_cents(self) -> int:
        return max(0, self.total_cents - self.refunded_cents)

    @property
    def payout_cents(self) -> int:
        """What the seller keeps after commission and shipping."""

        return max(
            0, self.net_revenue_cents - self.shipping_cents - self.commission_cents
        )

    @property
    def ship_to_line(self) -> str:
        parts = [
            self.ship_to_street1,
            self.ship_to_street2,
            self.ship_to_city,
            f"{self.ship_to_state} {self.ship_to_postal_code}".strip(),
        ]
        return ", ".join(part for part in parts if part)

    @property
    def shipped_line(self) -> str:
        if not self.tracking_number:
            return "Not shipped yet"
        return f"{self.shipping_carrier or 'UPS'} {self.tracking_number}"

    @property
    def estimated_delivery_text(self) -> str:
        if not self.estimated_delivery_date:
            return "Calculated at checkout"
        return self.estimated_delivery_date.strftime("%b %d, %Y")

    @property
    def open_return(self) -> "ReturnRequest | None":
        from .enums import ReturnStatus

        for request in self.returns:
            if request.status in ReturnStatus.OPEN:
                return request
        return None

    # -- timeline ----------------------------------------------------------
    def add_event(
        self,
        event_type: str,
        message: str,
        actor=None,
        metadata: dict | None = None,
        *,
        visible_to_customer: bool = True,
    ) -> "OrderEvent":
        """Append an immutable entry to the order timeline."""

        from .order_events import OrderEvent

        event = OrderEvent(
            order_id=self.id,
            event_type=event_type,
            message=message,
            actor_id=getattr(actor, "id", None),
            actor_role=getattr(actor, "role", None),
            actor_name=getattr(actor, "full_name", None),
            visible_to_customer=visible_to_customer,
            metadata_json=metadata or {},
        )
        db.session.add(event)
        return event

    def record_note(
        self, message: str, actor=None, internal: bool = False
    ) -> "OrderEvent":
        return self.add_event(
            OrderEventType.NOTE,
            message,
            actor,
            {"internal": internal},
            visible_to_customer=not internal,
        )

    # -- money -------------------------------------------------------------
    def recalculate_totals(
        self,
        *,
        shipping_cents: int | None = None,
        tax_cents: int | None = None,
        discount_cents: int | None = None,
    ) -> None:
        """Recompute the money fields from the current lines and inputs."""

        self.subtotal_cents = sum(item.line_total_cents for item in self.items)
        if discount_cents is not None:
            self.discount_cents = max(0, int(discount_cents))
        if shipping_cents is not None:
            self.shipping_cents = max(0, int(shipping_cents))
        taxable = max(0, self.subtotal_cents - self.discount_cents)
        if tax_cents is not None:
            self.tax_cents = max(0, int(tax_cents))
        else:
            self.tax_cents = int(round(taxable * (self.tax_rate or 0.0)))
        self.total_cents = max(
            0,
            self.subtotal_cents
            + self.shipping_cents
            + self.tax_cents
            - self.discount_cents,
        )
        self.commission_cents = int(
            round(self.subtotal_cents * (self.commission_rate or 0.0))
        )

    def apply_refund(self, amount_cents: int) -> None:
        amount = max(0, int(amount_cents))
        self.refunded_cents = min(
            self.total_cents, (self.refunded_cents or 0) + amount
        )
        if self.refunded_cents >= self.total_cents:
            self.payment_status = PaymentStatus.REFUNDED
        elif self.refunded_cents > 0:
            self.payment_status = PaymentStatus.PARTIALLY_REFUNDED

    def group_key(self) -> str:
        return self.checkout_group_id

    def to_summary(self) -> dict:
        return {
            "order_number": self.order_number,
            "status": self.status,
            "status_label": self.status_label,
            "total_cents": self.total_cents,
            "currency": self.currency,
            "store": self.store.name if self.store else None,
            "item_count": self.item_count,
            "placed_at": self.placed_at.isoformat() if self.placed_at else None,
            "tracking_number": self.tracking_number,
        }

    def to_dict(self, include_items: bool = True) -> dict:
        payload = {
            "id": self.public_id,
            "order_number": self.order_number,
            "checkout_group_id": self.checkout_group_id,
            "status": self.status,
            "payment_status": self.payment_status,
            "fulfillment_status": self.fulfillment_status,
            "currency": self.currency,
            "totals": {
                "subtotal_cents": self.subtotal_cents,
                "shipping_cents": self.shipping_cents,
                "tax_cents": self.tax_cents,
                "discount_cents": self.discount_cents,
                "total_cents": self.total_cents,
                "refunded_cents": self.refunded_cents,
            },
            "coupon_code": self.coupon_code,
            "store": {
                "id": self.store.public_id,
                "name": self.store.name,
                "slug": self.store.slug,
            }
            if self.store
            else None,
            "shipping_address": {
                "name": self.ship_to_name,
                "street1": self.ship_to_street1,
                "street2": self.ship_to_street2,
                "city": self.ship_to_city,
                "state": self.ship_to_state,
                "postal_code": self.ship_to_postal_code,
                "country": self.ship_to_country,
                "residential": self.is_residential,
            },
            "shipping": {
                "carrier": self.shipping_carrier,
                "service_code": self.shipping_service_code,
                "service_name": self.shipping_service_name,
                "quote_reference": self.shipping_quote_ref,
                "billable_weight_lb": self.billable_weight_lb,
                "package_count": self.package_count,
                "estimated_delivery_days": self.estimated_delivery_days,
                "breakdown": self.shipping_quote_breakdown or {},
            },
            "tracking_number": self.tracking_number,
            "tracking_url": self.tracking_url,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": (
                self.delivered_at.isoformat() if self.delivered_at else None
            ),
            "placed_at": self.placed_at.isoformat() if self.placed_at else None,
            "customer_note": self.customer_note,
            "cancellable": self.is_cancellable,
            "returnable": self.is_returnable,
        }
        if include_items:
            payload["items"] = [item.to_dict() for item in self.items]
            payload["timeline"] = [event.to_dict() for event in self.events]
        return payload

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Order {self.order_number} {self.status}>"


class OrderItem(TimestampMixin, db.Model):
    """A purchased line, frozen with the values shown at checkout."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("oit")
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), index=True
    )

    title_snapshot: Mapped[str] = mapped_column(String(200))
    sku_snapshot: Mapped[str] = mapped_column(String(64), default="")
    image_snapshot: Mapped[str | None] = mapped_column(String(400))

    quantity: Mapped[int] = mapped_column(Integer, default=1)
    quantity_refunded: Mapped[int] = mapped_column(Integer, default=0)
    unit_price_cents: Mapped[int] = mapped_column(Integer, default=0)
    line_total_cents: Mapped[int] = mapped_column(Integer, default=0)
    unit_weight_oz: Mapped[int] = mapped_column(Integer, default=16)
    line_weight_oz: Mapped[int] = mapped_column(Integer, default=16)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product | None"] = relationship("Product")

    @property
    def refundable_quantity(self) -> int:
        return max(0, self.quantity - (self.quantity_refunded or 0))

    @property
    def is_reviewed(self) -> bool:
        return bool(self.review)

    @property
    def review(self):
        from .review import Review

        return (
            db.session.query(Review)
            .filter(Review.order_item_id == self.id)
            .one_or_none()
        )

    def build_from(self, cart_item) -> "OrderItem":
        """Populate the snapshot columns from a cart line."""

        product = cart_item.product
        self.product_id = product.id if product else None
        self.store_id = cart_item.store_id
        self.title_snapshot = product.title if product else "Unavailable item"
        self.sku_snapshot = product.sku if product else ""
        self.image_snapshot = product.thumbnail_url if product else None
        self.quantity = int(cart_item.quantity)
        self.unit_price_cents = int(cart_item.unit_price_cents)
        self.line_total_cents = int(cart_item.line_total_cents)
        self.unit_weight_oz = int(product.weight_oz) if product else 16
        self.line_weight_oz = self.unit_weight_oz * self.quantity
        return self

    def register_refund(self, quantity: int) -> None:
        self.quantity_refunded = min(
            self.quantity, (self.quantity_refunded or 0) + max(0, int(quantity))
        )

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "product_id": self.product.public_id if self.product else None,
            "product_slug": self.product.slug if self.product else None,
            "title": self.title_snapshot,
            "sku": self.sku_snapshot,
            "quantity": self.quantity,
            "quantity_refunded": self.quantity_refunded,
            "unit_price_cents": self.unit_price_cents,
            "line_total_cents": self.line_total_cents,
            "currency": "USD",
            "image_url": self.image_snapshot,
            "weight_oz": self.line_weight_oz,
            "refundable_quantity": self.refundable_quantity,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<OrderItem {self.public_id} {self.title_snapshot[:24]}>"
