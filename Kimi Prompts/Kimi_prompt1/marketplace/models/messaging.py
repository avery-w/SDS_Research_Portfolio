"""Direct messaging between customers and sellers.

This is the channel the AI assistant steers shoppers toward when a question is
genuinely about one seller's product or order, rather than something the
marketplace itself can answer.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..clock import utcnow
from ..extensions import db
from ..ids import new_public_id
from .enums import ConversationStatus, MessageRole
from .mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .catalog import Product
    from .store import Store
    from .user import User


class Conversation(TimestampMixin, db.Model):
    """One thread between a shopper and one store."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("cnv")
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )

    subject: Mapped[str] = mapped_column(String(200), default="Product question")
    status: Mapped[str] = mapped_column(
        String(16), default=ConversationStatus.OPEN, nullable=False, index=True
    )

    started_by_assistant: Mapped[bool] = mapped_column(Boolean, default=False)
    customer_unread_count: Mapped[int] = mapped_column(Integer, default=0)
    seller_unread_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    customer: Mapped["User"] = relationship("User", foreign_keys=[customer_id])
    store: Mapped["Store"] = relationship("Store", back_populates="conversations")
    product: Mapped["Product | None"] = relationship("Product")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )

    __table_args__ = (
        Index("ix_conversations_store_status", "store_id", "status"),
        Index("ix_conversations_customer_status", "customer_id", "status"),
    )

    # -- presentation ------------------------------------------------------
    @property
    def status_label(self) -> str:
        return ConversationStatus.label(self.status)

    @property
    def is_open(self) -> bool:
        return self.status == ConversationStatus.OPEN

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def last_message(self) -> "Message | None":
        return self.messages[-1] if self.messages else None

    @property
    def preview(self) -> str:
        last = self.last_message
        if not last:
            return "No messages yet."
        body = (last.body or "").strip().replace("\n", " ")
        return body[:120] + ("..." if len(body) > 120 else "")

    @property
    def customer_label(self) -> str:
        return self.customer.full_name if self.customer else "Shopper"

    @property
    def store_label(self) -> str:
        return self.store.name if self.store else "Store"

    # -- participants ------------------------------------------------------
    def involves(self, user) -> bool:
        if not user or not getattr(user, "id", None):
            return False
        if getattr(user, "is_admin", False):
            return True
        if user.id == self.customer_id:
            return True
        return bool(self.store and self.store.owner_id == user.id)

    def role_for(self, user) -> str:
        """Return the ``MessageRole`` value this user speaks as."""

        if user is None or not getattr(user, "id", None):
            return MessageRole.ASSISTANT
        if getattr(user, "is_admin", False):
            return MessageRole.ADMIN
        if self.store and user.id == self.store.owner_id:
            return MessageRole.SELLER
        return MessageRole.CUSTOMER

    # -- state -------------------------------------------------------------
    def post(self, sender, body: str, role: str | None = None) -> "Message":
        """Append a message and update the unread counters."""

        speaking_as = role or self.role_for(sender)
        message = Message(
            conversation_id=self.id,
            sender_id=getattr(sender, "id", None),
            sender_role=speaking_as,
            sender_name=getattr(sender, "full_name", None)
            or ("Mercado Assistant" if speaking_as == MessageRole.ASSISTANT else None),
            body=(body or "").strip(),
        )
        db.session.add(message)
        self.last_message_at = utcnow()
        self.touch_unread(speaking_as)
        if self.status == ConversationStatus.CLOSED:
            self.status = ConversationStatus.OPEN
            self.closed_at = None
        return message

    def touch_unread(self, speaker_role: str) -> None:
        """Increment the counter for whoever did *not* just speak."""

        if speaker_role == MessageRole.CUSTOMER:
            self.seller_unread_count = (self.seller_unread_count or 0) + 1
        elif speaker_role in {MessageRole.SELLER, MessageRole.ADMIN}:
            self.customer_unread_count = (self.customer_unread_count or 0) + 1
        elif speaker_role == MessageRole.ASSISTANT:
            self.customer_unread_count = (self.customer_unread_count or 0) + 1

    def mark_read_for(self, user) -> None:
        if user is None or not getattr(user, "id", None):
            return
        if user.id == self.customer_id or getattr(user, "is_admin", False):
            self.customer_unread_count = 0
        if self.store and user.id == self.store.owner_id:
            self.seller_unread_count = 0

    def close(self) -> None:
        self.status = ConversationStatus.CLOSED
        self.closed_at = utcnow()

    def reopen(self) -> None:
        self.status = ConversationStatus.OPEN
        self.closed_at = None

    def to_dict(self, include_messages: bool = False) -> dict:
        payload = {
            "id": self.public_id,
            "subject": self.subject,
            "status": self.status,
            "store": {
                "id": self.store.public_id,
                "name": self.store.name,
                "slug": self.store.slug,
            }
            if self.store
            else None,
            "customer": self.customer.to_summary() if self.customer else None,
            "product": {
                "id": self.product.public_id,
                "title": self.product.title,
                "slug": self.product.slug,
            }
            if self.product
            else None,
            "message_count": self.message_count,
            "unread": {
                "customer": self.customer_unread_count,
                "seller": self.seller_unread_count,
            },
            "preview": self.preview,
            "started_by_assistant": self.started_by_assistant,
            "last_message_at": (
                self.last_message_at.isoformat() if self.last_message_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_messages:
            payload["messages"] = [m.to_dict() for m in self.messages]
        return payload

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Conversation {self.public_id} {self.status}>"


class Message(TimestampMixin, db.Model):
    """A single message inside a conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("msg")
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    sender_role: Mapped[str] = mapped_column(
        String(16), default=MessageRole.CUSTOMER, index=True
    )
    sender_name: Mapped[str | None] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    attachment_path: Mapped[str | None] = mapped_column(String(400))
    is_automated: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    sender: Mapped["User | None"] = relationship("User", foreign_keys=[sender_id])

    @property
    def role_label(self) -> str:
        return MessageRole.label(self.sender_role)

    @property
    def is_from_customer(self) -> bool:
        return self.sender_role == MessageRole.CUSTOMER

    @property
    def is_from_seller_side(self) -> bool:
        return self.sender_role in {MessageRole.SELLER, MessageRole.ADMIN}

    def mark_read(self) -> None:
        if not self.read_at:
            self.read_at = utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "sender_role": self.sender_role,
            "sender_name": self.sender_name,
            "body": self.body,
            "attachment_url": self.attachment_path,
            "is_automated": self.is_automated,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Message {self.public_id} {self.sender_role}>"
