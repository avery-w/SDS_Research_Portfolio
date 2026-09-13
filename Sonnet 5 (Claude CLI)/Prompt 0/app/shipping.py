"""UPS shipping rate lookup.

Uses the real UPS Rating API (OAuth client-credentials flow) when
UPS_CLIENT_ID/UPS_CLIENT_SECRET/UPS_ACCOUNT_NUMBER are configured. Falls back
to a flat-rate estimator otherwise, so checkout works without a UPS account.
"""

import time

import requests
from flask import current_app

# UPS service codes -> display names (subset commonly used for small parcel)
UPS_SERVICES = {
    "03": "UPS Ground",
    "12": "UPS 3 Day Select",
    "02": "UPS 2nd Day Air",
    "01": "UPS Next Day Air",
}

_token_cache = {"access_token": None, "expires_at": 0}


def _ups_base_url():
    env = current_app.config["UPS_ENV"]
    return "https://onlinetools.ups.com" if env == "production" else "https://wwwcie.ups.com"


def _get_access_token():
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 30:
        return _token_cache["access_token"]

    client_id = current_app.config["UPS_CLIENT_ID"]
    client_secret = current_app.config["UPS_CLIENT_SECRET"]
    resp = requests.post(
        f"{_ups_base_url()}/security/v1/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + int(data.get("expires_in", 3600))
    return _token_cache["access_token"]


def _ups_configured():
    cfg = current_app.config
    return bool(cfg.get("UPS_CLIENT_ID") and cfg.get("UPS_CLIENT_SECRET") and cfg.get("UPS_ACCOUNT_NUMBER"))


def get_shipping_rates(destination, weight_lbs):
    """Return a list of {code, name, cost, business_days} shipping options.

    destination: dict with address, city, state, zip, country
    weight_lbs: total shippable weight in pounds
    """
    if _ups_configured():
        try:
            return _get_ups_rates(destination, weight_lbs)
        except Exception:
            current_app.logger.exception("UPS Rating API call failed, using fallback estimator")

    return _estimate_rates(destination, weight_lbs)


def _get_ups_rates(destination, weight_lbs):
    ship_from = current_app.config["SHIP_FROM_ADDRESS"]
    token = _get_access_token()

    payload = {
        "RateRequest": {
            "Request": {"TransactionReference": {"CustomerContext": "Rate Shop"}},
            "Shipment": {
                "Shipper": {
                    "Name": ship_from["name"],
                    "ShipperNumber": current_app.config["UPS_ACCOUNT_NUMBER"],
                    "Address": {
                        "AddressLine": [ship_from["address"]],
                        "City": ship_from["city"],
                        "StateProvinceCode": ship_from["state"],
                        "PostalCode": ship_from["zip"],
                        "CountryCode": ship_from["country"],
                    },
                },
                "ShipTo": {
                    "Address": {
                        "AddressLine": [destination["address"]],
                        "City": destination["city"],
                        "StateProvinceCode": destination["state"],
                        "PostalCode": destination["zip"],
                        "CountryCode": destination.get("country", "US"),
                    }
                },
                "ShipFrom": {
                    "Address": {
                        "AddressLine": [ship_from["address"]],
                        "City": ship_from["city"],
                        "StateProvinceCode": ship_from["state"],
                        "PostalCode": ship_from["zip"],
                        "CountryCode": ship_from["country"],
                    }
                },
                "Package": {
                    "PackagingType": {"Code": "02", "Description": "Package"},
                    "PackageWeight": {
                        "UnitOfMeasurement": {"Code": "LBS"},
                        "Weight": str(max(weight_lbs, 0.1)),
                    },
                },
            },
        }
    }

    resp = requests.post(
        f"{_ups_base_url()}/api/rating/v2205/Shop",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "transId": "rateshop",
            "transactionSrc": "marketplace",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    rated = data["RateResponse"]["RatedShipment"]
    if isinstance(rated, dict):
        rated = [rated]

    options = []
    for shipment in rated:
        code = shipment["Service"]["Code"]
        cost = float(shipment["TotalCharges"]["MonetaryValue"])
        options.append(
            {
                "code": code,
                "name": UPS_SERVICES.get(code, shipment["Service"].get("Description", code)),
                "cost": round(cost, 2),
            }
        )
    return sorted(options, key=lambda o: o["cost"])


# ponytail: no UPS account configured -> flat weight-tiered estimate instead
# of true UPS zone charts. Upgrade path: set UPS_CLIENT_ID/SECRET/ACCOUNT to
# use _get_ups_rates for real published rates.
_ESTIMATE_BASE = {
    "03": (7.50, 0.60),   # Ground: base + per-lb
    "12": (14.00, 0.90),  # 3 Day Select
    "02": (22.00, 1.40),  # 2nd Day Air
    "01": (38.00, 2.20),  # Next Day Air
}


def _estimate_rates(destination, weight_lbs):
    weight = max(weight_lbs, 0.1)
    options = []
    for code, (base, per_lb) in _ESTIMATE_BASE.items():
        cost = base + per_lb * weight
        options.append({"code": code, "name": UPS_SERVICES[code], "cost": round(cost, 2)})
    return sorted(options, key=lambda o: o["cost"])
