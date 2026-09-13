"""Accounts.

A single ``User`` table holds every role. Role and status are separate fields
so an administrator can promote a customer to seller, or suspend an account,
without touching any other table.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from ..clock import utcnow
from ..extensions import db
from ..ids import new_public_id
from .enums import UserRole, UserStatus
from .mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .account import Address, ApiToken, Notification
    from .cart import Cart
    from .order import Order
    from .review import Review
    from .store import Store


class User(TimestampMixin, UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: new_public_id("usr")
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    password_updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    first_name: Mapped[str] = mapped_column(String(80), default="")
    last_name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str | None] = mapped_column(String(32))

    role: Mapped[str] = mapped_column(
        String(16), default=UserRole.CUSTOMER, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), default=UserStatus.ACTIVE, nullable=False, index=True
    )
    status_reason: Mapped[str | None] = mapped_column(Text)

    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)

    avatar_path: Mapped[str | None] = mapped_column(String(255))

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_login_ip: Mapped[str | None] = mapped_column(String(64))
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    auth_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    internal_notes: Mapped[str | None] = mapped_column(Text)

    store: Mapped["Store | None"] = relationship(
        "Store",
        back_populates="owner",
        uselist=False,
        foreign_keys="Store.owner_id",
    )
    addresses: Mapped[list["Address"]] = relationship(
        "Address", back_populates="user", cascade="all, delete-orphan"
    )
    api_tokens: Mapped[list["ApiToken"]] = relationship(
        "ApiToken", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="buyer", foreign_keys="Order.buyer_id"
    )
    carts: Mapped[list["Cart"]] = relationship("Cart", back_populates="user")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="author")

    __table_args__ = (
        Index("ix_users_role_status", "role", "status"),
        Index("ix_users_created_at", "created_at"),
    )

    # -- identity ----------------------------------------------------------
    def get_id(self) -> str:
        return str(self.id)

    @property
    def full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email.split("@")[0]

    @property
    def initials(self) -> str:
        letters = [part[0] for part in (self.first_name, self.last_name) if part]
        return "".join(letters).upper() or self.email[:2].upper()

    @property
    def display_name(self) -> str:
        return self.full_name

    # -- credentials -------------------------------------------------------
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)
        self.password_updated_at = utcnow()
        self.auth_version = (self.auth_version or 0) + 1

    def check_password(self, raw_password: str) -> bool:
        if not raw_password or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    def invalidate_sessions(self) -> None:
        """Bump the auth version so every existing session is rejected."""

        self.auth_version = (self.auth_version or 0) + 1

    # -- state -------------------------------------------------------------
    @property
    def is_active(self) -> bool:
        """Only fully active accounts may hold a session."""

        return self.status == UserStatus.ACTIVE

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > utcnow())

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_seller(self) -> bool:
        return self.role == UserRole.SELLER

    @property
    def is_customer(self) -> bool:
        return self.role == UserRole.CUSTOMER

    @property
    def role_label(self) -> str:
        return UserRole.label(self.role)

    @property
    def status_label(self) -> str:
        return UserStatus.label(self.status)

    @property
    def can_sell(self) -> bool:
        """Can this user list products right now?"""

        if not self.is_active:
            return False
        if self.role not in {UserRole.SELLER, UserRole.ADMIN}:
            return False
        from .enums import StoreStatus

        return bool(self.store and self.store.status == StoreStatus.ACTIVE)

    def register_login(self, ip_address: str | None = None) -> None:
        self.last_login_at = utcnow()
        self.last_login_ip = ip_address
        self.failed_login_count = 0
        self.locked_until = None

    def register_failed_login(self, threshold: int = 8, lock_minutes: int = 15) -> None:
        from ..clock import minutes_from_now

        self.failed_login_count = (self.failed_login_count or 0) + 1
        if self.failed_login_count >= threshold:
            self.locked_until = minutes_from_now(lock_minutes)
            self.failed_login_count = 0

    def to_summary(self) -> dict:
        """Compact representation used by the chatbot and the JSON API."""

        return {
            "id": self.public_id,
            "name": self.full_name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "store": self.store.public_id if self.store else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User {self.public_id} {self.email} {self.role}>"
