"""UPS shipping rates from the fixed origin.

Uses the live UPS Rating API when credentials are configured, otherwise an
estimator that applies UPS's published rules (dimensional weight, whole-pound
billing, package limits, zones, residential and additional-handling surcharges).
"""

import base64
import json
import logging
import math
import urllib.request
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

ORIGIN = {
    "AddressLine": ["110 Inner Campus Drive"],
    "City": "Austin",
    "StateProvinceCode": "TX",
    "PostalCode": "78705",
    "CountryCode": "US",
}
SERVICES = {"03": "UPS Ground", "12": "UPS 3 Day Select", "02": "UPS 2nd Day Air", "01": "UPS Next Day Air"}

DIM_DIVISOR = 139  # UPS daily rates, inches/pounds
MAX_WEIGHT_LB = 150
MAX_LENGTH_IN = 108
MAX_LENGTH_PLUS_GIRTH_IN = 165

CENT = Decimal("0.01")


class ShippingError(Exception):
    pass


@dataclass
class Package:
    weight: float
    dims: list  # [length, width, height], length is the longest side

    @property
    def length_plus_girth(self):
        l, w, h = sorted(self.dims, reverse=True)
        return l + 2 * (w + h)

    @property
    def billable_lb(self):
        l, w, h = self.dims
        return max(1, math.ceil(max(self.weight, l * w * h / DIM_DIVISOR)))

    @property
    def additional_handling(self):
        l, w, _ = sorted(self.dims, reverse=True)
        return l > 48 or w > 30 or self.weight > 50


def _fits(p):
    return p.weight <= MAX_WEIGHT_LB and max(p.dims) <= MAX_LENGTH_IN and p.length_plus_girth <= MAX_LENGTH_PLUS_GIRTH_IN


def pack(items):
    """Greedy: stack units along their shortest side until a UPS limit would be exceeded.

    ponytail: greedy stacking, not bin packing. Swap in a 3D packer if boxes come out oversized.
    """
    packages, cur = [], None
    for product, qty in items:
        unit_dims = sorted([float(product.length_in), float(product.width_in), float(product.height_in)], reverse=True)
        unit = Package(float(product.weight_lb), unit_dims)
        if not _fits(unit):
            raise ShippingError(f"{product.name} exceeds UPS package limits.")
        for _ in range(qty):
            if cur is not None:
                l, w, h = cur.dims
                merged = Package(cur.weight + unit.weight, [max(l, unit_dims[0]), max(w, unit_dims[1]), h + unit_dims[2]])
                if _fits(merged):
                    cur = merged
                    continue
                packages.append(cur)
            cur = Package(unit.weight, list(unit_dims))
    if cur:
        packages.append(cur)
    return packages


def zone_for(zip_code):
    """Approximate UPS zone from Austin (ZIP3 787) by destination ZIP prefix.

    ponytail: coarse regional table. Load the official UPS zone chart for origin 787 if estimates drift.
    """
    z3 = int(zip_code[:3])
    if 786 <= z3 <= 789:
        return 2
    if 750 <= z3 <= 799 or z3 == 733 or z3 == 885:
        return 3 if z3 < 790 else 5
    if 967 <= z3 <= 968 or z3 >= 995:
        return 8  # Hawaii, Alaska
    return {7: 4, 6: 5, 3: 5, 8: 6, 4: 6, 5: 6, 2: 6, 1: 7, 0: 7, 9: 7}[z3 // 100]


# Base rate for a 1 lb package in zone 2, then per additional lb, scaled by zone.
BASE = {"03": Decimal("10.50"), "12": Decimal("18.00"), "02": Decimal("24.00"), "01": Decimal("38.00")}
PER_LB = {"03": Decimal("0.95"), "12": Decimal("1.60"), "02": Decimal("2.40"), "01": Decimal("4.10")}
RESIDENTIAL = {"03": Decimal("5.95"), "12": Decimal("6.40"), "02": Decimal("6.40"), "01": Decimal("6.40")}
ADDITIONAL_HANDLING = Decimal("30.00")


def estimate(packages, dest_zip, residential=True):
    zone = zone_for(dest_zip)
    fuel = 1 + Decimal(settings.UPS_FUEL_SURCHARGE_PCT) / 100
    rates = {}
    for code in SERVICES:
        total = Decimal(0)
        for p in packages:
            charge = BASE[code] * (1 + Decimal("0.12") * (zone - 2))
            charge += PER_LB[code] * (p.billable_lb - 1) * (1 + Decimal("0.15") * (zone - 2))
            if p.additional_handling:
                charge += ADDITIONAL_HANDLING
            if residential:
                charge += RESIDENTIAL[code]
            total += charge * fuel
        rates[code] = total.quantize(CENT, ROUND_HALF_UP)
    return rates


def _post(url, headers, data):
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _ups_token():
    token = cache.get("ups_token")
    if token:
        return token
    auth = base64.b64encode(f"{settings.UPS_CLIENT_ID}:{settings.UPS_CLIENT_SECRET}".encode()).decode()
    data = _post(
        f"{settings.UPS_BASE_URL}/security/v1/oauth/token",
        {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded",
         "x-merchant-id": settings.UPS_ACCOUNT_NUMBER},
        b"grant_type=client_credentials",
    )
    token = data["access_token"]
    cache.set("ups_token", token, int(data.get("expires_in", 3600)) - 60)
    return token


def ups_rates(packages, dest):
    address = {"AddressLine": [dest["line1"]], "City": dest["city"], "StateProvinceCode": dest["state"],
               "PostalCode": dest["zip"], "CountryCode": "US", "ResidentialAddressIndicator": ""}
    body = {"RateRequest": {"Request": {"RequestOption": "Shop"}, "Shipment": {
        "Shipper": {"Name": "Marketplace", "ShipperNumber": settings.UPS_ACCOUNT_NUMBER, "Address": ORIGIN},
        "ShipFrom": {"Name": "Marketplace", "Address": ORIGIN},
        "ShipTo": {"Name": dest.get("name", "Customer"), "Address": address},
        "Package": [{
            "PackagingType": {"Code": "02"},
            "Dimensions": {"UnitOfMeasurement": {"Code": "IN"},
                           **{k: f"{math.ceil(v)}" for k, v in zip(("Length", "Width", "Height"), p.dims)}},
            "PackageWeight": {"UnitOfMeasurement": {"Code": "LBS"}, "Weight": f"{math.ceil(p.weight)}"},
        } for p in packages],
    }}}
    data = _post(
        f"{settings.UPS_BASE_URL}/api/rating/v2409/Shop",
        {"Authorization": f"Bearer {_ups_token()}", "Content-Type": "application/json",
         "transId": "rate", "transactionSrc": "marketplace"},
        json.dumps(body).encode(),
    )
    shipments = data["RateResponse"]["RatedShipment"]
    if isinstance(shipments, dict):
        shipments = [shipments]
    return {s["Service"]["Code"]: Decimal(s["TotalCharges"]["MonetaryValue"]).quantize(CENT)
            for s in shipments if s["Service"]["Code"] in SERVICES}


def quote(items, dest):
    """items: [(product, qty)], dest: dict(line1, city, state, zip). Returns (rates, source)."""
    packages = pack(items)
    if settings.UPS_CLIENT_ID:
        try:
            return ups_rates(packages, dest), "ups"
        except Exception:
            log.exception("UPS Rating API failed, falling back to estimate")
    return estimate(packages, dest["zip"]), "estimate"
