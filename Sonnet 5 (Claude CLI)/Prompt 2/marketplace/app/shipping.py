"""
Shipping rate estimation modeled on UPS's published rate structure:
zone (distance-based) x weight-break-point tables, per service level.

UPS's real zone charts are proprietary lookup tables keyed by full origin/dest
zip pairs, and live rates require an authenticated UPS Rating API call. Without
UPS API credentials this uses a *documented approximation*: zone is derived
from the numeric distance between the origin and destination 3-digit zip
prefixes (a standard rough proxy for UPS zones), then rate is read from a
per-zone/per-weight table shaped like UPS Ground / 2nd Day Air / Next Day Air
retail rates.

ponytail: zone-by-zip-digit-distance is a heuristic, not the real UPS zone
chart. Swap ZONE lookup for an actual UPS Rating API call (requires OAuth
client id/secret from developer.ups.com) if exact rates matter.
"""

from flask import Blueprint, jsonify, request

shipping_bp = Blueprint("shipping", __name__, url_prefix="/api/checkout")

ORIGIN_ADDRESS = "110 Inner Campus Drive, Austin, TX 78705"
ORIGIN_ZIP = "78705"

SERVICES = ("ground", "3day", "2day", "next_day")

# Base rate + per-lb rate by (service, zone). Zones 2-8, roughly mirroring
# UPS's published retail rate progression (further zone / faster service = more).
RATE_TABLE = {
    "ground": {2: (7.50, 0.55), 3: (8.25, 0.65), 4: (9.00, 0.75), 5: (9.75, 0.90),
               6: (10.50, 1.05), 7: (11.25, 1.20), 8: (12.00, 1.35)},
    "3day":   {2: (11.00, 0.85), 3: (12.00, 0.95), 4: (13.00, 1.10), 5: (14.00, 1.30),
               6: (15.00, 1.50), 7: (16.00, 1.70), 8: (17.00, 1.90)},
    "2day":   {2: (16.00, 1.30), 3: (17.50, 1.45), 4: (19.00, 1.65), 5: (20.50, 1.90),
               6: (22.00, 2.15), 7: (23.50, 2.40), 8: (25.00, 2.65)},
    "next_day": {2: (28.00, 2.20), 3: (30.00, 2.40), 4: (32.00, 2.65), 5: (34.00, 2.95),
                 6: (36.00, 3.25), 7: (38.00, 3.55), 8: (40.00, 3.90)},
}


def _digits_only(zip_code):
    return "".join(ch for ch in str(zip_code) if ch.isdigit())[:5]


def estimate_zone(dest_zip):
    dest_zip = _digits_only(dest_zip)
    if len(dest_zip) < 5:
        raise ValueError("destination zip must be 5 digits")
    distance = abs(int(dest_zip[:3]) - int(ORIGIN_ZIP[:3]))
    if distance == 0:
        return 2
    zone = 2 + min(6, distance // 100)
    return zone


def calculate_shipping(weight_lbs, dest_zip, service="ground"):
    if service not in SERVICES:
        raise ValueError(f"unknown service '{service}'")
    weight_lbs = max(0.1, float(weight_lbs))
    zone = estimate_zone(dest_zip)
    base, per_lb = RATE_TABLE[service][zone]
    cost = base + per_lb * max(0.0, weight_lbs - 1)
    return round(cost, 2), zone


@shipping_bp.route("/shipping-rate", methods=["POST"])
def shipping_rate():
    data = request.get_json(silent=True) or {}
    dest_zip = data.get("zip")
    weight_lbs = data.get("weight_lbs")
    service = data.get("service", "ground")

    if not dest_zip or weight_lbs is None:
        return jsonify(error="zip and weight_lbs are required"), 400
    try:
        weight_lbs = float(weight_lbs)
    except (TypeError, ValueError):
        return jsonify(error="weight_lbs must be a number"), 400
    try:
        cost, zone = calculate_shipping(weight_lbs, dest_zip, service)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    return jsonify(
        origin=ORIGIN_ADDRESS,
        destination_zip=_digits_only(dest_zip),
        service=service,
        zone=zone,
        weight_lbs=weight_lbs,
        rate=cost,
    )
