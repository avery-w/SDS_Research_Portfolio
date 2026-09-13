"""UPS Rating API integration.

Ship-from is fixed per business requirements:
  110 Inner Campus Drive, Austin, TX 78705

Docs: https://developer.ups.com/api/reference?loc=en_US#operation/Rate
Auth: https://developer.ups.com/api/reference?loc=en_US#tag/Authorization
"""

import time

import httpx
from fastapi import HTTPException

from app.config import get_settings

settings = get_settings()

SHIP_FROM = {
    "AddressLine": ["110 Inner Campus Drive"],
    "City": "Austin",
    "StateProvinceCode": "TX",
    "PostalCode": "78705",
    "CountryCode": "US",
}

_BASE_URLS = {
    "sandbox": "https://wwwcie.ups.com",
    "production": "https://onlinetools.ups.com",
}

# UPS Ground / 2nd Day Air / Next Day Air (Standard service codes)
SERVICE_CODES = {
    "03": "UPS Ground",
    "02": "UPS 2nd Day Air",
    "01": "UPS Next Day Air",
}

_token_cache: dict[str, tuple[str, float]] = {}


def _base_url() -> str:
    return _BASE_URLS.get(settings.ups_env, _BASE_URLS["sandbox"])


def _get_access_token() -> str:
    cached = _token_cache.get("token")
    if cached and cached[1] > time.time():
        return cached[0]

    if not settings.ups_client_id or not settings.ups_client_secret:
        raise HTTPException(status_code=503, detail="Shipping is temporarily unavailable")

    resp = httpx.post(
        f"{_base_url()}/security/v1/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(settings.ups_client_id, settings.ups_client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    token = body["access_token"]
    expires_in = int(body.get("expires_in", 3600))
    _token_cache["token"] = (token, time.time() + expires_in - 60)
    return token


def get_shipping_rates(
    *,
    to_name: str,
    to_address1: str,
    to_city: str,
    to_state: str,
    to_zip: str,
    weight_lb: float,
    length_in: float,
    width_in: float,
    height_in: float,
) -> list[dict]:
    """Returns [{code, name, cost_cents}] for each available UPS service, cheapest first."""
    try:
        token = _get_access_token()
    except HTTPException:
        # No UPS credentials configured (e.g. local dev) -> flat-rate fallback so
        # checkout still works. Real quotes require UPS_CLIENT_ID/SECRET.
        return _fallback_rates(weight_lb)

    payload = {
        "RateRequest": {
            "Request": {"TransactionReference": {"CustomerContext": "marketplace-checkout"}},
            "Shipment": {
                "Shipper": {
                    "Name": "Marketplace Fulfillment",
                    "ShipperNumber": settings.ups_account_number,
                    "Address": SHIP_FROM,
                },
                "ShipFrom": {"Name": "Marketplace Fulfillment", "Address": SHIP_FROM},
                "ShipTo": {
                    "Name": to_name,
                    "Address": {
                        "AddressLine": [to_address1],
                        "City": to_city,
                        "StateProvinceCode": to_state,
                        "PostalCode": to_zip,
                        "CountryCode": "US",
                    },
                },
                "Package": [
                    {
                        "PackagingType": {"Code": "02", "Description": "Package"},
                        "Dimensions": {
                            "UnitOfMeasurement": {"Code": "IN"},
                            "Length": str(length_in),
                            "Width": str(width_in),
                            "Height": str(height_in),
                        },
                        "PackageWeight": {
                            "UnitOfMeasurement": {"Code": "LBS"},
                            "Weight": str(max(weight_lb, 0.1)),
                        },
                    }
                ],
            },
        }
    }

    try:
        resp = httpx.post(
            f"{_base_url()}/api/rating/v2409/Shop",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, KeyError, ValueError):
        return _fallback_rates(weight_lb)

    rated = data.get("RateResponse", {}).get("RatedShipment", [])
    if isinstance(rated, dict):
        rated = [rated]

    rates = []
    for shipment in rated:
        code = shipment["Service"]["Code"]
        charge = float(shipment["TotalCharges"]["MonetaryValue"])
        rates.append(
            {
                "code": code,
                "name": SERVICE_CODES.get(code, shipment["Service"].get("Description", code)),
                "cost_cents": round(charge * 100),
            }
        )
    return sorted(rates, key=lambda r: r["cost_cents"]) or _fallback_rates(weight_lb)


def _fallback_rates(weight_lb: float) -> list[dict]:
    # ponytail: flat-rate estimate, only used when UPS creds are absent/unreachable.
    # Upgrade path: none needed once UPS_CLIENT_ID/SECRET are set in production.
    base = 6.5 + max(weight_lb, 0.5) * 1.25
    return [
        {"code": "03", "name": "UPS Ground (est.)", "cost_cents": round(base * 100)},
        {"code": "02", "name": "UPS 2nd Day Air (est.)", "cost_cents": round((base + 12) * 100)},
        {"code": "01", "name": "UPS Next Day Air (est.)", "cost_cents": round((base + 28) * 100)},
    ]
