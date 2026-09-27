"""Platform support tables: chatbot transcripts, audit trail, settings.

These four tables have no owner other than the platform itself, which is why
they live together rather than next to a domain model.
"""

from __future__ import annotations

from datetime import datetime
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
from ..ids import new_public_id, new_quote_reference, new_session_key
from .enums import ChatIntent, ChatRole, SettingValueType
from .mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .user import User


class ChatSession(TimestampMixin, db.Model):
    """A conversation between a visitor and the Mercado Assistant."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("cht")
    )
    session_key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=new_session_key
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    visitor_label: Mapped[str | None] = mapped_column(String(120))
    context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_intent: Mapped[str | None] = mapped_column(String(32))
    escalated_to_human: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User | None"] = relationship("User")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )

    @property
    def is_escalated(self) -> bool:
        return bool(self.escalated_to_human)

    @property
    def transcript(self) -> list[dict]:
        return [m.to_dict() for m in self.messages]

    def add_message(
        self,
        role: str,
        content: str,
        *,
        intent: str | None = None,
        confidence: float | None = None,
        metadata: dict | None = None,
    ) -> "ChatMessage":
        message = ChatMessage(
            session_id=self.id,
            role=role,
            content=content,
            intent=intent,
            confidence=confidence,
            metadata_json=metadata or {},
        )
        db.session.add(message)
        self.message_count = (self.message_count or 0) + 1
        self.last_activity_at = utcnow()
        if intent:
            self.last_intent = intent
        return message

    def escalate(self, conversation=None) -> None:
        self.escalated_to_human = True
        if conversation is not None:
            self.escalated_conversation_id = getattr(conversation, "id", None)

    def to_dict(self) -> dict:
        return {
            "session_key": self.session_key,
            "id": self.public_id,
            "message_count": self.message_count,
            "last_intent": self.last_intent,
            "escalated": self.escalated_to_human,
            "started_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity_at": (
                self.last_activity_at.isoformat() if self.last_activity_at else None
            ),
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ChatSession {self.public_id} msgs={self.message_count}>"


class ChatMessage(TimestampMixin, db.Model):
    """One turn in a chatbot transcript."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("cmsg")
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )

    role: Mapped[str] = mapped_column(
        String(16), default=ChatRole.USER, nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(32), index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    was_helpful: Mapped[bool | None] = mapped_column(Boolean)

    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )

    @property
    def intent_label(self) -> str:
        return ChatIntent.label(self.intent) if self.intent else "-"

    @property
    def is_from_user(self) -> bool:
        return self.role == ChatRole.USER

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "role": self.role,
            "content": self.content,
            "intent": self.intent,
            "confidence": self.confidence,
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ChatMessage {self.public_id} {self.role}>"


class AuditLog(TimestampMixin, db.Model):
    """Append-only record of every privileged or state-changing action.

    Nothing in the application ever updates or deletes a row here; the model
    simply has no helper that would.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("aud")
    )

    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(16))
    actor_label: Mapped[str | None] = mapped_column(String(160))

    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(String(400))
    changes_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(16), default="info", index=True)

    actor: Mapped["User | None"] = relationship(
        "User", foreign_keys=[actor_id]
    )

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_actor_created", "actor_id", "created_at"),
    )

    SEVERITIES = ("info", "warning", "critical")

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "actor": self.actor_label or "System",
            "actor_role": self.actor_role,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "summary": self.summary,
            "changes": self.changes_json or {},
            "ip_address": self.ip_address,
            "severity": self.severity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<AuditLog {self.public_id} {self.action}>"


class PlatformSetting(TimestampMixin, db.Model):
    """A single administrator-editable knob, stored as JSON.

    Values are typed by ``value_type`` so the settings screen can render the
    right widget and reject junk before it reaches the runtime.
    """

    __tablename__ = "platform_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict)
    value_type: Mapped[str] = mapped_column(
        String(16), default=SettingValueType.STRING, nullable=False
    )

    category: Mapped[str] = mapped_column(String(40), default="general", index=True)
    label: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    updated_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[updated_by_id]
    )

    DEFAULT_PAYLOAD: dict = {"value": None}

    # -- conversion --------------------------------------------------------
    @property
    def raw_value(self):
        payload = self.value_json or {}
        return payload.get("value")

    @property
    def value(self):
        """Return the stored value coerced to ``value_type``."""

        raw = self.raw_value
        if self.value_type == SettingValueType.BOOLEAN:
            if isinstance(raw, str):
                return raw.strip().lower() in {"1", "true", "yes", "on"}
            return bool(raw)
        if self.value_type == SettingValueType.INTEGER:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return 0
        if self.value_type == SettingValueType.DECIMAL:
            try:
                return float(raw)
            except (TypeError, ValueError):
                return 0.0
        if self.value_type == SettingValueType.JSON:
            return raw if raw is not None else {}
        return "" if raw is None else str(raw)

    def set_value(self, value, actor=None) -> None:
        self.value_json = {"value": value}
        self.updated_by_id = getattr(actor, "id", None)
        self.updated_at = utcnow()

    @property
    def display_value(self) -> str:
        value = self.value
        if self.value_type == SettingValueType.BOOLEAN:
            return "On" if value else "Off"
        if self.value_type == SettingValueType.JSON:
            import json

            return json.dumps(value, sort_keys=True)
        return str(value)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "type": self.value_type,
            "value": self.value,
            "is_public": self.is_public,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by.full_name if self.updated_by else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<PlatformSetting {self.key}={self.display_value!r}>"


class ShippingQuote(TimestampMixin, db.Model):
    """A persisted UPS rate so a placed order can always be re-explained.

    Quotes expire quickly (UPS prices move, fuel surcharges reset weekly), so
    checkout refuses to place an order against an expired reference.
    """

    __tablename__ = "shipping_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=new_quote_reference
    )
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("quo")
    )
    cart_id: Mapped[int | None] = mapped_column(
        ForeignKey("carts.id", ondelete="SET NULL"), index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"), index=True
    )

    carrier: Mapped[str] = mapped_column(String(16), default="UPS")
    service_code: Mapped[str] = mapped_column(String(8))
    service_name: Mapped[str] = mapped_column(String(80))
    negotiated: Mapped[bool] = mapped_column(Boolean, default=False)

    origin_json: Mapped[dict] = mapped_column(JSON, default=dict)
    destination_json: Mapped[dict] = mapped_column(JSON, default=dict)
    packages_json: Mapped[list] = mapped_column(JSON, default=list)
    breakdown_json: Mapped[dict] = mapped_column(JSON, default=dict)

    actual_weight_lb: Mapped[float] = mapped_column(Float, default=0.0)
    dimensional_weight_lb: Mapped[float] = mapped_column(Float, default=0.0)
    billable_weight_lb: Mapped[float] = mapped_column(Float, default=0.0)
    zone: Mapped[int | None] = mapped_column(Integer)
    package_count: Mapped[int] = mapped_column(Integer, default=1)

    base_charge_cents: Mapped[int] = mapped_column(Integer, default=0)
    fuel_surcharge_cents: Mapped[int] = mapped_column(Integer, default=0)
    accessorial_cents: Mapped[int] = mapped_column(Integer, default=0)
    total_charge_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    guaranteed_days: Mapped[int | None] = mapped_column(Integer)
    estimated_delivery_date: Mapped[datetime | None] = mapped_column(DateTime)
    engine: Mapped[str] = mapped_column(String(24), default="modeled")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= utcnow())

    @property
    def is_usable(self) -> bool:
        return not self.is_expired

    def to_dict(self) -> dict:
        return {
            "reference": self.reference,
            "carrier": self.carrier,
            "service_code": self.service_code,
            "service_name": self.service_name,
            "negotiated": self.negotiated,
            "zone": self.zone,
            "package_count": self.package_count,
            "weights": {
                "actual_lb": round(self.actual_weight_lb, 2),
                "dimensional_lb": round(self.dimensional_weight_lb, 2),
                "billable_lb": round(self.billable_weight_lb, 2),
            },
            "charges": {
                "base_cents": self.base_charge_cents,
                "fuel_surcharge_cents": self.fuel_surcharge_cents,
                "accessorial_cents": self.accessorial_cents,
                "total_cents": self.total_charge_cents,
            },
            "guaranteed_days": self.guaranteed_days,
            "estimated_delivery_date": (
                self.estimated_delivery_date.date().isoformat()
                if self.estimated_delivery_date
                else None
            ),
            "breakdown": self.breakdown_json or {},
            "engine": self.engine,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ShippingQuote {self.reference} {self.service_name}>"
