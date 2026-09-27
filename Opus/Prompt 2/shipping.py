"""UPS-style shipping rates, following UPS published rating rules.

Origin is fixed at 110 Inner Campus Drive, Austin, TX 78705. Rating follows the UPS rules:
  * zone from origin->destination distance (UPS zones 2-8; AK/HI are non-contiguous, air only)
  * dimensional weight = L x W x H / 139 (daily rates), dimensions rounded to whole inches
  * billable weight = max(actual, dimensional), rounded up to the next pound
  * limits: 150 lb actual, 108 in length, 165 in length + girth
  * Additional Handling: longest side > 48 in, second side > 30 in, or > 50 lb actual
  * Large Package: length + girth > 130 in or longest side > 96 in (90 lb minimum billable)
  * Residential surcharge and a percentage fuel surcharge on top of transport + accessorials

ponytail: rate card and ZIP3 centroids are approximations of UPS daily rates. For negotiated
account rates, swap `quote()` internals for the UPS Rating API (same inputs and outputs).
"""
import math

ORIGIN = {"street": "110 Inner Campus Drive", "city": "Austin", "state": "TX", "zip": "78705"}
ORIGIN_LATLON = (30.2862, -97.7394)
DIM_DIVISOR = 139

# (zip3 low, zip3 high, state, lat, lon). Big states are split by region so zones stay honest.
ZIP3 = [
    (5, 5, "NY", 40.8, -73.0), (10, 27, "MA", 42.3, -71.8), (28, 29, "RI", 41.7, -71.5),
    (30, 38, "NH", 43.2, -71.5), (39, 49, "ME", 44.7, -69.4), (50, 59, "VT", 44.0, -72.7),
    (60, 69, "CT", 41.6, -72.7), (70, 89, "NJ", 40.2, -74.6), (100, 149, "NY", 42.2, -75.2),
    (150, 196, "PA", 40.9, -77.8), (197, 199, "DE", 39.0, -75.5), (200, 205, "DC", 38.9, -77.0),
    (206, 219, "MD", 39.0, -76.8), (220, 246, "VA", 37.5, -78.8), (247, 268, "WV", 38.6, -80.6),
    (270, 289, "NC", 35.6, -79.4), (290, 299, "SC", 33.9, -80.9), (300, 319, "GA", 32.9, -83.4),
    (320, 339, "FL", 28.6, -81.6), (340, 349, "FL", 26.7, -80.3), (350, 369, "AL", 32.8, -86.8),
    (370, 385, "TN", 35.9, -86.4), (386, 397, "MS", 32.7, -89.7), (398, 399, "GA", 31.5, -84.2),
    (400, 427, "KY", 37.8, -85.3), (430, 458, "OH", 40.3, -82.8), (460, 479, "IN", 39.9, -86.3),
    (480, 499, "MI", 43.3, -84.5), (500, 528, "IA", 42.0, -93.2), (530, 549, "WI", 44.3, -89.6),
    (550, 567, "MN", 45.7, -93.9), (570, 577, "SD", 44.3, -99.4), (580, 588, "ND", 47.5, -100.5),
    (590, 599, "MT", 46.9, -110.4), (600, 629, "IL", 40.3, -89.0), (630, 658, "MO", 38.5, -92.3),
    (660, 679, "KS", 38.5, -97.6), (680, 693, "NE", 41.1, -98.3), (700, 714, "LA", 30.9, -91.9),
    (716, 729, "AR", 34.9, -92.4), (730, 732, "OK", 35.5, -97.5), (733, 733, "TX", 30.3, -97.7),
    (734, 749, "OK", 35.6, -96.9), (750, 753, "TX", 32.8, -96.8), (754, 759, "TX", 32.3, -95.3),
    (760, 762, "TX", 32.8, -97.3), (763, 767, "TX", 31.6, -97.2), (768, 769, "TX", 31.4, -100.4),
    (770, 778, "TX", 29.8, -95.4), (779, 779, "TX", 28.8, -97.0), (780, 782, "TX", 29.4, -98.5),
    (783, 785, "TX", 27.2, -97.9), (786, 789, "TX", 30.3, -97.7), (790, 794, "TX", 34.3, -101.9),
    (795, 796, "TX", 32.4, -99.7), (797, 797, "TX", 32.0, -102.1), (798, 799, "TX", 31.8, -106.4),
    (800, 816, "CO", 39.0, -105.5), (820, 831, "WY", 43.0, -107.5), (832, 838, "ID", 44.2, -114.6),
    (840, 847, "UT", 39.4, -111.7), (850, 865, "AZ", 33.7, -111.9), (870, 884, "NM", 34.5, -106.1),
    (885, 885, "TX", 31.8, -106.4), (889, 898, "NV", 37.5, -116.5), (900, 935, "CA", 34.1, -118.0),
    (936, 961, "CA", 38.3, -121.6), (967, 968, "HI", 21.3, -157.8), (970, 979, "OR", 44.0, -121.5),
    (980, 994, "WA", 47.4, -121.2), (995, 999, "AK", 61.2, -149.9),
]
NONCONTIGUOUS = {"AK", "HI"}

# service: (name, [1 lb rate by zone 2..8], [each additional lb by zone 2..8], [transit days by zone 2..8])
RATES = {
    "GND": ("UPS Ground", [10.20, 10.60, 11.10, 11.50, 11.90, 12.30, 12.90],
            [0.45, 0.60, 0.85, 1.05, 1.30, 1.50, 1.75], [1, 2, 3, 4, 4, 5, 5]),
    "3DS": ("UPS 3 Day Select", [18.95, 21.20, 24.60, 27.40, 29.75, 31.40, 33.60],
            [1.40, 1.85, 2.45, 3.05, 3.50, 3.85, 4.20], [3, 3, 3, 3, 3, 3, 3]),
    "2DA": ("UPS 2nd Day Air", [24.50, 27.30, 29.90, 32.80, 35.10, 37.60, 40.20],
            [2.10, 2.60, 3.20, 3.90, 4.60, 5.20, 5.90], [2, 2, 2, 2, 2, 2, 2]),
    "1DA": ("UPS Next Day Air", [49.80, 55.60, 61.40, 66.90, 70.20, 73.50, 76.80],
            [4.10, 4.90, 5.80, 6.70, 7.40, 8.10, 8.90], [1, 1, 1, 1, 1, 1, 1]),
}
NONCONTIGUOUS_AIR_MULTIPLIER = 1.6
RESIDENTIAL = {"GND": 6.15, "air": 6.60}
ADDITIONAL_HANDLING = 31.45
LARGE_PACKAGE = 245.00
# Stock cartons (inside dims, inches), smallest first.
CARTONS = [(10, 8, 4), (12, 10, 6), (16, 12, 8), (20, 16, 12), (24, 18, 18)]
PACK_EFFICIENCY = 0.8
MAX_WEIGHT, MAX_LENGTH, MAX_LENGTH_GIRTH = 150, 108, 165


class ShippingError(ValueError):
    pass


def locate(zip_code):
    z = str(zip_code or "").strip()[:5]
    if len(z) != 5 or not z.isdigit():
        raise ShippingError("Destination ZIP must be a 5-digit US ZIP code.")
    z3 = int(z[:3])
    for lo, hi, state, lat, lon in ZIP3:
        if lo <= z3 <= hi:
            return state, lat, lon
    raise ShippingError(f"UPS does not serve ZIP {z} from this origin (military/territory ZIPs unsupported).")


def miles(a, b):
    (lat1, lon1), (lat2, lon2) = [(math.radians(x), math.radians(y)) for x, y in (a, b)]
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def zone_for(zip_code):
    state, lat, lon = locate(zip_code)
    d = miles(ORIGIN_LATLON, (lat, lon))
    for zone, limit in zip(range(2, 8), (150, 300, 600, 1000, 1400, 1800)):
        if d <= limit:
            return zone, state, round(d)
    return 8, state, round(d)


def pack(units):
    """units: list of (weight_lb, (l, w, h)) per physical unit. Returns packages as (weight, dims).

    ponytail: volume-based first-fit into stock cartons, not true 3D bin packing.
    """
    packages, open_boxes = [], []  # open box: [weight, volume]
    for w, dims in sorted(units, key=lambda u: -math.prod(u[1])):
        vol = math.prod(dims)
        big = CARTONS[-1]
        if vol > math.prod(big) * PACK_EFFICIENCY or sorted(dims)[-1] > big[0]:
            packages.append((w, tuple(dims)))  # ships in its own box
            continue
        for box in open_boxes:
            if box[0] + w <= MAX_WEIGHT and box[1] + vol <= math.prod(big) * PACK_EFFICIENCY:
                box[0] += w
                box[1] += vol
                break
        else:
            open_boxes.append([w, vol])
    for w, vol in open_boxes:
        carton = next(c for c in CARTONS if math.prod(c) * PACK_EFFICIENCY >= vol)
        packages.append((w, carton))
    return packages


def rate_package(service, zone, weight, dims, noncontiguous):
    l, w, h = sorted((round(d) for d in dims), reverse=True)
    girth_len = l + 2 * (w + h)
    if weight > MAX_WEIGHT or l > MAX_LENGTH or girth_len > MAX_LENGTH_GIRTH:
        raise ShippingError(
            f"A package ({weight:.1f} lb, {l}x{w}x{h} in) exceeds UPS limits "
            f"({MAX_WEIGHT} lb, {MAX_LENGTH} in length, {MAX_LENGTH_GIRTH} in length+girth).")
    billable = math.ceil(max(weight, l * w * h / DIM_DIVISOR, 1))
    surcharges = 0.0
    large = girth_len > 130 or l > 96
    if large:
        billable = max(billable, 90)
        surcharges += LARGE_PACKAGE
    elif l > 48 or w > 30 or weight > 50:
        surcharges += ADDITIONAL_HANDLING
    _, base, per_lb, _ = RATES[service]
    transport = base[zone - 2] + per_lb[zone - 2] * (billable - 1)
    if noncontiguous:
        transport *= NONCONTIGUOUS_AIR_MULTIPLIER
    return transport, surcharges, billable


def quote(zip_code, units, fuel_pct, residential=True, free_ground_over=0.0, subtotal=0.0):
    """Return a list of rate options, cheapest first. Raises ShippingError on unrateable input."""
    if not units:
        raise ShippingError("Nothing to ship.")
    zone, state, distance = zone_for(zip_code)
    noncontiguous = state in NONCONTIGUOUS
    packages = pack(units)
    options = []
    for code, (name, _, _, days) in RATES.items():
        if noncontiguous and code in ("GND", "3DS"):
            continue  # UPS Ground / 3 Day Select do not serve AK/HI from the contiguous US
        transport = surcharges = 0.0
        billable_total = 0
        for weight, dims in packages:
            t, s, b = rate_package(code, zone, weight, dims, noncontiguous)
            transport, surcharges, billable_total = transport + t, surcharges + s, billable_total + b
        if residential:
            surcharges += RESIDENTIAL["GND" if code == "GND" else "air"] * len(packages)
        fuel = (transport + surcharges) * fuel_pct / 100
        total = round(transport + surcharges + fuel, 2)
        free = code == "GND" and free_ground_over > 0 and subtotal >= free_ground_over
        options.append({
            "service": code, "name": name, "zone": zone, "transit_days": days[zone - 2],
            "packages": len(packages), "billable_lb": billable_total,
            "transport": round(transport, 2), "surcharges": round(surcharges, 2), "fuel": round(fuel, 2),
            "list_total": total, "total": 0.0 if free else total, "free": free,
        })
    options.sort(key=lambda o: o["total"])
    return {"origin": ORIGIN, "destination_zip": str(zip_code)[:5], "destination_state": state,
            "distance_mi": distance, "zone": zone, "options": options}


if __name__ == "__main__":
    # Self-checks: zones, dim weight, limits, surcharges, packing, AK air-only.
    assert zone_for("78705")[0] == 2                     # Austin -> Austin
    assert zone_for("77002")[0] in (2, 3)               # Houston sits on the 150 mi boundary
    assert zone_for("10001")[0] == 7 and zone_for("90210")[0] == 6 and zone_for("99501")[0] == 8
    t, s, b = rate_package("GND", 2, 2, (20, 20, 20), False)
    assert b == 58 and s == 0                          # dim weight 8000/139 -> 58 lb, no surcharge
    assert rate_package("GND", 2, 55, (10, 10, 10), False)[1] == ADDITIONAL_HANDLING
    assert rate_package("GND", 2, 5, (97, 10, 10), False)[2] >= 90  # large package minimum
    for bad in ((151, (10, 10, 10)), (5, (109, 5, 5)), (5, (100, 20, 20))):
        try:
            rate_package("GND", 2, *bad, False)
            raise AssertionError(bad)
        except ShippingError:
            pass
    assert len(pack([(1, (6, 6, 3))] * 4)) == 1         # small items share one carton
    assert len(pack([(100, (10, 10, 10))] * 2)) == 2    # 150 lb carton cap splits them
    q = quote("99501", [(1, (6, 6, 3))], 15)
    assert {o["service"] for o in q["options"]} == {"2DA", "1DA"}
    q = quote("78705", [(1, (6, 6, 3))], 0, free_ground_over=75, subtotal=80)
    assert q["options"][0]["service"] == "GND" and q["options"][0]["total"] == 0
    for z in ("abc", "00901", "1234"):
        try:
            quote(z, [(1, (6, 6, 3))], 0)
            raise AssertionError(z)
        except ShippingError:
            pass
    print("shipping self-checks passed")
