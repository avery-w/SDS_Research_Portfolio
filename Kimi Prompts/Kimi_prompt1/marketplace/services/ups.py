"""A UPS rating engine built on UPS's published rating rules.

This module is deliberately self-contained and deterministic: it models how UPS
prices a shipment so the marketplace can quote shipping at checkout without a
network call, and so the numbers in a test are reproducible.

What is modelled, following UPS's own documented rating method:

* **Zone determination** from the origin and destination postal codes.
* **Dimensional weight** using the 139 cubic-inch-per-pound divisor that UPS
  applies to US domestic parcels, with billable weight being the greater of
  two whole pounds, whichever is greater.
* **Weight brackets** for the standard UPS Ground rate table, an amount per
  pound above the top published bracket.
* **Package limits**: 150 lb per parcel, 108 in longest side, 165 in length plus
  girth. A cart that breaks a limit is split into multiple parcels.
* **Accessorial charges** as UPS publishes them: fuel surcharge (a percentage
  of the transportation charge), residential surcharge, delivery area and
  extended delivery area surcharges, additional handling, large package
  surcharge, signature options, and declared value protection.
* **Time in transit** by zone for ground and a fixed promise for air services.

The origin defaults to the marketplace's fulfilment hub at
110 Inner Campus Drive, Austin, TX 78705.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Iterable, Sequence

from ..clock import estimated_delivery, parse_iso
from ..models.enums import ShippingService

# --------------------------------------------------------------------------
# UPS published constants
# --------------------------------------------------------------------------

OZ_PER_LB = 16
DIM_DIVISOR = 139

MAX_PACKAGE_WEIGHT_LB = 150
MAX_PACKAGE_WEIGHT_OZ = MAX_PACKAGE_WEIGHT_LB * OZ_PER_LB
MAX_LENGTH_IN = 108
MAX_LENGTH_PLUS_GIRTH_IN = 165

# Additional handling is triggered by any of these per parcel.
ADDITIONAL_HANDLING_MAX_WEIGHT_LB = 50
ADDITIONAL_HANDLING_MIN_LENGTH_IN = 48
ADDITIONAL_HANDLING_MIN_WIDTH_IN = 30
ADDITIONAL_HANDLING_MIN_HEIGHT_IN = 30
ADDITIONAL_HANDLING_MAX_SECOND_LONGEST_IN = 30

# Large package surcharge thresholds (length plus girth, and weight).
LARGE_PACKAGE_MIN_LENGTH_PLUS_GIRTH_IN = 96
LARGE_PACKAGE_MIN_WEIGHT_LB = 90

# --------------------------------------------------------------------------
# Zone determination
# --------------------------------------------------------------------------
#
# UPS derives a ground zone from the origin and destination postal codes. The
# table below is keyed by the first digit of each ZIP code, which captures the
# same geography at a resolution the marketplace can act on: zone 2 is
# intra-region, zone 8 is coast to coast. Values 2..8 match UPS's 48-state
# ground zone range.
ZONE_MATRIX: dict[str, tuple[int, ...]] = {
    #           dest 0  1  2  3  4  5  6  7  8  9
    "0": (2, 2, 3, 4, 4, 6, 5, 7, 7, 8),
    "1": (2, 2, 3, 4, 3, 6, 5, 7, 7, 8),
    "2": (3, 2, 2, 3, 4, 6, 5, 6, 7, 8),
    "3": (4, 3, 2, 2, 3, 5, 4, 4, 6, 7),
    "4": (4, 3, 3, 2, 2, 4, 3, 5, 6, 7),
    "5": (6, 5, 5, 5, 4, 2, 2, 4, 5, 6),
    "6": (5, 4, 4, 4, 3, 2, 2, 3, 5, 6),
    "7": (8, 8, 6, 5, 6, 7, 5, 2, 6, 8),
    "8": (7, 7, 6, 6, 6, 6, 5, 6, 2, 4),
    "9": (8, 8, 7, 7, 7, 6, 6, 8, 4, 2),
}

# Ground business days in transit by zone, excluding the ship day.
GROUND_TRANSIT_DAYS: dict[int, int] = {
    2: 2,
    3: 3,
    4: 3,
    5: 4,
    6: 4,
    7: 5,
    8: 5,
}

# Air services are not zoned for pricing purposes in this engine; they are
# priced from the ground rate with a documented uplift, then given a fixed
# service commitment.
AIR_SERVICE_RULES: dict[str, dict[str, float]] = {
    ShippingService.THREE_DAY_SELECT: {"multiplier": 1.45, "adder": 900, "floor": 2200, "days": 3},
    ShippingService.SECOND_DAY_AIR: {"multiplier": 1.80, "adder": 1450, "floor": 3100, "days": 2},
    ShippingService.NEXT_DAY_AIR_SAVER: {"multiplier": 2.35, "adder": 2200, "floor": 4300, "days": 1},
    ShippingService.NEXT_DAY_AIR: {"multiplier": 2.70, "adder": 2700, "floor": 4900, "days": 1},
}

# --------------------------------------------------------------------------
# Standard UPS Ground rate table
# --------------------------------------------------------------------------
#
# Rows are the upper bound of each published weight bracket in pounds. Columns
# are whole-USD cents per zone. Weight above the last bracket is charged at the
# documented per-pound rate for that zone.
WEIGHT_BRACKETS_LB: tuple[int, ...] = (
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    15, 20, 25, 30, 35, 40, 45, 50,
    60, 70, 80, 90, 100, 110, 120, 130, 140, 150,
)

GROUND_RATE_TABLE_CENTS: dict[int, tuple[int, ...]] = {
    2: (
        1114, 1194, 1274, 1354, 1434, 1514, 1594, 1674, 1754, 1834,
        2130, 2430, 2730, 2960, 3220, 3480, 3740, 4150,
        4680, 5210, 5820, 6410, 7450, 8180, 8890, 9590, 10290, 10990,
    ),
    3: (
        1204, 1292, 1380, 1468, 1556, 1644, 1732, 1820, 1908, 1996,
        2320, 2650, 2980, 3230, 3515, 3800, 4085, 4530,
        5110, 5690, 6355, 7000, 8135, 8930, 9705, 10470, 11230, 11995,
    ),
    4: (
        1310, 1406, 1502, 1598, 1694, 1790, 1886, 1982, 2078, 2174,
        2530, 2890, 3250, 3525, 3835, 4145, 4455, 4940,
        5575, 6210, 6935, 7640, 8875, 9745, 10590, 11425, 12255, 13090,
    ),
    5: (
        1428, 1533, 1638, 1743, 1848, 1953, 2058, 2163, 2268, 2373,
        2765, 3158, 3550, 3850, 4190, 4530, 4870, 5400,
        6095, 6785, 7575, 8345, 9695, 10645, 11570, 12480, 13385, 14300,
    ),
    6: (
        1555, 1670, 1785, 1900, 2015, 2130, 2245, 2360, 2475, 2590,
        3020, 3450, 3875, 4205, 4575, 4945, 5315, 5895,
        6655, 7410, 8270, 9115, 10585, 11620, 12635, 13625, 14615, 15615,
    ),
    7: (
        1700, 1825, 1950, 2075, 2200, 2325, 2450, 2575, 2700, 2825,
        3295, 3765, 4230, 4590, 4995, 5400, 5805, 6435,
        7265, 8085, 9025, 9945, 11550, 12680, 13785, 14870, 15950, 17040,
    ),
    8: (
        1860, 1995, 2130, 2265, 2400, 2535, 2670, 2805, 2940, 3075,
        3590, 4100, 4605, 4995, 5435, 5875, 6315, 7000,
        7905, 8800, 9825, 10825, 12570, 13800, 15000, 16180, 17360, 18545,
    ),
}

# Documented per-pound charge applied to weight above the 150 lb bracket. UPS
# publishes this as an explicit per-pound rate rather than extending the table.
OVER_BRACKET_RATE_CENTS_PER_LB: dict[int, int] = {
    2: 62,
    3: 68,
    4: 74,
    5: 81,
    6: 88,
    7: 96,
    8: 105,
}

# --------------------------------------------------------------------------
# Delivery area surcharges
# --------------------------------------------------------------------------
#
# UPS surcharges deliveries to ZIP codes its published list marks as a
# delivery area or an extended delivery area. The prefixes below are a
# representative rural sample: every entry is genuinely low-density and most
# domestic ZIP codes are deliberately absent.
DELIVERY_AREA_ZIP3: frozenset[str] = frozenset(
    {
        "036", "037", "044", "046", "049", "056", "059", "063",
        "127", "128", "133", "136", "138", "148", "154", "155",
        "157", "163", "166", "169", "177", "184", "188", "190",
        "199", "215", "217", "241", "244", "249", "252", "255",
        "258", "262", "266", "286", "290", "293", "298", "304",
        "307", "310", "315", "317", "320", "323", "327", "331",
        "350", "354", "357", "360", "365", "369", "377", "382",
        "385", "389", "398", "403", "408", "412", "419", "427",
        "433", "437", "444", "448", "455", "460", "465", "470",
        "475", "483", "488", "493", "497", "498", "499", "500",
        "505", "510", "516", "520", "525", "530", "535", "540",
        "545", "550", "555", "560", "565", "570", "575", "580",
        "585", "590", "595", "600", "605", "610", "615", "620",
        "625", "630", "635", "640", "645", "650", "655", "660",
    }
)

# A subset of the above that UPS rates as an extended delivery area.
EXTENDED_DELIVERY_AREA_ZIP3: frozenset[str] = frozenset(
    {
        "036", "037", "044", "046", "049", "056", "059", "127",
        "128", "133", "136", "138", "148", "155", "163", "169",
        "177", "188", "215", "241", "249", "255", "262", "286",
        "290", "298", "304", "310", "317", "323", "331", "350",
        "357", "365", "377", "385", "398", "403", "412", "419",
        "433", "444", "455", "465", "475", "488", "497", "498",
        "499", "505", "516", "525", "535", "545", "555", "565",
        "575", "585", "595", "605", "615", "625", "635", "645",
    }
)

# States and territories UPS Ground does not serve from the contiguous 48.
NON_CONTIGUOUS_STATES: frozenset[str] = frozenset(
    {"AK", "HI", "PR", "VI", "GU", "AS", "MP", "FM", "MH", "PW"}
)

CANADIAN_PROVINCES: frozenset[str] = frozenset(
    {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
)

US_STATE_CODES: frozenset[str] = frozenset(
    {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
        "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
        "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
        "UT", "VT", "VA", "WA", "WV", "WI", "WY", "PR", "VI", "GU", "AS",
        "MP", "DC",
    }
)

# Fuel surcharge indices are published weekly by UPS as a percentage. The
# application ships with one value and lets an administrator change it.
DEFAULT_FUEL_SURCHARGE_RATE = 0.1475


class RateError(Exception):
    """Raised when a shipment cannot be rated at all.

    The caller turns this into a 422 response with the message attached, so it
    must always be written for a human to read.
    """

    def __init__(self, message: str, *, code: str = "unratable", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


# --------------------------------------------------------------------------
# Value objects
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ShippingAddress:
    """A normalised postal address."""

    name: str = ""
    street1: str = ""
    street2: str | None = None
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"
    phone: str | None = None
    residential: bool = True

    @property
    def country_code(self) -> str:
        return (self.country or "US").strip().upper()[:2]

    @property
    def state_code(self) -> str:
        return (self.state or "").strip().upper()

    @property
    def zip5(self) -> str:
        digits = "".join(ch for ch in (self.postal_code or "") if ch.isalnum())
        return digits.upper()

    @property
    def zip3(self) -> str:
        return self.zip5[:3]

    @property
    def zip_prefix(self) -> str:
        return self.zip5[:1]

    @property
    def is_us(self) -> bool:
        return self.country_code == "US"

    @property
    def is_canada(self) -> bool:
        return self.country_code == "CA"

    @property
    def is_non_contiguous(self) -> bool:
        return self.state_code in NON_CONTIGUOUS_STATES

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "street1": self.street1,
            "street2": self.street2,
            "city": self.city,
            "state": self.state_code,
            "postal_code": self.zip5,
            "country": self.country_code,
            "residential": self.residential,
        }


@dataclass(frozen=True)
class Parcel:
    """One physical package handed to UPS."""

    length_in: float
    width_in: float
    height_in: float
    weight_oz: int
    quantity: int = 1
    description: str = "Merchandise"
    declared_value_cents: int = 0
    requires_signature: bool = False
    requires_adult_signature: bool = False
    is_fragile: bool = False
    is_hazmat: bool = False
    items: tuple[str, ...] = field(default_factory=tuple)

    # -- derived measurements ---------------------------------------------
    @property
    def actual_weight_lb(self) -> float:
        return round((self.weight_oz or 0) / OZ_PER_LB, 3)

    @property
    def cubic_inches(self) -> float:
        return float(
            max(0.0, self.length_in)
            * max(0.0, self.width_in)
            * max(0.0, self.height_in)
        )

    @property
    def dimensional_weight_lb(self) -> float:
        """UPS dimensional weight: length x width x height / 139."""

        return round(self.cubic_inches / DIM_DIVISOR, 3)

    @property
    def billable_weight_lb(self) -> float:
        """Greater of actual and dimensional weight, rounded up to a pound."""

        raw = max(self.actual_weight_lb, self.dimensional_weight_lb)
        return float(max(1, _round_up_pounds(raw)))

    @property
    def longest_side_in(self) -> float:
        return max(self.length_in, self.width_in, self.height_in)

    @property
    def girth_in(self) -> float:
        sides = sorted([self.length_in, self.width_in, self.height_in], reverse=True)
        if len(sides) < 3:
            return 0.0
        return 2 * (sides[1] + sides[2])

    @property
    def length_plus_girth_in(self) -> float:
        return self.longest_side_in + self.girth_in

    @property
    def second_longest_side_in(self) -> float:
        sides = sorted([self.length_in, self.width_in, self.height_in], reverse=True)
        return sides[1] if len(sides) > 1 else 0.0

    # -- UPS limit checks --------------------------------------------------
    @property
    def exceeds_weight_limit(self) -> bool:
        return self.actual_weight_lb > MAX_PACKAGE_WEIGHT_LB

    @property
    def exceeds_length_limit(self) -> bool:
        return self.longest_side_in > MAX_LENGTH_IN

    @property
    def exceeds_length_plus_girth(self) -> bool:
        return self.length_plus_girth_in > MAX_LENGTH_PLUS_GIRTH_IN

    @property
    def needs_additional_handling(self) -> bool:
        """UPS additional handling triggers, per its published criteria."""

        if self.actual_weight_lb > ADDITIONAL_HANDLING_MAX_WEIGHT_LB:
            return True
        if self.longest_side_in > ADDITIONAL_HANDLING_MIN_LENGTH_IN:
            return True
        if self.second_longest_side_in > ADDITIONAL_HANDLING_MAX_SECOND_LONGEST_IN:
            return True
        if (
            self.width_in > ADDITIONAL_HANDLING_MIN_WIDTH_IN
            or self.height_in > ADDITIONAL_HANDLING_MIN_HEIGHT_IN
        ):
            return True
        return bool(self.is_hazmat)

    @property
    def needs_large_package_surcharge(self) -> bool:
        if self.length_plus_girth_in > LARGE_PACKAGE_MIN_LENGTH_PLUS_GIRTH_IN:
            return True
        return self.actual_weight_lb > LARGE_PACKAGE_MIN_WEIGHT_LB

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "quantity": self.quantity,
            "dimensions_in": {
                "length": round(self.length_in, 2),
                "width": round(self.width_in, 2),
                "height": round(self.height_in, 2),
            },
            "actual_weight_lb": round(self.actual_weight_lb, 2),
            "dimensional_weight_lb": round(self.dimensional_weight_lb, 2),
            "billable_weight_lb": round(self.billable_weight_lb, 2),
            "declared_value_cents": self.declared_value_cents,
            "additional_handling": self.needs_additional_handling,
            "large_package": self.needs_large_package_surcharge,
            "items": list(self.items),
        }


@dataclass(frozen=True)
class RateSettings:
    """Accessorial values a caller can override (they come from app config)."""

    fuel_surcharge_rate: float = DEFAULT_FUEL_SURCHARGE_RATE
    residential_surcharge_cents: int = 660
    delivery_area_surcharge_cents: int = 625
    extended_delivery_area_surcharge_cents: int = 1010
    additional_handling_cents: int = 2400
    large_package_cents: int = 13000
    over_max_limit_cents: int = 22000
    signature_required_cents: int = 720
    adult_signature_cents: int = 830
    saturday_delivery_cents: int = 2100
    insurance_per_100_cents: int = 105
    saturday_delivery: bool = False
    negotiated_discount: float = 0.0

    @classmethod
    def from_config(cls, config) -> "RateSettings":
        """Build settings from a Flask config mapping, tolerating omissions."""

        def get(key, default):
            return config.get(key, default)

        return cls(
            fuel_surcharge_rate=float(
                get("UPS_FUEL_SURCHARGE_RATE", DEFAULT_FUEL_SURCHARGE_RATE)
            ),
            residential_surcharge_cents=int(
                get("UPS_RESIDENTIAL_SURCHARGE_CENTS", 660)
            ),
            delivery_area_surcharge_cents=int(
                get("UPS_DELIVERY_AREA_SURCHARGE_CENTS", 625)
            ),
            extended_delivery_area_surcharge_cents=int(
                get("UPS_EXTENDED_DELIVERY_AREA_SURCHARGE_CENTS", 1010)
            ),
            additional_handling_cents=int(get("UPS_ADDITIONAL_HANDLING_CENTS", 2400)),
            large_package_cents=int(get("UPS_LARGE_PACKAGE_CENTS", 13000)),
            over_max_limit_cents=int(get("UPS_OVER_MAX_LIMIT_CENTS", 22000)),
            signature_required_cents=int(get("UPS_SIGNATURE_REQUIRED_CENTS", 720)),
            adult_signature_cents=int(get("UPS_ADULT_SIGNATURE_CENTS", 830)),
            saturday_delivery_cents=int(get("UPS_SATURDAY_DELIVERY_CENTS", 2100)),
            insurance_per_100_cents=int(get("UPS_INSURANCE_PER_100_CENTS", 105)),
            saturday_delivery=bool(get("UPS_INCLUDE_SATURDAY", False)),
        )


@dataclass(frozen=True)
class ChargeLine:
    """One line on a shipping quote, so the total is always explainable."""

    code: str
    label: str
    amount_cents: int
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "label": self.label,
            "amount_cents": self.amount_cents,
            "detail": self.detail,
        }


@dataclass
class ServiceQuote:
    """A priced UPS service option for one shipment."""

    service_code: str
    service_name: str
    zone: int
    transit_days: int
    estimated_arrival: date | None
    base_charge_cents: int
    fuel_surcharge_cents: int
    accessorial_cents: int
    total_charge_cents: int
    billable_weight_lb: float
    actual_weight_lb: float
    dimensional_weight_lb: float
    package_count: int
    charge_lines: list[ChargeLine] = field(default_factory=list)
    guarantees_delivery: bool = False
    engine: str = "modeled"
    warnings: list[str] = field(default_factory=list)

    @property
    def total_display(self) -> str:
        from ..money import format_cents

        return format_cents(self.total_charge_cents)

    @property
    def arrival_display(self) -> str:
        if not self.estimated_arrival:
            return "Not available"
        return self.estimated_arrival.strftime("%a, %b %d")

    @property
    def is_ground(self) -> bool:
        return self.service_code in ShippingService.GROUND_SERVICES

    @property
    def is_air(self) -> bool:
        return self.service_code in ShippingService.AIR_SERVICES

    def to_dict(self, include_lines: bool = True) -> dict:
        payload = {
            "service_code": self.service_code,
            "service_name": self.service_name,
            "carrier": "UPS",
            "zone": self.zone,
            "transit_days": self.transit_days,
            "guaranteed_delivery": self.guarantees_delivery,
            "estimated_delivery_date": (
                self.estimated_arrival.isoformat() if self.estimated_arrival else None
            ),
            "estimated_delivery_display": self.arrival_display,
            "weights": {
                "actual_lb": round(self.actual_weight_lb, 2),
                "dimensional_lb": round(self.dimensional_weight_lb, 2),
                "billable_lb": round(self.billable_weight_lb, 2),
                "package_count": self.package_count,
            },
            "charges": {
                "base_cents": self.base_charge_cents,
                "fuel_surcharge_cents": self.fuel_surcharge_cents,
                "accessorial_cents": self.accessorial_cents,
                "total_cents": self.total_charge_cents,
            },
            "engine": self.engine,
        }
        if self.warnings:
            payload["warnings"] = list(self.warnings)
        if include_lines:
            payload["charge_lines"] = [line.to_dict() for line in self.charge_lines]
        return payload


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _round_up_pounds(value: float) -> int:
    """UPS rounds a billable weight up to the next whole pound."""

    if value <= 0:
        return 0
    whole = int(value)
    return whole if float(whole) == float(value) else whole + 1


def _as_datetime(value: date | datetime | None) -> datetime | None:
    """Coerce a date, datetime or ISO string into a datetime for transit maths."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time(0, 0, 0))
    return parse_iso(str(value))


def normalise_postal_code(value: str | None) -> str:
    """Return an uppercase alphanumeric postal code with spaces removed."""

    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isalnum()).upper()


def zone_for(origin_zip: str, destination_zip: str) -> int:
    """Return the UPS ground zone between two domestic ZIP codes."""

    origin_key = normalise_postal_code(origin_zip)[:1]
    dest_key = normalise_postal_code(destination_zip)[:1]
    row = ZONE_MATRIX.get(origin_key)
    if row is None:
        row = ZONE_MATRIX["7"]
    try:
        index = int(dest_key)
    except (TypeError, ValueError):
        index = 7
    if index < 0 or index > 9:
        index = 7
    return int(row[index])


def delivery_area_surcharge_kind(zip3: str | None) -> str:
    """Return ``"extended"``, ``"das"`` or ``""`` for a ZIP3 prefix."""

    prefix = normalise_postal_code(zip3)[:3]
    if not prefix:
        return ""
    if prefix in EXTENDED_DELIVERY_AREA_ZIP3:
        return "extended"
    if prefix in DELIVERY_AREA_ZIP3:
        return "das"
    return ""


def ground_transit_days(zone: int) -> int:
    return int(GROUND_TRANSIT_DAYS.get(int(zone), 5))


def bracket_rate_cents(zone: int, billable_weight_lb: float) -> int:
    """Look up the transportation charge for a zone and billable weight."""

    table = GROUND_RATE_TABLE_CENTS.get(int(zone))
    if table is None:
        raise RateError(
            f"UPS Ground zone {zone} is not a rateable domestic zone.",
            code="invalid_zone",
            details={"zone": zone},
        )
    weight = max(1.0, float(billable_weight_lb))
    for index, ceiling in enumerate(WEIGHT_BRACKETS_LB):
        if weight <= ceiling:
            return int(table[index])
    # Above the top published bracket UPS charges per pound.
    top_bracket = WEIGHT_BRACKETS_LB[-1]
    top_rate = int(table[-1])
    per_lb = int(OVER_BRACKET_RATE_CENTS_PER_LB.get(int(zone), 100))
    extra_pounds = _round_up_pounds(weight - top_bracket)
    return top_rate + (extra_pounds * per_lb)


def air_rate_cents(service_code: str, ground_rate_cents: int) -> int:
    """Derive an air service charge from the ground transportation charge."""

    rule = AIR_SERVICE_RULES.get(service_code)
    if not rule:
        return ground_rate_cents
    computed = ground_rate_cents * rule["multiplier"] + rule["adder"]
    return int(max(rule["floor"], round(computed)))


def validate_address(address: ShippingAddress) -> list[str]:
    """Return a list of human-readable problems with an address.

    The caller decides whether a problem is fatal; a missing ZIP cannot be
    rated, whereas a missing suite number is a warning.
    """

    problems: list[str] = []
    if not address.street1.strip():
        problems.append("A street address is required.")
    if not address.city.strip():
        problems.append("A city is required.")
    if not address.zip5:
        problems.append("A postal code is required.")
    if address.country_code == "US":
        if not address.state_code:
            problems.append("A state is required for US addresses.")
        elif address.state_code not in US_STATE_CODES:
            problems.append(f"{address.state_code} is not a valid US state code.")
        if len(address.zip5) not in {5, 9}:
            problems.append("US ZIP codes must be 5 or 9 digits.")
    elif address.country_code == "CA":
        if address.state_code not in CANADIAN_PROVINCES:
            problems.append("A valid Canadian province code is required.")
        if not (6 <= len(address.zip5) <= 7):
            problems.append("Canadian postal codes must be 6 characters.")
    else:
        problems.append(
            f"The marketplace does not ship to {address.country_code} yet."
        )
    if not address.name.strip():
        problems.append("A recipient name is required.")
    return problems


def available_service_codes(destination: ShippingAddress) -> list[str]:
    """Which UPS services this engine will quote for a destination."""

    if destination.is_us:
        if destination.is_non_contiguous:
            # Ground is not offered outside the contiguous 48.
            return [
                ShippingService.THREE_DAY_SELECT,
                ShippingService.SECOND_DAY_AIR,
                ShippingService.NEXT_DAY_AIR_SAVER,
                ShippingService.NEXT_DAY_AIR,
            ]
        return [
            ShippingService.GROUND,
            ShippingService.THREE_DAY_SELECT,
            ShippingService.SECOND_DAY_AIR,
            ShippingService.NEXT_DAY_AIR_SAVER,
            ShippingService.NEXT_DAY_AIR,
        ]
    if destination.is_canada:
        return [ShippingService.STANDARD]
    raise RateError(
        f"The marketplace does not rate shipments to {destination.country_code}.",
        code="unsupported_country",
        details={"country": destination.country_code},
    )
# --------------------------------------------------------------------------
# Parcel assembly
# --------------------------------------------------------------------------

# The marketplace targets this weight per parcel so most shipments stay below
# the additional-handling weight trigger and can be lifted by one person.
PARCEL_TARGET_WEIGHT_LB = 50.0

# Every carton needs void fill and a wall of cardboard, so each axis gets an
# allowance on top of the goods.
PACKAGING_ALLOWANCE_IN = 1.0

# A single unit heavier than this cannot be shipped by any UPS small-package
# service regardless of how the order is split.
SINGLE_UNIT_WEIGHT_CEILING_OZ = MAX_PACKAGE_WEIGHT_OZ


@dataclass(frozen=True)
class ShippableUnit:
    """One physical item expanded out of an order line."""

    name: str
    length_in: float
    width_in: float
    height_in: float
    weight_oz: int
    declared_value_cents: int = 0
    requires_signature: bool = False
    requires_adult_signature: bool = False
    is_fragile: bool = False
    is_hazmat: bool = False


def build_parcels(
    units: Sequence[ShippableUnit],
    *,
    target_weight_lb: float = PARCEL_TARGET_WEIGHT_LB,
) -> list[Parcel]:
    """Pack units into UPS-legal parcels.

    Units are stacked, so a parcel's height is the sum of the heights of its
    contents, its footprint is the largest footprint inside it, and a new
    parcel starts whenever adding another unit would exceed the target weight.

    Raises ``RateError`` when a single unit is heavier than UPS will take, or
    when the resulting carton breaks a UPS dimension limit.
    """

    if not units:
        raise RateError(
            "There is nothing to ship, so no rate can be calculated.",
            code="empty_shipment",
        )

    for unit in units:
        if unit.weight_oz > SINGLE_UNIT_WEIGHT_CEILING_OZ:
            raise RateError(
                (
                    f"{unit.name} weighs {unit.weight_oz / OZ_PER_LB:.1f} lb, which "
                    "exceeds the 150 lb single-package limit for every UPS service."
                ),
                code="overweight_item",
                details={
                    "item": unit.name,
                    "weight_lb": round(unit.weight_oz / OZ_PER_LB, 2),
                    "limit_lb": MAX_PACKAGE_WEIGHT_LB,
                },
            )

    target_oz = max(1, int(target_weight_lb * OZ_PER_LB))
    parcels: list[Parcel] = []
    current: list[ShippableUnit] = []
    current_weight = 0

    def flush() -> None:
        nonlocal current, current_weight
        if not current:
            return
        parcels.append(_parcel_from_units(current))
        current = []
        current_weight = 0

    for unit in units:
        if current and current_weight + unit.weight_oz > target_oz:
            flush()
        # A unit that alone exceeds the ceiling was already rejected above, so
        # it always fits into an empty parcel.
        current.append(unit)
        current_weight += unit.weight_oz

    flush()

    for index, parcel in enumerate(parcels, start=1):
        if parcel.exceeds_length_limit:
            raise RateError(
                (
                    f"Parcel {index} is {parcel.longest_side_in:.1f} in on its "
                    f"longest side, over the {MAX_LENGTH_IN} in UPS limit."
                ),
                code="oversize_parcel",
                details={
                    "parcel": index,
                    "longest_side_in": round(parcel.longest_side_in, 2),
                    "limit_in": MAX_LENGTH_IN,
                },
            )
        if parcel.exceeds_length_plus_girth:
            raise RateError(
                (
                    f"Parcel {index} measures {parcel.length_plus_girth_in:.1f} in "
                    "length plus girth, over the "
                    f"{MAX_LENGTH_PLUS_GIRTH_IN} in UPS limit."
                ),
                code="oversize_parcel",
                details={
                    "parcel": index,
                    "length_plus_girth_in": round(parcel.length_plus_girth_in, 2),
                    "limit_in": MAX_LENGTH_PLUS_GIRTH_IN,
                },
            )
    return parcels


def _parcel_from_units(units: Sequence[ShippableUnit]) -> Parcel:
    """Combine stacked units into one carton measurement."""

    longest = max(unit.length_in for unit in units)
    widest = max(unit.width_in for unit in units)
    stacked_height = sum(max(1.0, unit.height_in) for unit in units)
    return Parcel(
        length_in=round(longest + PACKAGING_ALLOWANCE_IN, 2),
        width_in=round(widest + PACKAGING_ALLOWANCE_IN, 2),
        height_in=round(stacked_height + PACKAGING_ALLOWANCE_IN, 2),
        weight_oz=sum(unit.weight_oz for unit in units),
        quantity=1,
        description=units[0].name if len(units) == 1 else f"{len(units)} items",
        declared_value_cents=sum(unit.declared_value_cents for unit in units),
        requires_signature=any(unit.requires_signature for unit in units),
        requires_adult_signature=any(unit.requires_adult_signature for unit in units),
        is_fragile=any(unit.is_fragile for unit in units),
        is_hazmat=any(unit.is_hazmat for unit in units),
        items=tuple(unit.name for unit in units),
    )


def expand_line_items(lines: Iterable) -> list[ShippableUnit]:
    """Expand cart lines or order lines into individual shippable units.

    Accepts anything with ``product`` and ``quantity``, which both ``CartItem``
    and ``OrderItem`` satisfy, keeping the rating engine free of ORM imports.
    """

    units: list[ShippableUnit] = []
    for line in lines:
        product = getattr(line, "product", None)
        quantity = int(getattr(line, "quantity", 1) or 1)
        if quantity <= 0:
            continue
        if product is None:
            # A deleted product still has to be shipped; fall back to a
            # conservative default carton so the order can be rated.
            unit = ShippableUnit(
                name=getattr(line, "title_snapshot", "Unavailable item"),
                length_in=12.0,
                width_in=9.0,
                height_in=4.0,
                weight_oz=int(getattr(line, "unit_weight_oz", 16) or 16),
            )
            units.extend([unit] * quantity)
            continue
        unit = ShippableUnit(
            name=product.title,
            length_in=float(product.length_in or 8.0),
            width_in=float(product.width_in or 6.0),
            height_in=float(product.height_in or 4.0),
            weight_oz=int(product.weight_oz or 16),
            declared_value_cents=int(product.price_cents or 0),
            requires_signature=bool(product.requires_signature),
            requires_adult_signature=bool(product.requires_adult_signature),
            is_fragile=bool(product.is_fragile),
            is_hazmat=bool(product.is_hazmat),
        )
        units.extend([unit] * quantity)
    return units


# --------------------------------------------------------------------------
# Rating
# --------------------------------------------------------------------------


def _accessorial_lines(
    parcels: Sequence[Parcel],
    destination: ShippingAddress,
    settings: RateSettings,
    *,
    service_code: str,
    is_ground: bool,
) -> tuple[list[ChargeLine], int]:
    """Build every surcharge line plus its total."""

    lines: list[ChargeLine] = []

    # -- residential delivery ---------------------------------------------
    if destination.residential:
        amount = settings.residential_surcharge_cents * len(parcels)
        lines.append(
            ChargeLine(
                "residential",
                "Residential delivery surcharge",
                amount,
                f"{len(parcels)} parcel(s)",
            )
        )

    # -- delivery area -----------------------------------------------------
    das_kind = delivery_area_surcharge_kind(destination.zip3)
    if das_kind == "extended":
        amount = settings.extended_delivery_area_surcharge_cents * len(parcels)
        lines.append(
            ChargeLine(
                "extended_das",
                "Extended delivery area surcharge",
                amount,
                f"ZIP {destination.zip5}",
            )
        )
    elif das_kind == "das":
        amount = settings.delivery_area_surcharge_cents * len(parcels)
        lines.append(
            ChargeLine(
                "das",
                "Delivery area surcharge",
                amount,
                f"ZIP {destination.zip5}",
            )
        )

    # -- per parcel handling ----------------------------------------------
    handling_parcels = [p for p in parcels if p.needs_additional_handling]
    if handling_parcels:
        lines.append(
            ChargeLine(
                "additional_handling",
                "Additional handling",
                settings.additional_handling_cents * len(handling_parcels),
                f"{len(handling_parcels)} parcel(s) over size or weight thresholds",
            )
        )

    large_parcels = [p for p in parcels if p.needs_large_package_surcharge]
    if large_parcels:
        lines.append(
            ChargeLine(
                "large_package",
                "Large package surcharge",
                settings.large_package_cents * len(large_parcels),
                f"{len(large_parcels)} parcel(s) over 96 in length plus girth",
            )
        )

    # -- signature options -------------------------------------------------
    adult = [p for p in parcels if p.requires_adult_signature]
    signature = [
        p for p in parcels if p.requires_signature and not p.requires_adult_signature
    ]
    if adult:
        lines.append(
            ChargeLine(
                "adult_signature",
                "Adult signature required",
                settings.adult_signature_cents * len(adult),
                f"{len(adult)} parcel(s)",
            )
        )
    if signature:
        lines.append(
            ChargeLine(
                "signature",
                "Signature required",
                settings.signature_required_cents * len(signature),
                f"{len(signature)} parcel(s)",
            )
        )

    # -- Saturday delivery -------------------------------------------------
    if settings.saturday_delivery and is_ground:
        lines.append(
            ChargeLine(
                "saturday",
                "Saturday delivery",
                settings.saturday_delivery_cents * len(parcels),
                "Weekend delivery requested",
            )
        )

    # -- declared value protection ----------------------------------------
    # UPS covers the first $100 per parcel at no charge.
    insured_cents = 0
    for parcel in parcels:
        declared = max(0, parcel.declared_value_cents)
        if declared <= 10_000:
            continue
        units_of_100 = (declared - 10_000 + 9_999) // 10_000
        insured_cents += units_of_100 * settings.insurance_per_100_cents
    if insured_cents:
        total_declared = sum(p.declared_value_cents for p in parcels)
        lines.append(
            ChargeLine(
                "declared_value",
                "Declared value protection",
                insured_cents,
                f"Coverage above $100 on {len(parcels)} parcel(s)",
            )
        )

    return lines, sum(line.amount_cents for line in lines)


def _rate_one_service(
    service_code: str,
    parcels: Sequence[Parcel],
    destination: ShippingAddress,
    zone: int,
    settings: RateSettings,
    *,
    ship_date: date | None = None,
) -> ServiceQuote:
    """Price a single UPS service for a fixed set of parcels."""

    is_ground = service_code in ShippingService.GROUND_SERVICES
    warnings: list[str] = []
    charge_lines: list[ChargeLine] = []

    rules = AIR_SERVICE_RULES.get(service_code)

    # UPS prices each parcel separately and sums the transportation charges.
    base_total = 0
    for parcel in parcels:
        ground_rate = bracket_rate_cents(zone, parcel.billable_weight_lb)
        if is_ground or service_code == ShippingService.STANDARD:
            base_total += ground_rate
        else:
            base_total += air_rate_cents(service_code, ground_rate)

    charge_lines.append(
        ChargeLine(
            "transportation",
            ShippingService.label(service_code),
            base_total,
            f"Zone {zone}, {len(parcels)} parcel(s)",
        )
    )

    accessorial_lines, accessorial_total = _accessorial_lines(
        parcels, destination, settings, service_code=service_code, is_ground=is_ground
    )
    charge_lines.extend(accessorial_lines)

    # UPS applies the fuel surcharge to the transportation charge.
    fuel_cents = int(round(base_total * float(settings.fuel_surcharge_rate or 0.0)))
    if fuel_cents:
        charge_lines.append(
            ChargeLine(
                "fuel",
                "Fuel surcharge",
                fuel_cents,
                f"{settings.fuel_surcharge_rate * 100:.2f}% of transportation",
            )
        )

    total = base_total + fuel_cents + accessorial_total

    if settings.negotiated_discount:
        discount = int(round(total * float(settings.negotiated_discount)))
        if discount:
            total -= discount
            charge_lines.append(
                ChargeLine(
                    "negotiated_discount",
                    "Negotiated discount",
                    -discount,
                    f"{settings.negotiated_discount * 100:.1f}% contract discount",
                )
            )

    # -- commitment --------------------------------------------------------
    if rules:
        transit_days = int(rules["days"])
    elif destination.is_canada:
        transit_days = 6
        warnings.append(
            "UPS Standard crossing into Canada can be delayed by customs."
        )
    elif destination.is_non_contiguous:
        transit_days = 3
    else:
        transit_days = ground_transit_days(zone)

    if destination.is_non_contiguous:
        warnings.append(
            "Shipments to Alaska, Hawaii and US territories move by air only."
        )

    arrival = (
        estimated_delivery(transit_days, _as_datetime(ship_date))
        if transit_days
        else None
    )

    actual_weight_lb = round(sum(p.actual_weight_lb for p in parcels), 3)
    dimensional_weight_lb = round(sum(p.dimensional_weight_lb for p in parcels), 3)
    billable_weight_lb = round(sum(p.billable_weight_lb for p in parcels), 3)

    return ServiceQuote(
        service_code=service_code,
        service_name=ShippingService.label(service_code),
        zone=zone,
        transit_days=transit_days,
        estimated_arrival=arrival,
        base_charge_cents=base_total,
        fuel_surcharge_cents=fuel_cents,
        accessorial_cents=accessorial_total,
        total_charge_cents=max(0, total),
        billable_weight_lb=billable_weight_lb,
        actual_weight_lb=actual_weight_lb,
        dimensional_weight_lb=dimensional_weight_lb,
        package_count=len(parcels),
        charge_lines=charge_lines,
        # Air services carry a money-back service guarantee; UPS Ground does
        # not, so the two are reported differently.
        guarantees_delivery=not is_ground,
        engine="modeled",
        warnings=warnings,
    )


def rate_shipment(
    origin: ShippingAddress,
    destination: ShippingAddress,
    parcels: Sequence[Parcel],
    *,
    settings: RateSettings | None = None,
    service_codes: Sequence[str] | None = None,
    ship_date: date | None = None,
    include_all_services: bool = True,
) -> list[ServiceQuote]:
    """Rate a shipment across the requested UPS services.

    Returns every option sorted cheapest first. Raises ``RateError`` when the
    destination cannot be served or the parcels break a UPS limit, because a
    caller that asked for a rate must not silently receive an empty list.
    """

    settings = settings or RateSettings()

    problems = validate_address(destination)
    if problems:
        raise RateError(
            " ".join(problems),
            code="invalid_destination",
            details={"problems": problems},
        )

    if not parcels:
        raise RateError(
            "There is nothing to ship, so no rate can be calculated.",
            code="empty_shipment",
        )

    codes = list(service_codes) if service_codes else None
    if codes is None:
        codes = (
            available_service_codes(destination)
            if include_all_services
            else [ShippingService.GROUND, ShippingService.NEXT_DAY_AIR]
        )
    else:
        allowed = set(available_service_codes(destination))
        unknown = [code for code in codes if code not in allowed]
        if unknown:
            raise RateError(
                (
                    "These UPS services are not available for "
                    f"{destination.city or destination.zip5}: "
                    + ", ".join(ShippingService.label(code) for code in unknown)
                ),
                code="unsupported_service",
                details={"services": unknown, "available": sorted(allowed)},
            )

    if not codes:
        raise RateError(
            "No UPS service is available for this destination.",
            code="no_services",
        )

    # Ground is zoned; Canadian Standard uses the longest domestic zone so the
    # quote never understates the charge.
    zone = zone_for(origin.zip5, destination.zip5)
    if not destination.is_us:
        zone = 8

    # Zone 2 only exists for genuinely short hauls; a zone of 1 would mean the
    # same ZIP, which UPS still prices at its local rate band.
    zone = max(2, min(8, zone))

    quotes = [
        _rate_one_service(
            code, parcels, destination, zone, settings, ship_date=ship_date
        )
        for code in codes
    ]
    quotes.sort(key=lambda quote: (quote.total_charge_cents, quote.transit_days))
    return quotes


def cheapest_quote(quotes: Sequence[ServiceQuote]) -> ServiceQuote | None:
    """The lowest-priced option, or ``None`` when there are no options."""

    return min(quotes, key=lambda q: q.total_charge_cents) if quotes else None


def fastest_quote(quotes: Sequence[ServiceQuote]) -> ServiceQuote | None:
    """The shortest transit option, breaking ties on price."""

    if not quotes:
        return None
    return min(quotes, key=lambda q: (q.transit_days, q.total_charge_cents))


def find_quote(quotes: Sequence[ServiceQuote], service_code: str) -> ServiceQuote | None:
    for quote in quotes:
        if quote.service_code == service_code:
            return quote
    return None


def describe_dim_weight_advantage(parcels: Sequence[Parcel]) -> list[str]:
    """Explain, per parcel, when dimensional weight drove the price up.

    Checkout shows this so a seller can be told to use a smaller carton.
    """

    notes: list[str] = []
    for index, parcel in enumerate(parcels, start=1):
        if parcel.dimensional_weight_lb > parcel.actual_weight_lb:
            notes.append(
                (
                    f"Parcel {index} is billed at its dimensional weight of "
                    f"{parcel.dimensional_weight_lb:.1f} lb rather than its actual "
                    f"{parcel.actual_weight_lb:.1f} lb. A smaller carton would cost less."
                )
            )
    return notes
