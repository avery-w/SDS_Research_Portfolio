"""UPS shipping rates, computed per UPS published guidelines.

Rules applied (UPS Rate and Service Guide):
  * Each dimension is rounded to the nearest whole inch.
  * Dimensional weight = L x W x H / 139 (daily rates divisor), rounded up to the next pound.
  * Billable weight = the greater of actual weight (rounded up) and dimensional weight.
  * Package limits: 150 lb actual, 108 in length, 165 in length + girth.
  * Zone comes from the distance between origin and destination ZIP codes.
  * Residential delivery surcharge per package, then the fuel surcharge on top.
"""
import math
import re
from functools import lru_cache

ORIGIN = {"street": "110 Inner Campus Drive", "city": "Austin", "state": "TX", "zip": "78705"}

DIM_DIVISOR = 139
MAX_WEIGHT_LB = 150
MAX_LENGTH_IN = 108
MAX_LENGTH_PLUS_GIRTH_IN = 165
RESIDENTIAL_CENTS = 585

# (max miles, zone). Anything farther is zone 8.
ZONE_MILES = [(150, 2), (300, 3), (600, 4), (1000, 5), (1400, 6), (1800, 7)]

# UPS Ground, cents: (first lb, each additional lb) by zone.
# ponytail: approximated rate card, swap for the UPS Rating API if you need your negotiated rates.
GROUND = {2: (1150, 60), 3: (1210, 75), 4: (1270, 95), 5: (1320, 120), 6: (1390, 150), 7: (1430, 175), 8: (1490, 205)}
SERVICES = {
    "ground": ("UPS Ground", 1.0),
    "3day": ("UPS 3 Day Select", 1.9),
    "2day": ("UPS 2nd Day Air", 2.6),
    "nextday": ("UPS Next Day Air", 4.2),
}


def billable_weight(weight_lb, length, width, height):
    dims = sorted((round(length), round(width), round(height)), reverse=True)
    if weight_lb > MAX_WEIGHT_LB:
        raise ValueError(f"Packages over {MAX_WEIGHT_LB} lb cannot ship via UPS.")
    if dims[0] > MAX_LENGTH_IN or dims[0] + 2 * (dims[1] + dims[2]) > MAX_LENGTH_PLUS_GIRTH_IN:
        raise ValueError("Package exceeds UPS size limits.")
    dim_weight = math.ceil(dims[0] * dims[1] * dims[2] / DIM_DIVISOR)
    return max(math.ceil(weight_lb), dim_weight, 1)


def zone_for_miles(miles):
    return next((zone for limit, zone in ZONE_MILES if miles <= limit), 8)


@lru_cache(maxsize=1)
def _geo():
    import pgeocode  # downloads the GeoNames US ZIP table on first use, then caches it on disk
    return pgeocode.GeoDistance("us")


def zone_for_zip(dest_zip):
    if not re.fullmatch(r"\d{5}", dest_zip or ""):
        raise ValueError("Enter a 5 digit US ZIP code.")
    km = _geo().query_postal_code(ORIGIN["zip"], dest_zip)
    if math.isnan(km):
        raise ValueError("Unknown ZIP code.")
    return zone_for_miles(km * 0.621371)


def quote_packages(packages, zone, fuel_pct):
    """packages: list of (weight_lb, L, W, H). Returns {service: cents} for the whole shipment."""
    first, extra = GROUND[zone]
    rates = {}
    for code, (_, multiplier) in SERVICES.items():
        total = 0
        for pkg in packages:
            weight = billable_weight(*pkg)
            total += round((first + extra * (weight - 1)) * multiplier) + RESIDENTIAL_CENTS
        rates[code] = round(total * (1 + fuel_pct / 100))
    return rates


if __name__ == "__main__":
    assert billable_weight(2.2, 10, 10, 10) == 8  # 1000/139 = 7.19 -> 8 lb dim weight beats 3 lb actual
    assert billable_weight(20, 6, 6, 6) == 20
    assert billable_weight(0.1, 1, 1, 1) == 1
    for bad in [(151, 1, 1, 1), (1, 109, 1, 1), (1, 60, 30, 30)]:
        try:
            billable_weight(*bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    assert [zone_for_miles(m) for m in (10, 151, 700, 5000)] == [2, 3, 5, 8]
    q = quote_packages([(1, 5, 5, 5)], 2, 0)
    assert q["ground"] == 1150 + 585 and q["nextday"] == round(1150 * 4.2) + 585
    assert quote_packages([(1, 5, 5, 5)] * 2, 2, 10)["ground"] == round(2 * 1735 * 1.1)
    print("shipping ok")
