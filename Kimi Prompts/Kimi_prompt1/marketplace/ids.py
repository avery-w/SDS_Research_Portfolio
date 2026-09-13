"""Identifier generation and slug helpers.

Public identifiers are random, URL-safe and prefixed by entity type so an
exposed ID never leaks row counts or lets anyone enumerate other records.
"""

from __future__ import annotations

import re
import secrets
import unicodedata
from datetime import datetime

SLUG_STRIP = re.compile(r"[^a-z0-9]+")
MULTI_DASH = re.compile(r"-{2,}")

# Ambiguous characters are excluded so an order number can be read over the
# phone without confusion between O/0 and I/1.
REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_public_id(prefix: str, length: int = 12) -> str:
    """Return e.g. ``prd_9fK2mQ7pLx4A``."""

    token = secrets.token_urlsafe(length)
    cleaned = re.sub(r"[^A-Za-z0-9]", "", token)[:length]
    if len(cleaned) < length:
        cleaned = (cleaned + secrets.token_hex(length))[:length]
    return f"{prefix}_{cleaned}"


def new_reference(length: int = 8) -> str:
    """Human-transcribable uppercase reference code."""

    return "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(length))


def new_order_number(now: datetime | None = None) -> str:
    """Return a marketplace order number such as ``MP-2609-4KX7QP``."""

    moment = now or datetime.utcnow()
    return f"MP-{moment:%y%m}-{new_reference(6)}"


def new_return_number(now: datetime | None = None) -> str:
    moment = now or datetime.utcnow()
    return f"RT-{moment:%y%m}-{new_reference(6)}"


def new_quote_reference() -> str:
    return f"QT-{new_reference(10)}"


def slugify(value: str, max_length: int = 90) -> str:
    """ASCII slug suitable for a URL path segment."""

    if not value:
        return ""
    normalised = unicodedata.normalize("NFKD", str(value))
    ascii_only = normalised.encode("ascii", "ignore").decode("ascii").lower()
    slug = SLUG_STRIP.sub("-", ascii_only).strip("-")
    slug = MULTI_DASH.sub("-", slug)
    return slug[:max_length].strip("-")


def unique_slug(base: str, taken: set[str], max_length: int = 90) -> str:
    """Return ``base`` slugified, suffixed with ``-2``, ``-3`` ... on conflict."""

    candidate = slugify(base, max_length) or "item"
    if candidate not in taken:
        return candidate
    suffix = 2
    while True:
        trimmed = candidate[: max_length - len(str(suffix)) - 1]
        attempt = f"{trimmed}-{suffix}"
        if attempt not in taken:
            return attempt
        suffix += 1


def new_session_key() -> str:
    return secrets.token_urlsafe(24)


def new_token(prefix: str = "tok") -> tuple[str, str]:
    """Return ``(prefix + secret, secret)`` for API tokens.

    Only the full value is ever shown to the user; the database stores a hash
    of the secret half.
    """

    secret = secrets.token_urlsafe(32)
    return f"{prefix}_{secret}", secret
