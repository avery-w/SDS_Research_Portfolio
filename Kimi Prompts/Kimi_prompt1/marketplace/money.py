"""Money helpers.

All monetary values are stored as integer cents so that no floating point
rounding error can ever reach an invoice or a payout.

Note: class name is ``Currency`` to stay out of the way of the builtin.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTS = Decimal("1")


class Currency:
    """Immutable container for a currency code and its display symbol."""

    __slots__ = ("code", "symbol", "decimal_places")

    def __init__(self, code: str = "USD", symbol: str = "$", decimal_places: int = 2):
        self.code = code
        self.symbol = symbol
        self.decimal_places = decimal_places

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Currency({self.code!r})"

    def format(self, cents: int | None, include_symbol: bool = True) -> str:
        if cents is None:
            cents = 0
        quantised = (Decimal(int(cents)) / Decimal(100)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        body = f"{quantised:,.2f}"
        if not include_symbol:
            return body
        negative = body.startswith("-")
        if negative:
            body = body[1:]
        rendered = f"{self.symbol}{body}"
        return f"-{rendered}" if negative else rendered


USD = Currency("USD", "$", 2)


def format_cents(cents: int | None, currency: Currency = USD) -> str:
    """Format integer cents as a display string, e.g. ``$1,234.50``."""

    return currency.format(cents)


def cents_to_decimal(cents: int) -> Decimal:
    return (Decimal(int(cents)) / Decimal(100)).quantize(CENTS)


def decimal_to_cents(value: Decimal | float | int | str) -> int:
    """Convert a decimal money value to integer cents, rounding half up."""

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return 0
    return int(
        (decimal_value * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def parse_money_to_cents(raw: str | None) -> int:
    """Parse user input such as ``"$1,299.99"`` into integer cents.

    Returns ``0`` for empty input. Raises ``ValueError`` for junk so callers
    can turn it into a 400 response instead of silently charging the wrong
    amount.
    """

    if raw is None:
        return 0
    cleaned = str(raw).strip()
    if not cleaned:
        return 0
    cleaned = cleaned.replace("$", "").replace(",", "").replace(" ", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    try:
        value = Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{raw!r} is not a valid money amount") from exc
    if value != value.quantize(Decimal("0.01")):
        raise ValueError("money amounts may have at most two decimal places")
    return decimal_to_cents(value)


def percentage_of(cents: int, rate: float) -> int:
    """Return ``rate`` (a fraction, e.g. 0.0825) of ``cents`` in cents."""

    return int(
        (Decimal(int(cents)) * Decimal(str(rate))).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def apply_discount_cents(
    subtotal_cents: int,
    *,
    discount_type: str,
    value: int,
    max_discount_cents: int | None = None,
) -> int:
    """Compute the discount amount in cents for a coupon definition."""

    if subtotal_cents <= 0:
        return 0
    if discount_type == "percent":
        amount = percentage_of(subtotal_cents, value / 100.0)
    elif discount_type == "fixed":
        amount = int(value)
    else:
        return 0
    if max_discount_cents:
        amount = min(amount, int(max_discount_cents))
    return max(0, min(amount, subtotal_cents))


def split_cents(total_cents: int, weights: list[int]) -> list[int]:
    """Split ``total_cents`` across ``weights`` with no lost or invented cent.

    The largest-remainder method keeps ``sum(result) == total_cents`` exactly,
    which matters when an order is split across several stores.
    """

    if not weights:
        return []
    weight_sum = sum(weights)
    if weight_sum <= 0:
        base = total_cents // len(weights)
        result = [base] * len(weights)
        result[-1] += total_cents - sum(result)
        return result

    raw = [Decimal(int(total_cents)) * Decimal(w) / Decimal(weight_sum) for w in weights]
    floored = [int(value) for value in raw]
    remainder = total_cents - sum(floored)
    order = sorted(
        range(len(raw)), key=lambda i: raw[i] - floored[i], reverse=True
    )
    for index in order[:remainder]:
        floored[index] += 1
    return floored
