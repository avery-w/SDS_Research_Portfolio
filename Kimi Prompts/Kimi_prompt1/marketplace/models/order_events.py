"""Order timeline entries and customer return requests."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
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
from ..ids import new_public_id, new_return_number
from .enums import (
    OrderEventType,
    ReturnReason,
    ReturnResolution,
    ReturnStatus,
)
from .mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .order import Order, OrderItem
    from .user import User


class OrderEvent(TimestampMixin, db.Model):
    """An immutable entry in an order's history.

    Sellers see every event; customers only see entries where
    ``visible_to_customer`` is true, which keeps internal notes internal.
    """

    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("oev")
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )

    event_type: Mapped[str] = mapped_column(
        String(32), default=OrderEventType.NOTE, index=True
    )
    message: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_role: Mapped[str | None] = mapped_column(String(16))
    actor_name: Mapped[str | None] = mapped_column(String(160))
    visible_to_customer: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    order: Mapped["Order"] = relationship("Order", back_populates="events")
    actor: Mapped["User | None"] = relationship("User", foreign_keys=[actor_id])

    @property
    def event_label(self) -> str:
        return OrderEventType.label(self.event_type)

    @property
    def icon(self) -> str:
        return {
            OrderEventType.CREATED: "sparkle",
            OrderEventType.PAID: "card",
            OrderEventType.PROCESSING: "box",
            OrderEventType.SHIPPED: "truck",
            OrderEventType.DELIVERED: "check",
            OrderEventType.CANCELLED: "x",
            OrderEventType.REFUNDED: "arrow-uturn",
            OrderEventType.NOTE: "note",
            OrderEventType.RETURN_REQUESTED: "arrow-uturn",
            OrderEventType.RETURN_APPROVED: "check",
            OrderEventType.RETURN_REJECTED: "x",
            OrderEventType.RETURN_RECEIVED: "box",
            OrderEventType.RETURN_REFUNDED: "card",
            OrderEventType.ADMIN_OVERRIDE: "shield",
        }.get(self.event_type, "dot")

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "type": self.event_type,
            "label": self.event_label,
            "message": self.message,
            "actor": self.actor_name or "System",
            "actor_role": self.actor_role,
            "icon": self.icon,
            "visible_to_customer": self.visible_to_customer,
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<OrderEvent {self.public_id} {self.event_type}>"


class ReturnRequest(TimestampMixin, db.Model):
    """A customer's request to send one or more items back."""

    __tablename__ = "return_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("rma")
    )
    return_number: Mapped[str] = mapped_column(
        String(24), unique=True, index=True, default=new_return_number
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_items.id", ondelete="SET NULL"), index=True
    )
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), index=True
    )

    status: Mapped[str] = mapped_column(
        String(20), default=ReturnStatus.REQUESTED, nullable=False, index=True
    )
    reason_code: Mapped[str] = mapped_column(
        String(30), default=ReturnReason.OTHER, nullable=False
    )
    reason_text: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str] = mapped_column(
        String(20), default=ReturnResolution.REFUND, nullable=False
    )

    quantity: Mapped[int] = mapped_column(Integer, default=1)
    refund_amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    restock: Mapped[bool] = mapped_column(Boolean, default=True)

    return_tracking_number: Mapped[str | None] = mapped_column(String(64))
    return_label_url: Mapped[str | None] = mapped_column(String(400))

    decided_at: Mapped[datetime | None] = mapped_column(DateTime)
    decided_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    decision_note: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(DateTime)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_admin_override: Mapped[bool] = mapped_column(Boolean, default=False)

    order: Mapped["Order"] = relationship("Order", back_populates="returns")
    order_item: Mapped["OrderItem | None"] = relationship("OrderItem")
    buyer: Mapped["User"] = relationship("User", foreign_keys=[buyer_id])
    decided_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[decided_by_id]
    )

    __table_args__ = (
        Index("ix_returns_order_status", "order_id", "status"),
        Index("ix_returns_store_status", "store_id", "status"),
    )

    # -- presentation ------------------------------------------------------
    @property
    def status_label(self) -> str:
        return ReturnStatus.label(self.status)

    @property
    def reason_label(self) -> str:
        return ReturnReason.label(self.reason_code)

    @property
    def resolution_label(self) -> str:
        return ReturnResolution.label(self.resolution)

    @property
    def is_open(self) -> bool:
        return self.status in ReturnStatus.OPEN

    @property
    def is_decided(self) -> bool:
        return self.status in {
            ReturnStatus.APPROVED,
            ReturnStatus.REJECTED,
            ReturnStatus.RECEIVED,
            ReturnStatus.REFUNDED,
        }

    @property
    def is_seller_fault(self) -> bool:
        return self.reason_code in ReturnReason.SELLER_FAULT

    @property
    def item_title(self) -> str:
        if self.order_item:
            return self.order_item.title_snapshot
        return f"Entire order {self.order.order_number}" if self.order else "Order"

    @property
    def suggested_refund_cents(self) -> int:
        """Refund the line total proportionally to the returned quantity."""

        if not self.order_item:
            return 0
        unit = int(self.order_item.unit_price_cents or 0)
        return unit * max(1, int(self.quantity or 1))

    def approve(self, actor=None, note: str | None = None) -> None:
        self.status = ReturnStatus.APPROVED
        self.decided_at = utcnow()
        self.decided_by_id = getattr(actor, "id", None)
        self.decision_note = note
        if not self.refund_amount_cents:
            self.refund_amount_cents = self.suggested_refund_cents

    def reject(self, actor=None, note: str | None = None) -> None:
        self.status = ReturnStatus.REJECTED
        self.decided_at = utcnow()
        self.decided_by_id = getattr(actor, "id", None)
        self.decision_note = note

    def mark_received(self, restock: bool = True) -> None:
        self.status = ReturnStatus.RECEIVED
        self.received_at = utcnow()
        self.restock = restock

    def mark_refunded(self) -> None:
        self.status = ReturnStatus.REFUNDED
        self.refunded_at = utcnow()

    def cancel(self) -> None:
        self.status = ReturnStatus.CANCELLED

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "return_number": self.return_number,
            "order_number": self.order.order_number if self.order else None,
            "item_title": self.item_title,
            "status": self.status,
            "reason_code": self.reason_code,
            "reason_text": self.reason_text,
            "resolution": self.resolution,
            "quantity": self.quantity,
            "refund_amount_cents": self.refund_amount_cents,
            "decision_note": self.decision_note,
            "return_tracking_number": self.return_tracking_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "refunded_at": self.refunded_at.isoformat() if self.refunded_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ReturnRequest {self.return_number} {self.status}>"
