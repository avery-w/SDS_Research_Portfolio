"""Account side tables: saved addresses, API tokens and notifications."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..clock import utcnow
from ..extensions import db
from ..ids import new_public_id, new_token
from .enums import NotificationKind
from .mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .user import User

API_TOKEN_PREFIX_LENGTH = 12
API_TOKEN_SCOPES = (
    "profile:read",
    "orders:read",
    "orders:write",
    "cart:write",
    "products:read",
    "products:write",
    "messages:write",
    "admin:read",
    "admin:write",
)


def hash_api_secret(secret: str) -> str:
    """Deterministic hash so a token can be looked up without storing it."""

    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class Address(TimestampMixin, db.Model):
    """A saved shipping or billing address owned by one user."""

    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("adr")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    label: Mapped[str] = mapped_column(String(60), default="Home")
    recipient_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(32))
    street1: Mapped[str] = mapped_column(String(200))
    street2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(40))
    postal_code: Mapped[str] = mapped_column(String(20), index=True)
    country: Mapped[str] = mapped_column(String(2), default="US")
    is_residential: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default_shipping: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default_billing: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship("User", back_populates="addresses")

    @property
    def one_line(self) -> str:
        parts = [self.street1, self.street2, self.city, f"{self.state} {self.postal_code}"]
        return ", ".join(part for part in parts if part)

    def as_shipping_dict(self) -> dict:
        return {
            "name": self.recipient_name,
            "phone": self.phone,
            "street1": self.street1,
            "street2": self.street2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "residential": self.is_residential,
        }

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "label": self.label,
            "recipient_name": self.recipient_name,
            "phone": self.phone,
            "street1": self.street1,
            "street2": self.street2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "is_residential": self.is_residential,
            "is_default_shipping": self.is_default_shipping,
            "is_default_billing": self.is_default_billing,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Address {self.public_id} {self.city}, {self.state}>"


class ApiToken(TimestampMixin, db.Model):
    """A bearer token for programmatic access to the JSON API.

    The plaintext token is shown exactly once, at creation. Only a SHA-256
    digest is persisted, and lookups go through the non-secret prefix so the
    digest never has to be scanned in full.
    """

    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("tkn")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(80), default="API token")
    prefix: Mapped[str] = mapped_column(String(24), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scopes: Mapped[list] = mapped_column(JSON, default=list)

    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_used_ip: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship("User", back_populates="api_tokens")

    # -- lifecycle ---------------------------------------------------------
    @classmethod
    def issue(
        cls,
        user: "User",
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> tuple["ApiToken", str]:
        """Create a token row and return ``(row, plaintext_token)``."""

        full_token, secret = new_token("mdk")
        record = cls(
            user_id=user.id,
            name=(name or "API token").strip()[:80],
            prefix=full_token[:API_TOKEN_PREFIX_LENGTH],
            token_hash=hash_api_secret(secret),
            scopes=list(scopes or ["profile:read", "orders:read", "products:read"]),
            expires_at=expires_at,
        )
        db.session.add(record)
        return record, full_token

    def matches(self, plaintext: str) -> bool:
        return hmac.compare_digest(self.token_hash, hash_api_secret(plaintext))

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= utcnow())

    @property
    def is_usable(self) -> bool:
        return not self.is_revoked and not self.is_expired

    def has_scope(self, scope: str) -> bool:
        if "admin:write" in (self.scopes or []):
            return True
        return scope in (self.scopes or [])

    def revoke(self) -> None:
        self.revoked_at = utcnow()

    def touch(self, ip_address: str | None = None) -> None:
        self.last_used_at = utcnow()
        self.last_used_ip = ip_address

    # -- presentation ------------------------------------------------------
    @property
    def display_prefix(self) -> str:
        return f"{self.prefix}{'*' * 6}"

    @property
    def status_label(self) -> str:
        if self.is_revoked:
            return "Revoked"
        if self.is_expired:
            return "Expired"
        return "Active"

    def to_dict(self, include_token: str | None = None) -> dict:
        payload = {
            "id": self.public_id,
            "name": self.name,
            "prefix": self.display_prefix,
            "scopes": list(self.scopes or []),
            "status": self.status_label,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
        if include_token:
            payload["token"] = include_token
        return payload

    @staticmethod
    def generate_name() -> str:
        return f"token-{secrets.token_hex(3)}"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ApiToken {self.public_id} {self.display_prefix}>"


class Notification(TimestampMixin, db.Model):
    """An in-app message shown in the notification tray."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("ntf")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    kind: Mapped[str] = mapped_column(
        String(24), default=NotificationKind.SYSTEM, index=True
    )
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(400))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship("User", back_populates="notifications")

    @property
    def icon(self) -> str:
        return NotificationKind.ICONS.get(self.kind, "bell")

    @property
    def kind_label(self) -> str:
        return NotificationKind.label(self.kind)

    def mark_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.read_at = utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
            "url": self.url,
            "is_read": self.is_read,
            "icon": self.icon,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Notification {self.public_id} {self.kind}>"
