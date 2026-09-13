"""
UPS-guideline shipping rate calculator.

Origin is fixed at 110 Inner Campus Drive, Austin, TX 78705 (zip3 "787"),
per the project spec. Real UPS retail rates require a business account and
live Rating API access, so this implements UPS's published *methodology*
(dimensional weight, zone-based pricing, service tiers) as a self-contained
calculator:

  1. Dimensional weight = (L x W x H) / 139  [UPS domestic divisor, inches -> lb]
  2. Billable weight = max(actual weight, dimensional weight), rounded up to
     the next whole pound.
  3. Zone (2-8) is estimated from how far the destination zip3 prefix is from
     the origin zip3 (787). This is the same rough zip3-distance heuristic
     many shipping estimators use in place of UPS's licensed zone charts.
  4. Cost = (base fee + per-lb zone rate x billable weight) x service
     multiplier.

# ponytail: zone-by-zip3-delta is an approximation, not UPS's licensed zone
# chart. Upgrade path: swap ZONE_BREAKPOINTS/zone lookup for UPS's real
# origin-to-destination zone chart (or call the live UPS Rating API) once
# UPS developer credentials are available.
"""

import math

from .schemas import ShippingOption

ORIGIN_ZIP3 = 787  # 110 Inner Campus Drive, Austin, TX 78705

DIM_DIVISOR = 139.0
BASE_FEE_CENTS = 850

# per-pound rate (cents) by zone, roughly tracking UPS Ground published tiers
ZONE_PER_LB_CENTS = {2: 85, 3: 95, 4: 105, 5: 120, 6: 135, 7: 155, 8: 180}
ZONE_BREAKPOINTS = [50, 130, 230, 330, 430, 530]  # zip3 delta upper bounds for zones 2..7; beyond -> zone 8

SERVICES = {
    "ground": {"label": "UPS Ground", "multiplier": 1.0, "days": "3-5 business days"},
    "three_day_select": {"label": "UPS 3 Day Select", "multiplier": 1.6, "days": "3 business days"},
    "second_day_air": {"label": "UPS 2nd Day Air", "multiplier": 2.4, "days": "2 business days"},
    "next_day_air": {"label": "UPS Next Day Air", "multiplier": 4.0, "days": "1 business day"},
}


class InvalidShippingInput(ValueError):
    pass


def _zone_for_zip(dest_zip: str) -> int:
    digits = "".join(ch for ch in dest_zip if ch.isdigit())
    if len(digits) < 5:
        raise InvalidShippingInput("Destination zip code must be 5 digits")
    dest_zip3 = int(digits[:3])
    delta = abs(dest_zip3 - ORIGIN_ZIP3)
    for zone, breakpoint in zip(range(2, 8), ZONE_BREAKPOINTS):
        if delta <= breakpoint:
            return zone
    return 8


def billable_weight_lb(total_weight_oz: float, length_in: float, width_in: float, height_in: float) -> int:
    actual_lb = total_weight_oz / 16.0
    dimensional_lb = (length_in * width_in * height_in) / DIM_DIVISOR
    return max(1, math.ceil(max(actual_lb, dimensional_lb)))


def quote_all_services(
    dest_zip: str, total_weight_oz: float, length_in: float, width_in: float, height_in: float
) -> list[ShippingOption]:
    zone = _zone_for_zip(dest_zip)
    weight_lb = billable_weight_lb(total_weight_oz, length_in, width_in, height_in)
    per_lb = ZONE_PER_LB_CENTS[zone]

    quotes = []
    for service_key, cfg in SERVICES.items():
        base_cost = BASE_FEE_CENTS + per_lb * weight_lb
        cost_cents = round(base_cost * cfg["multiplier"])
        quotes.append(
            ShippingOption(
                service=service_key,
                label=cfg["label"],
                cost_cents=cost_cents,
                est_business_days=cfg["days"],
            )
        )
    return quotes


def quote_service(
    dest_zip: str, service: str, total_weight_oz: float, length_in: float, width_in: float, height_in: float
) -> ShippingOption:
    if service not in SERVICES:
        raise InvalidShippingInput(f"Unknown shipping service '{service}'")
    for option in quote_all_services(dest_zip, total_weight_oz, length_in, width_in, height_in):
        if option.service == service:
            return option
    raise InvalidShippingInput("Could not compute shipping rate")
