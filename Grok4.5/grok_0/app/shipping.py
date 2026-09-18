"""
Approximate UPS Ground rates based on public dimensional-weight and zone guidelines.
Origin is fixed at: 110 Inner Campus Drive, Austin, TX 78705 (ZIP 78705).

In production replace this with the official UPS Rating API.
"""
from math import ceil

# Simplified zone lookup by destination ZIP prefix (illustrative)
ZONE_TABLE = {
    "78": 2, "77": 2, "76": 3, "75": 3, "74": 3, "73": 4,
    "70": 4, "71": 4, "72": 4, "80": 4, "79": 3,
    "90": 5, "91": 5, "92": 5, "93": 5, "94": 5, "95": 5,
    "10": 6, "11": 6, "12": 6, "13": 6, "14": 6,
    "20": 5, "21": 5, "22": 5, "30": 5, "33": 5,
    "00": 8, "01": 7, "02": 7,
}

BASE_RATES = {  # zone -> base cost for first pound
    2: 8.50, 3: 10.20, 4: 12.80, 5: 15.40, 6: 18.90, 7: 22.50, 8: 28.00
}
PER_LB = {
    2: 0.85, 3: 1.10, 4: 1.45, 5: 1.80, 6: 2.20, 7: 2.70, 8: 3.40
}


def dimensional_weight(length_in: float, width_in: float, height_in: float) -> float:
    """UPS Ground dimensional divisor is typically 139."""
    return (length_in * width_in * height_in) / 139.0


def get_zone(dest_zip: str) -> int:
    if not dest_zip or len(dest_zip) < 2:
        return 8
    prefix = dest_zip.strip()[:2]
    return ZONE_TABLE.get(prefix, 8)


def calculate_shipping(
    weight_lb: float,
    length_in: float = 10.0,
    width_in: float = 8.0,
    height_in: float = 4.0,
    dest_zip: str = "10001",
    service: str = "ground",
) -> dict:
    dim_wt = dimensional_weight(length_in, width_in, height_in)
    billable = max(float(weight_lb), dim_wt)
    billable = max(1.0, ceil(billable))  # UPS bills to the next whole pound

    zone = get_zone(dest_zip)
    base = BASE_RATES.get(zone, 30.0)
    per_lb = PER_LB.get(zone, 4.0)
    cost = base + (billable - 1) * per_lb

    # Approximate fuel surcharge
    cost *= 1.12

    return {
        "origin": "110 Inner Campus Drive, Austin, TX 78705",
        "origin_zip": "78705",
        "destination_zip": dest_zip,
        "zone": zone,
        "billable_weight_lb": billable,
        "dimensional_weight_lb": round(dim_wt, 2),
        "service": service,
        "shipping_cost": round(cost, 2),
        "currency": "USD",
        "note": (
            "Approximate rate based on UPS Ground dimensional-weight and zone guidelines. "
            "For production use the official UPS Rating API with your account credentials."
        ),
    }
