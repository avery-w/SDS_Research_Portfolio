import os
import json
import requests
from django.core.cache import cache

UPS_BASE = os.getenv("UPS_API_BASE", "https://onlinetools.ups.com")
ORIGIN = {
    "AddressLine": ["110 Inner Campus Drive"],
    "City": "Austin",
    "StateProvinceCode": "TX",
    "PostalCode": "78705",
    "CountryCode": "US",
}

def get_token():
    tok = cache.get("ups_token")
    if tok:
        return tok
    r = requests.post(
        f"{UPS_BASE}/security/v1/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(os.getenv("UPS_CLIENT_ID"), os.getenv("UPS_CLIENT_SECRET")),
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    cache.set("ups_token", data["access_token"], timeout=data.get("expires_in", 3300))
    return data["access_token"]

def shop_rates(dest, packages):
    body = {
        "RateRequest": {
            "Request": {"RequestOption": "Shop"},
            "Shipment": {
                "Shipper": {"Address": ORIGIN},
                "ShipFrom": {"Address": ORIGIN},
                "ShipTo": {
                    "Address": {
                        "AddressLine": [dest["address1"]],
                        "City": dest["city"],
                        "StateProvinceCode": dest["state"],
                        "PostalCode": dest["postal"],
                        "CountryCode": dest.get("country", "US"),
                    }
                },
                "Package": [
                    {
                        "PackagingType": {"Code": "02"},
                        "Dimensions": {
                            "UnitOfMeasurement": {"Code": "IN"},
                            "Length": str(p["length_in"]),
                            "Width": str(p["width_in"]),
                            "Height": str(p["height_in"]),
                        },
                        "PackageWeight": {
                            "UnitOfMeasurement": {"Code": "LBS"},
                            "Weight": str(p["weight_lb"]),
                        },
                    }
                    for p in packages
                ],
            },
        }
    }
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    r = requests.post(f"{UPS_BASE}/api/rating/v1/Shop", headers=headers, data=json.dumps(body), timeout=15)
    r.raise_for_status()
    return r.json()
