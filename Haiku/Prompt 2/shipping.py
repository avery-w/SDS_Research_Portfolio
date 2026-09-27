"""UPS-style shipping rate engine.

Implements the UPS rating rules that decide a price: package weight and size
limits, dimensional weight, billable weight rounding, distance-based zones,
Additional Handling / Large Package / residential surcharges and a fuel
surcharge. Every shipment originates at 110 Inner Campus Drive, Austin, TX 78705.
"""
import math
from datetime import date, timedelta

ORIGIN = {
    "name": "Forty Acres Market Fulfillment",
    "street": "110 Inner Campus Drive",
    "city": "Austin",
    "state": "TX",
    "zip": "78705",
}
ORIGIN_LATLON = (30.2862, -97.7394)

# UPS package limits and rating constants (daily rates).
MAX_WEIGHT_LB = 150
MAX_LENGTH_IN = 108
MAX_LENGTH_PLUS_GIRTH_IN = 165
DIM_DIVISOR = 139
LARGE_PACKAGE_MIN_BILLABLE_LB = 90

ADDITIONAL_HANDLING_DIMS = 28.75   # longest side > 48 in or second-longest > 30 in
ADDITIONAL_HANDLING_WEIGHT = 43.50  # actual weight > 50 lb
LARGE_PACKAGE = 240.00              # length + girth > 130 in or longest side > 96 in

# Base price for a 1 lb package and each additional lb, UPS Ground, zones 2-8.
# ponytail: approximates the published UPS daily rate chart, swap in the UPS Rating API for live contract rates.
GROUND_BASE = {2: 10.20, 3: 10.85, 4: 11.70, 5: 12.40, 6: 12.95, 7: 13.45, 8: 14.05}
GROUND_PER_LB = {2: 0.55, 3: 0.75, 4: 1.05, 5: 1.35, 6: 1.60, 7: 1.85, 8: 2.10}
GROUND_DAYS = {2: 1, 3: 2, 4: 3, 5: 3, 6: 4, 7: 4, 8: 5}

# code: (name, multiplier on the ground rate, business days, available to AK/HI)
SERVICES = {
    "03": ("UPS Ground", 1.0, None, False),
    "12": ("UPS 3 Day Select", 2.2, 3, True),
    "02": ("UPS 2nd Day Air", 2.9, 2, True),
    "01": ("UPS Next Day Air", 4.6, 1, True),
}
NONCONTIGUOUS_MULTIPLIER = 1.6  # AK/HI air rates relative to zone 8

# ZIP3 ranges -> representative point. Texas is split by region because the
# origin is in Austin and zone accuracy matters most nearby.
# ponytail: ZIP3 centroids, not per-ZIP geocoding; load the UPS zone chart for 78705 if exact zones matter.
ZIP3 = [
    (10, 27, "MA", 42.36, -71.06), (28, 29, "RI", 41.82, -71.41), (30, 38, "NH", 43.0, -71.5),
    (39, 49, "ME", 44.3, -69.8), (50, 59, "VT", 44.3, -72.6), (60, 69, "CT", 41.6, -72.7),
    (70, 89, "NJ", 40.2, -74.5), (100, 149, "NY", 41.5, -74.5), (150, 196, "PA", 40.6, -77.2),
    (197, 199, "DE", 39.2, -75.5), (200, 205, "DC", 38.9, -77.03), (206, 219, "MD", 39.0, -76.7),
    (220, 246, "VA", 37.5, -78.5), (247, 268, "WV", 38.6, -80.6), (270, 289, "NC", 35.6, -79.4),
    (290, 299, "SC", 33.9, -80.9), (300, 319, "GA", 33.2, -83.6), (320, 349, "FL", 28.1, -81.6),
    (350, 369, "AL", 32.8, -86.8), (370, 385, "TN", 35.9, -86.4), (386, 397, "MS", 32.7, -89.7),
    (398, 399, "GA", 31.6, -84.2), (400, 427, "KY", 37.7, -85.3), (430, 458, "OH", 40.3, -82.8),
    (460, 479, "IN", 39.9, -86.3), (480, 499, "MI", 43.3, -84.5), (500, 528, "IA", 42.0, -93.2),
    (530, 549, "WI", 44.3, -89.6), (550, 567, "MN", 45.7, -93.9), (570, 577, "SD", 44.3, -99.4),
    (580, 588, "ND", 47.5, -100.5), (590, 599, "MT", 46.9, -110.4), (600, 629, "IL", 40.3, -89.0),
    (630, 658, "MO", 38.5, -92.3), (660, 679, "KS", 38.5, -97.5), (680, 693, "NE", 41.1, -98.3),
    (700, 714, "LA", 31.1, -91.9), (716, 729, "AR", 34.9, -92.4), (730, 749, "OK", 35.5, -97.5),
    (750, 753, "TX", 32.78, -96.80), (754, 759, "TX", 32.35, -95.30), (760, 762, "TX", 32.75, -97.33),
    (763, 767, "TX", 31.55, -97.15), (768, 769, "TX", 31.46, -100.44), (770, 779, "TX", 29.76, -95.37),
    (780, 782, "TX", 29.42, -98.49), (783, 785, "TX", 27.2, -97.8), (786, 789, "TX", 30.27, -97.74),
    (790, 794, "TX", 34.3, -101.8), (795, 797, "TX", 32.2, -100.5), (798, 799, "TX", 31.76, -106.49),
    (800, 816, "CO", 39.0, -105.5), (820, 831, "WY", 42.8, -107.3), (832, 838, "ID", 44.2, -114.5),
    (840, 847, "UT", 40.2, -111.9), (850, 865, "AZ", 33.7, -111.9), (870, 884, "NM", 34.8, -106.2),
    (885, 885, "TX", 31.76, -106.49), (889, 898, "NV", 37.5, -116.9), (900, 961, "CA", 36.1, -119.7),
    (967, 968, "HI", 21.3, -157.8), (970, 979, "OR", 44.6, -122.1), (980, 994, "WA", 47.4, -121.5),
    (995, 999, "AK", 61.2, -149.9),
]


class ShippingError(ValueError):
    """Raised for input UPS cannot ship (bad ZIP, oversize item, unavailable service)."""


def _sorted_dims(l, w, h):
    return sorted((l, w, h), reverse=True)


def length_plus_girth(l, w, h):
    a, b, c = _sorted_dims(l, w, h)
    return a + 2 * (b + c)


def check_item(weight_lb, l, w, h):
    """Reject a single unit that could never fit in one UPS package."""
    if weight_lb > MAX_WEIGHT_LB:
        raise ShippingError(f"UPS packages are limited to {MAX_WEIGHT_LB} lb.")
    if max(l, w, h) > MAX_LENGTH_IN:
        raise ShippingError(f"UPS packages are limited to {MAX_LENGTH_IN} in on the longest side.")
    if length_plus_girth(l, w, h) > MAX_LENGTH_PLUS_GIRTH_IN:
        raise ShippingError(f"UPS packages are limited to {MAX_LENGTH_PLUS_GIRTH_IN} in length + girth.")


def pack(items):
    """Greedy packer. items: [{weight_lb, length_in, width_in, height_in, qty}] -> packages.

    Units are stacked on their smallest side; a new box starts when the next unit
    would push the box past a UPS limit.
    """
    units = []
    for it in items:
        dims = _sorted_dims(it["length_in"], it["width_in"], it["height_in"])
        check_item(it["weight_lb"], *dims)
        units += [(it["weight_lb"], dims)] * it["qty"]
    units.sort(key=lambda u: u[0], reverse=True)

    packages = []
    for weight, (l, w, h) in units:
        for p in packages:
            nl, nw, nh = max(p["l"], l), max(p["w"], w), p["h"] + h
            if p["weight"] + weight <= MAX_WEIGHT_LB and max(nl, nw, nh) <= MAX_LENGTH_IN \
                    and length_plus_girth(nl, nw, nh) <= MAX_LENGTH_PLUS_GIRTH_IN:
                p.update(weight=p["weight"] + weight, l=nl, w=nw, h=nh)
                break
        else:
            packages.append({"weight": weight, "l": l, "w": w, "h": h})
    return packages


def _miles(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def zone_for(zip_code):
    """Return (zone, state, miles). zone is 2-8, or 'AK'/'HI' for noncontiguous states."""
    if not (isinstance(zip_code, str) and len(zip_code) >= 5 and zip_code[:5].isdigit()):
        raise ShippingError("Enter a valid 5-digit US ZIP code.")
    z3 = int(zip_code[:3])
    for lo, hi, state, lat, lon in ZIP3:
        if lo <= z3 <= hi:
            miles = _miles(ORIGIN_LATLON, (lat, lon))
            if state in ("AK", "HI"):
                return state, state, round(miles)
            for zone, limit in ((2, 150), (3, 300), (4, 600), (5, 1000), (6, 1400), (7, 1800)):
                if miles <= limit:
                    return zone, state, round(miles)
            return 8, state, round(miles)
    raise ShippingError("We only ship UPS to the 50 US states and DC (no PO/military or territory ZIPs).")


def add_business_days(start, days):
    d = start
    while days:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days -= 1
    return d


def rate_package(pkg, zone):
    """Billable weight + surcharges for one package; returns (billable_lb, ground_transport, surcharges)."""
    l, w, h = (math.ceil(x) for x in _sorted_dims(pkg["l"], pkg["w"], pkg["h"]))
    dim_weight = math.ceil(l * w * h / DIM_DIVISOR)
    billable = max(math.ceil(pkg["weight"]), dim_weight, 1)
    surcharges = {}
    lg = l + 2 * (w + h)
    if lg > 130 or l > 96:
        surcharges["Large Package"] = LARGE_PACKAGE
        billable = max(billable, LARGE_PACKAGE_MIN_BILLABLE_LB)
    else:
        if l > 48 or w > 30:
            surcharges["Additional Handling (dimensions)"] = ADDITIONAL_HANDLING_DIMS
        if pkg["weight"] > 50:
            surcharges["Additional Handling (weight)"] = ADDITIONAL_HANDLING_WEIGHT
    z = 8 if zone in ("AK", "HI") else zone
    transport = GROUND_BASE[z] + GROUND_PER_LB[z] * (billable - 1)
    return billable, transport, surcharges, (l, w, h)


def quote(dest_zip, items, *, fuel_pct, residential_fee, today=None):
    """Quote every UPS service for shipping `items` from the Austin origin to `dest_zip`.

    All money in the result is integer cents.
    """
    if not items:
        raise ShippingError("Nothing to ship.")
    zone, state, miles = zone_for(dest_zip)
    packages = pack(items)
    today = today or date.today()

    rated = [rate_package(p, zone) for p in packages]
    services = []
    for code, (name, mult, days, noncontiguous_ok) in SERVICES.items():
        if zone in ("AK", "HI"):
            if not noncontiguous_ok:
                continue
            mult *= NONCONTIGUOUS_MULTIPLIER
        transit = days or GROUND_DAYS[zone]
        transport = sum(r[1] for r in rated) * mult
        surcharge = sum(sum(r[2].values()) for r in rated)
        residential = residential_fee * len(packages)
        fuel = (transport + surcharge + residential) * fuel_pct / 100
        total = transport + surcharge + residential + fuel
        services.append({
            "code": code,
            "name": name,
            "transit_days": transit,
            "delivery_date": add_business_days(today, transit).isoformat(),
            "cents": round(total * 100),
            "breakdown_cents": {
                "transportation": round(transport * 100),
                "surcharges": round(surcharge * 100),
                "residential": round(residential * 100),
                "fuel": round(fuel * 100),
            },
        })
    return {
        "origin": ORIGIN,
        "destination": {"zip": dest_zip[:5], "state": state, "zone": zone, "distance_mi": miles},
        "packages": [
            {"weight_lb": round(p["weight"], 2), "dims_in": list(r[3]), "billable_lb": r[0],
             "surcharges": sorted(r[2])}
            for p, r in zip(packages, rated)
        ],
        "services": services,
    }
