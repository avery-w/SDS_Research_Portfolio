"""Reusable column groups for the ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..clock import utcnow


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Marks records as deleted without losing the audit trail."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = utcnow()

    def restore(self) -> None:
        self.deleted_at = None


class MoneyMixin:
    """Adds a currency code column; amounts live on the concrete model."""

    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)


def cents_column(default: int = 0, nullable: bool = False):
    """Shortcut for a non-negative integer cents column."""

    return mapped_column(Integer, default=default, nullable=nullable)
