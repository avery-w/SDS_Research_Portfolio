"""Typed, administrator-editable platform settings.

Every knob the platform exposes has an entry in ``DEFAULTS``. That registry is
the single source of truth: it seeds the database on first run, drives the
admin settings screen, and validates incoming values so a bad edit is rejected
with a readable message instead of corrupting the runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..extensions import db
from ..models.enums import SettingValueType
from ..models.support import PlatformSetting

# Categories double as section headings on the settings screen.
CATEGORY_COMMERCE = "commerce"
CATEGORY_SHIPPING = "shipping"
CATEGORY_MARKETPLACE = "marketplace"
CATEGORY_CHATBOT = "chatbot"
CATEGORY_MODERATION = "moderation"

CATEGORY_LABELS = {
    CATEGORY_COMMERCE: "Commerce",
    CATEGORY_SHIPPING: "Shipping and UPS rating",
    CATEGORY_MARKETPLACE: "Marketplace rules",
    CATEGORY_CHATBOT: "Assistant",
    CATEGORY_MODERATION: "Trust and moderation",
}


@dataclass(frozen=True)
class SettingDefinition:
    """One configurable value and everything needed to render and validate it."""

    key: str
    label: str
    category: str
    value_type: str
    default: Any
    description: str = ""
    is_public: bool = False
    sort_order: int = 0
    minimum: float | None = None
    maximum: float | None = None


DEFAULTS: tuple[SettingDefinition, ...] = (
    # -- commerce ---------------------------------------------------------
    SettingDefinition(
        "commission_rate",
        "Marketplace commission",
        CATEGORY_COMMERCE,
        SettingValueType.DECIMAL,
        0.08,
        "Fraction of each item subtotal the marketplace keeps.",
        minimum=0.0,
        maximum=0.5,
        sort_order=10,
    ),
    SettingDefinition(
        "default_tax_rate",
        "Default sales tax rate",
        CATEGORY_COMMERCE,
        SettingValueType.DECIMAL,
        0.0825,
        "Applied to taxable subtotal when a destination has no specific rate.",
        minimum=0.0,
        maximum=0.25,
        sort_order=20,
    ),
    SettingDefinition(
        "free_shipping_threshold_cents",
        "Free shipping threshold",
        CATEGORY_COMMERCE,
        SettingValueType.INTEGER,
        7500,
        "Store subtotal, in cents, above which ground shipping is free. 0 disables it.",
        is_public=True,
        minimum=0,
        sort_order=30,
    ),
    SettingDefinition(
        "currency",
        "Currency",
        CATEGORY_COMMERCE,
        SettingValueType.STRING,
        "USD",
        "ISO-4217 code shown across the marketplace.",
        is_public=True,
        sort_order=40,
    ),
    SettingDefinition(
        "return_window_days",
        "Return window (days)",
        CATEGORY_COMMERCE,
        SettingValueType.INTEGER,
        30,
        "How long after delivery a customer may open a return.",
        is_public=True,
        minimum=0,
        maximum=120,
        sort_order=50,
    ),
    # -- shipping ---------------------------------------------------------
    SettingDefinition(
        "ups_fuel_surcharge_rate",
        "UPS fuel surcharge",
        CATEGORY_SHIPPING,
        SettingValueType.DECIMAL,
        0.1475,
        "Fraction added to the transportation charge. UPS publishes this weekly.",
        minimum=0.0,
        maximum=0.5,
        sort_order=10,
    ),
    SettingDefinition(
        "ups_residential_surcharge_cents",
        "Residential surcharge (cents)",
        CATEGORY_SHIPPING,
        SettingValueType.INTEGER,
        660,
        "Charged per parcel delivered to a residential address.",
        minimum=0,
        sort_order=20,
    ),
    SettingDefinition(
        "ups_origin_postal_code",
        "Ship-from ZIP",
        CATEGORY_SHIPPING,
        SettingValueType.STRING,
        "78705",
        "Origin postal code for platform-fulfilled shipments.",
        sort_order=30,
    ),
    SettingDefinition(
        "ups_handling_days",
        "Handling days",
        CATEGORY_SHIPPING,
        SettingValueType.INTEGER,
        1,
        "Business days added before a parcel enters the UPS network.",
        is_public=True,
        minimum=0,
        maximum=10,
        sort_order=40,
    ),
    SettingDefinition(
        "ups_quote_ttl_minutes",
        "Shipping quote lifetime (minutes)",
        CATEGORY_SHIPPING,
        SettingValueType.INTEGER,
        45,
        "How long a quoted rate stays valid at checkout.",
        minimum=5,
        maximum=1440,
        sort_order=50,
    ),
    # -- marketplace ------------------------------------------------------
    SettingDefinition(
        "marketplace_open",
        "Marketplace accepting orders",
        CATEGORY_MARKETPLACE,
        SettingValueType.BOOLEAN,
        True,
        "Turn off to pause checkout across the whole platform.",
        is_public=True,
        sort_order=10,
    ),
    SettingDefinition(
        "new_sellers_auto_approve",
        "Auto-approve new stores",
        CATEGORY_MARKETPLACE,
        SettingValueType.BOOLEAN,
        True,
        "When off, a new store stays pending until an administrator approves it.",
        sort_order=20,
    ),
    SettingDefinition(
        "customer_registration_open",
        "Open customer registration",
        CATEGORY_MARKETPLACE,
        SettingValueType.BOOLEAN,
        True,
        "When off, only administrators can create customer accounts.",
        is_public=True,
        sort_order=30,
    ),
    SettingDefinition(
        "max_items_per_order",
        "Maximum items per order",
        CATEGORY_MARKETPLACE,
        SettingValueType.INTEGER,
        50,
        "Guards against runaway carts.",
        minimum=1,
        maximum=500,
        sort_order=40,
    ),
    # -- assistant --------------------------------------------------------
    SettingDefinition(
        "chatbot_enabled",
        "Assistant enabled",
        CATEGORY_CHATBOT,
        SettingValueType.BOOLEAN,
        True,
        "Show the assistant widget and answer chat requests.",
        is_public=True,
        sort_order=10,
    ),
    SettingDefinition(
        "chatbot_use_llm",
        "Use the language model",
        CATEGORY_CHATBOT,
        SettingValueType.BOOLEAN,
        False,
        "When off, the deterministic rule engine answers every message.",
        sort_order=20,
    ),
    SettingDefinition(
        "chatbot_greeting",
        "Greeting",
        CATEGORY_CHATBOT,
        SettingValueType.STRING,
        "Hi! I can help you find products, track an order, or get you in touch with a seller.",
        "First line shown when the widget opens.",
        is_public=True,
        sort_order=30,
    ),
    SettingDefinition(
        "chatbot_handoff_keywords",
        "Human handoff keywords",
        CATEGORY_CHATBOT,
        SettingValueType.JSON,
        ["human", "agent", "representative", "manager", "complaint"],
        "Messages containing any of these escalate straight to a person.",
        sort_order=40,
    ),
    # -- moderation -------------------------------------------------------
    SettingDefinition(
        "auto_hide_flagged_reviews",
        "Auto-hide flagged reviews",
        CATEGORY_MODERATION,
        SettingValueType.BOOLEAN,
        False,
        "Hide a review as soon as it is reported, pending review.",
        sort_order=10,
    ),
    SettingDefinition(
        "listing_requires_image",
        "Require a product photo",
        CATEGORY_MODERATION,
        SettingValueType.BOOLEAN,
        True,
        "A product cannot be published without at least one image.",
        sort_order=20,
    ),
    SettingDefinition(
        "max_product_images",
        "Images per product",
        CATEGORY_MODERATION,
        SettingValueType.INTEGER,
        8,
        "Upper bound on uploaded product photos.",
        minimum=1,
        maximum=24,
        sort_order=30,
    ),
)

DEFINITIONS_BY_KEY: dict[str, SettingDefinition] = {d.key: d for d in DEFAULTS}


class SettingError(ValueError):
    """Raised when a submitted setting value cannot be accepted."""

    def __init__(self, key: str, message: str):
        super().__init__(message)
        self.key = key
        self.message = message


# --------------------------------------------------------------------------
# Coercion
# --------------------------------------------------------------------------


def coerce_value(definition: SettingDefinition, raw: Any) -> Any:
    """Convert submitted input into the declared type, or raise ``SettingError``."""

    value_type = definition.value_type
    key = definition.key

    if value_type == SettingValueType.BOOLEAN:
        if isinstance(raw, bool):
            return raw
        if raw is None:
            return False
        text = str(raw).strip().lower()
        if text in {"on", "true", "1", "yes", "enabled"}:
            return True
        if text in {"off", "false", "0", "no", "disabled", "", "none"}:
            return False
        raise SettingError(key, f"{definition.label} must be on or off.")

    if value_type == SettingValueType.INTEGER:
        try:
            number = int(str(raw).strip())
        except (TypeError, ValueError):
            raise SettingError(key, f"{definition.label} must be a whole number.")
        return _check_bounds(definition, number)

    if value_type == SettingValueType.DECIMAL:
        try:
            number = float(str(raw).strip())
        except (TypeError, ValueError):
            raise SettingError(key, f"{definition.label} must be a number.")
        return _check_bounds(definition, number)

    if value_type == SettingValueType.JSON:
        import json

        if isinstance(raw, (list, dict)):
            return raw
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            raise SettingError(key, f"{definition.label} must be valid JSON.")

    text = "" if raw is None else str(raw).strip()
    return _check_length(definition, text)


def _check_bounds(definition: SettingDefinition, number):
    if definition.minimum is not None and number < definition.minimum:
        raise SettingError(
            definition.key,
            f"{definition.label} must be at least {definition.minimum}.",
        )
    if definition.maximum is not None and number > definition.maximum:
        raise SettingError(
            definition.key,
            f"{definition.label} must be at most {definition.maximum}.",
        )
    return number


def _check_length(definition: SettingDefinition, text: str) -> str:
    if len(text) > 500:
        raise SettingError(
            definition.key, f"{definition.label} must be 500 characters or fewer."
        )
    return text


# --------------------------------------------------------------------------
# Access
# --------------------------------------------------------------------------


def ensure_defaults() -> int:
    """Create any missing setting rows. Returns how many were created."""

    existing = {key for (key,) in db.session.query(PlatformSetting.key).all()}
    created = 0
    for definition in DEFAULTS:
        if definition.key in existing:
            continue
        db.session.add(
            PlatformSetting(
                key=definition.key,
                value_json={"value": definition.default},
                value_type=definition.value_type,
                category=definition.category,
                label=definition.label,
                description=definition.description,
                is_public=definition.is_public,
                sort_order=definition.sort_order,
            )
        )
        created += 1
    if created:
        db.session.commit()
    return created


def get_record(key: str) -> PlatformSetting | None:
    return (
        db.session.query(PlatformSetting)
        .filter(PlatformSetting.key == key)
        .one_or_none()
    )


def get(key: str, fallback: Any = None) -> Any:
    """Return a setting's typed value, falling back to its declared default."""

    record = get_record(key)
    if record is not None:
        return record.value
    definition = DEFINITIONS_BY_KEY.get(key)
    if definition is not None:
        return definition.default
    return fallback


def get_bool(key: str, fallback: bool = False) -> bool:
    value = get(key, fallback)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_int(key: str, fallback: int = 0) -> int:
    try:
        return int(get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def get_float(key: str, fallback: float = 0.0) -> float:
    try:
        return float(get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def get_str(key: str, fallback: str = "") -> str:
    value = get(key, fallback)
    return fallback if value is None else str(value)


def get_list(key: str, fallback: list | None = None) -> list:
    value = get(key, fallback or [])
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(",") if part.strip()]
    return list(fallback or [])


def all_records() -> list[PlatformSetting]:
    return (
        db.session.query(PlatformSetting)
        .order_by(PlatformSetting.category, PlatformSetting.sort_order, PlatformSetting.key)
        .all()
    )


def grouped_records() -> list[tuple[str, str, list[PlatformSetting]]]:
    """Return ``[(category_key, category_label, records), ...]`` for the UI."""

    buckets: dict[str, list[PlatformSetting]] = {}
    for record in all_records():
        buckets.setdefault(record.category, []).append(record)
    ordered = sorted(
        buckets.items(),
        key=lambda item: min((r.sort_order for r in item[1]), default=0),
    )
    return [
        (key, CATEGORY_LABELS.get(key, key.replace("_", " ").title()), records)
        for key, records in ordered
    ]


def public_settings() -> dict[str, Any]:
    """Only the settings that are safe to expose to a template or the API."""

    return {
        record.key: record.value
        for record in all_records()
        if record.is_public
    }


def update_many(submitted: dict[str, Any], actor=None) -> tuple[list[str], list[SettingError]]:
    """Apply a batch of edits. Returns ``(changed_keys, errors)``.

    Validation runs for every key before anything is written, so a single bad
    field cannot leave the settings half-applied.
    """

    staged: list[tuple[PlatformSetting, Any]] = []
    errors: list[SettingError] = []

    for key, raw in submitted.items():
        definition = DEFINITIONS_BY_KEY.get(key)
        record = get_record(key)
        if definition is None and record is None:
            errors.append(SettingError(key, f"Unknown setting {key!r}."))
            continue
        if record is None:
            record = PlatformSetting(
                key=definition.key,
                value_type=definition.value_type,
                category=definition.category,
                label=definition.label,
                description=definition.description,
                is_public=definition.is_public,
                sort_order=definition.sort_order,
            )
            db.session.add(record)
        try:
            coerced = coerce_value(definition or _definition_from(record), raw)
        except SettingError as exc:
            errors.append(exc)
            continue
        if record.value != coerced or record.raw_value != coerced:
            staged.append((record, coerced))

    if errors:
        db.session.rollback()
        return [], errors

    changed: list[str] = []
    for record, coerced in staged:
        record.set_value(coerced, actor=actor)
        changed.append(record.key)

    if changed:
        db.session.commit()
    return changed, []


def _definition_from(record: PlatformSetting) -> SettingDefinition:
    """Build a definition for a row that predates the registry."""

    return SettingDefinition(
        key=record.key,
        label=record.label,
        category=record.category,
        value_type=record.value_type or SettingValueType.STRING,
        default=record.value,
        description=record.description or "",
        is_public=record.is_public,
        sort_order=record.sort_order,
    )


def set_value(key: str, raw: Any, actor=None) -> Any:
    """Set one value, raising ``SettingError`` when it is not acceptable."""

    definition = DEFINITIONS_BY_KEY.get(key)
    record = get_record(key)
    if definition is None and record is None:
        raise SettingError(key, f"Unknown setting {key!r}.")
    if record is None:
        record = PlatformSetting(
            key=definition.key,
            value_type=definition.value_type,
            category=definition.category,
            label=definition.label,
            description=definition.description,
            is_public=definition.is_public,
            sort_order=definition.sort_order,
        )
        db.session.add(record)
    coerced = coerce_value(definition or _definition_from(record), raw)
    record.set_value(coerced, actor=actor)
    db.session.commit()
    return coerced
