"""UPS shipping rates from the fixed origin, 110 Inner Campus Drive, Austin, TX 78705.

Uses the live UPS Rating API when UPS_CLIENT_ID / UPS_CLIENT_SECRET / UPS_ACCOUNT_NUMBER are set.
Otherwise it estimates with UPS's published rules: billable weight = max(actual, L*W*H/139) rounded
up to the next pound, 150 lb / 108 in / 165 in length+girth limits, large package minimum of 90 lb,
additional handling, residential and fuel surcharges, and zones by distance from the origin.
"""

import math
import re
import time
import uuid
from dataclasses import dataclass

import requests
from flask import current_app

ORIGIN = {
    "AddressLine": ["110 Inner Campus Drive"],
    "City": "Austin",
    "StateProvinceCode": "TX",
    "PostalCode": "78705",
    "CountryCode": "US",
}
ORIGIN_LATLON = (30.2862, -97.7394)

SERVICES = {"03": "UPS Ground", "12": "UPS 3 Day Select", "02": "UPS 2nd Day Air", "01": "UPS Next Day Air"}

# UPS guideline constants
DIM_DIVISOR = 139
MAX_WEIGHT_LB = 150
MAX_LENGTH_IN = 108
MAX_LENGTH_PLUS_GIRTH_IN = 165
LARGE_PACKAGE_MIN_BILLABLE_LB = 90

# ponytail: approximates UPS daily list rates (cents) by zone 2..8; real contract rates come from the live API.
BASE_1LB = {
    "03": [1035, 1080, 1140, 1180, 1245, 1300, 1370],
    "12": [1720, 1960, 2330, 2590, 2800, 2950, 3120],
    "02": [2280, 2560, 2860, 3110, 3380, 3610, 3830],
    "01": [4570, 5070, 5930, 6480, 6980, 7320, 7700],
}
PER_EXTRA_LB = {
    "03": [45, 60, 95, 130, 170, 210, 250],
    "12": [140, 180, 250, 320, 400, 460, 520],
    "02": [230, 300, 380, 470, 560, 640, 720],
    "01": [480, 580, 700, 820, 920, 1000, 1090],
}
FUEL_SURCHARGE_PCT = 20
RESIDENTIAL_CENTS = {"03": 595, "12": 645, "02": 645, "01": 645}
ADDITIONAL_HANDLING_CENTS = 3200
LARGE_PACKAGE_CENTS = 25000
AIR_DAYS = {"12": 3, "02": 2, "01": 1}
GROUND_DAYS = {2: 1, 3: 2, 4: 3, 5: 3, 6: 4, 7: 4, 8: 5}

# ponytail: zone by state centroid distance, not UPS's ZIP3 zone chart; use the live API for exact zones.
STATE_LATLON = {
    "AL": (32.8, -86.8), "AZ": (34.2, -111.7), "AR": (34.9, -92.4), "CA": (37.2, -119.5), "CO": (39.0, -105.5),
    "CT": (41.6, -72.7), "DE": (39.0, -75.5), "DC": (38.9, -77.0), "FL": (28.6, -82.4), "GA": (32.7, -83.4),
    "ID": (44.4, -114.6), "IL": (40.0, -89.2), "IN": (39.9, -86.3), "IA": (42.1, -93.5), "KS": (38.5, -98.4),
    "KY": (37.5, -85.3), "LA": (31.1, -92.0), "ME": (45.4, -69.2), "MD": (39.0, -76.8), "MA": (42.3, -71.8),
    "MI": (44.3, -85.4), "MN": (46.3, -94.3), "MS": (32.7, -89.7), "MO": (38.4, -92.5), "MT": (47.0, -109.6),
    "NE": (41.5, -99.8), "NV": (39.3, -116.6), "NH": (43.7, -71.6), "NJ": (40.2, -74.7), "NM": (34.4, -106.1),
    "NY": (42.9, -75.5), "NC": (35.6, -79.4), "ND": (47.5, -100.5), "OH": (40.3, -82.8), "OK": (35.6, -97.5),
    "OR": (43.9, -120.6), "PA": (40.9, -77.8), "RI": (41.7, -71.5), "SC": (33.9, -80.9), "SD": (44.4, -100.2),
    "TN": (35.9, -86.4), "TX": (31.5, -99.3), "UT": (39.3, -111.7), "VT": (44.1, -72.7), "VA": (37.5, -78.9),
    "WA": (47.4, -120.5), "WV": (38.6, -80.6), "WI": (44.6, -89.9), "WY": (43.0, -107.6),
}
US_STATES = set(STATE_LATLON) | {"AK", "HI"}
ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")


class ShippingError(ValueError):
    pass


@dataclass
class Package:
    weight_lb: float
    length: float
    width: float
    height: float

    def __post_init__(self):
        self.length, self.width, self.height = sorted((self.length, self.width, self.height), reverse=True)

    @property
    def length_plus_girth(self):
        return self.length + 2 * (self.width + self.height)

    @property
    def is_large(self):
        return self.length > 96 or self.length_plus_girth > 130

    @property
    def needs_additional_handling(self):
        return self.weight_lb > 50 or self.length > 48 or self.width > 30

    def check_limits(self):
        if self.weight_lb > MAX_WEIGHT_LB:
            raise ShippingError(f"Package exceeds the UPS maximum of {MAX_WEIGHT_LB} lb")
        if self.length > MAX_LENGTH_IN:
            raise ShippingError(f"Package exceeds the UPS maximum length of {MAX_LENGTH_IN} in")
        if self.length_plus_girth > MAX_LENGTH_PLUS_GIRTH_IN:
            raise ShippingError(f"Package exceeds the UPS maximum length plus girth of {MAX_LENGTH_PLUS_GIRTH_IN} in")

    def billable_weight(self):
        dim_weight = math.ceil(self.length * self.width * self.height / DIM_DIVISOR)
        billable = max(math.ceil(self.weight_lb), dim_weight, 1)
        return max(billable, LARGE_PACKAGE_MIN_BILLABLE_LB) if self.is_large else billable


def pack(lines):
    """lines: [(product, qty)] for one store. One combined box if it fits UPS limits, else one box per unit."""
    units = [Package(p.weight_lb, p.length_in, p.width_in, p.height_in) for p, qty in lines for _ in range(qty)]
    for unit in units:
        unit.check_limits()
    combined = Package(
        sum(u.weight_lb for u in units),
        max(u.length for u in units),
        max(u.width for u in units),
        sum(u.height for u in units),
    )
    try:
        combined.check_limits()
        return [combined]
    except ShippingError:
        return units


def validate_destination(dest):
    state = (dest.get("state") or "").strip().upper()
    zip_code = (dest.get("zip") or "").strip()
    if state not in US_STATES:
        raise ShippingError("Enter a valid 2-letter US state code")
    if not ZIP_RE.match(zip_code):
        raise ShippingError("Enter a valid ZIP code")
    return {**dest, "state": state, "zip": zip_code}


def zone_for(state):
    if state not in STATE_LATLON:
        raise ShippingError("Rate estimates cover the contiguous US; configure UPS API credentials for AK and HI")
    lat1, lon1 = map(math.radians, ORIGIN_LATLON)
    lat2, lon2 = map(math.radians, STATE_LATLON[state])
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    miles = 3958.8 * 2 * math.asin(math.sqrt(a))
    for zone, limit in ((2, 150), (3, 300), (4, 600), (5, 1000), (6, 1400), (7, 1800)):
        if miles <= limit:
            return zone
    return 8


def estimate_rates(packages, state, residential=True):
    """{service_code: (cents, business_days)} using UPS rules and approximate list rates."""
    zone = zone_for(state)
    rates = {}
    for code in SERVICES:
        total = 0
        for pkg in packages:
            weight = pkg.billable_weight()
            cents = BASE_1LB[code][zone - 2] + PER_EXTRA_LB[code][zone - 2] * (weight - 1)
            if pkg.needs_additional_handling:
                cents += ADDITIONAL_HANDLING_CENTS
            if pkg.is_large:
                cents += LARGE_PACKAGE_CENTS
            if residential:
                cents += RESIDENTIAL_CENTS[code]
            total += cents
        total += total * FUEL_SURCHARGE_PCT // 100
        rates[code] = (total, GROUND_DAYS[zone] if code == "03" else AIR_DAYS[code])
    return rates


_token = {"value": None, "expires": 0.0}


def _ups_token(cfg):
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    resp = requests.post(
        f"{cfg['UPS_BASE_URL']}/security/v1/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(cfg["UPS_CLIENT_ID"], cfg["UPS_CLIENT_SECRET"]),
        headers={"x-merchant-id": cfg["UPS_ACCOUNT_NUMBER"]},
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    _token.update(value=body["access_token"], expires=time.time() + int(body.get("expires_in", 3600)))
    return _token["value"]


def ups_rates(packages, dest):
    """Live rates from the UPS Rating API ("Shop" returns every available service)."""
    cfg = current_app.config
    address = {
        "AddressLine": [dest.get("street") or ""],
        "City": dest.get("city") or "",
        "StateProvinceCode": dest["state"],
        "PostalCode": dest["zip"],
        "CountryCode": "US",
        "ResidentialAddressIndicator": "",
    }
    payload = {
        "RateRequest": {
            "Request": {"RequestOption": "Shop"},
            "Shipment": {
                "Shipper": {"Name": "Marketplace", "ShipperNumber": cfg["UPS_ACCOUNT_NUMBER"], "Address": ORIGIN},
                "ShipFrom": {"Name": "Marketplace", "Address": ORIGIN},
                "ShipTo": {"Name": dest.get("name") or "Customer", "Address": address},
                "Package": [
                    {
                        "PackagingType": {"Code": "02"},
                        "Dimensions": {
                            "UnitOfMeasurement": {"Code": "IN"},
                            "Length": f"{p.length:.1f}",
                            "Width": f"{p.width:.1f}",
                            "Height": f"{p.height:.1f}",
                        },
                        "PackageWeight": {"UnitOfMeasurement": {"Code": "LBS"}, "Weight": f"{p.weight_lb:.1f}"},
                    }
                    for p in packages
                ],
            },
        }
    }
    resp = requests.post(
        f"{cfg['UPS_BASE_URL']}/api/rating/{cfg['UPS_API_VERSION']}/Shop",
        json=payload,
        headers={"Authorization": f"Bearer {_ups_token(cfg)}", "transId": uuid.uuid4().hex, "transactionSrc": "marketplace"},
        timeout=15,
    )
    resp.raise_for_status()
    rated = resp.json()["RateResponse"]["RatedShipment"]
    rates = {}
    for shipment in rated if isinstance(rated, list) else [rated]:
        code = shipment["Service"]["Code"]
        if code in SERVICES:
            charges = shipment.get("NegotiatedRateCharges", {}).get("TotalCharge") or shipment["TotalCharges"]
            days = shipment.get("GuaranteedDelivery", {}).get("BusinessDaysInTransit")
            rates[code] = (round(float(charges["MonetaryValue"]) * 100), int(days) if days else None)
    return rates


def quote(shipments, dest):
    """shipments: one package list per store. Returns services available for every shipment, costs summed."""
    dest = validate_destination(dest)
    cfg = current_app.config
    source = "estimate"
    per_shipment = None
    if cfg.get("UPS_CLIENT_ID") and cfg.get("UPS_CLIENT_SECRET") and cfg.get("UPS_ACCOUNT_NUMBER"):
        try:
            per_shipment = [ups_rates(pkgs, dest) for pkgs in shipments]
            source = "ups"
        except (requests.RequestException, KeyError, ValueError) as exc:
            current_app.logger.warning("UPS Rating API failed, using estimate: %s", exc)
    if per_shipment is None:
        per_shipment = [estimate_rates(pkgs, dest["state"]) for pkgs in shipments]

    common = set(SERVICES).intersection(*[r.keys() for r in per_shipment])
    services = []
    for code in sorted(common, key=lambda c: sum(r[c][0] for r in per_shipment)):
        days = [r[code][1] for r in per_shipment if r[code][1]]
        services.append(
            {
                "code": code,
                "name": SERVICES[code],
                "amount_cents": sum(r[code][0] for r in per_shipment),
                "business_days": max(days) if days else None,
                "per_shipment_cents": [r[code][0] for r in per_shipment],
            }
        )
    return {"source": source, "origin": "110 Inner Campus Drive, Austin, TX 78705", "services": services}
