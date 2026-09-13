"""Time helpers.

The whole application stores naive UTC datetimes: SQLite has no timezone type
and mixing aware and naive values is a reliable source of bugs. Every value is
converted at the edges (display, parsing) instead.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

UTC = timezone.utc

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR


def utcnow() -> datetime:
    """Naive UTC "now", safe to store in a DateTime column."""

    return datetime.now(UTC).replace(tzinfo=None)


def as_aware(moment: datetime | None) -> datetime | None:
    """Attach UTC to a naive datetime coming out of the database."""

    if moment is None:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def at_utc_noon(day: date) -> datetime:
    return datetime.combine(day, time(12, 0, 0))


def days_from_now(days: int) -> datetime:
    return utcnow() + timedelta(days=days)


def minutes_from_now(minutes: int) -> datetime:
    return utcnow() + timedelta(minutes=minutes)


def iso(moment: datetime | None) -> str | None:
    """Serialise for JSON with an explicit UTC offset."""

    if moment is None:
        return None
    return as_aware(moment).isoformat().replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string into a naive UTC datetime."""

    if not value:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(UTC).replace(tzinfo=None)


def humanise(moment: datetime | None) -> str:
    """Render a compact, readable relative time such as ``3 hours ago``."""

    if moment is None:
        return "never"
    delta_seconds = int((utcnow() - moment).total_seconds())
    future = delta_seconds < 0
    seconds = abs(delta_seconds)
    if seconds < 45:
        return "in a moment" if future else "just now"
    for limit, unit, divisor in (
        (90, "minute", MINUTE),
        (90 * MINUTE, "hour", HOUR),
        (36 * HOUR, "day", DAY),
        (30 * DAY, "month", 30 * DAY),
        (365 * DAY, "year", 365 * DAY),
    ):
        if seconds < limit:
            count = max(1, round(seconds / divisor))
            plural = "" if count == 1 else "s"
            if future:
                return f"in {count} {unit}{plural}"
            return f"{count} {unit}{plural} ago"
    return format_datetime(moment)


def format_datetime(moment: datetime | None, fmt: str = "%b %d, %Y at %H:%M UTC") -> str:
    if moment is None:
        return "-"
    return moment.strftime(fmt)


def format_date(moment: datetime | date | None, fmt: str = "%b %d, %Y") -> str:
    if moment is None:
        return "-"
    return moment.strftime(fmt)


def format_date_input(moment: datetime | date | None) -> str:
    """Value for an ``<input type="date">``."""

    if moment is None:
        return ""
    return moment.strftime("%Y-%m-%d")


def start_of_day(moment: datetime) -> datetime:
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def day_buckets(days: int, end: datetime | None = None) -> list[date]:
    """Return ``days`` consecutive calendar days ending at ``end``."""

    anchor = start_of_day(end or utcnow()).date()
    return [anchor - timedelta(days=offset) for offset in range(days - 1, -1, -1)]


def estimated_delivery(business_days: int, from_moment: datetime | None = None) -> date:
    """Add ``business_days`` skipping Saturdays and Sundays (UPS air/Ground)."""

    cursor = (from_moment or utcnow()).date()
    remaining = max(0, int(business_days))
    while remaining > 0:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            remaining -= 1
    return cursor
