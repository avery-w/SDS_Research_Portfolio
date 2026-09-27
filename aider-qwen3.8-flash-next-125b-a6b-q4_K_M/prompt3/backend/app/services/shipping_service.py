import httpx
import json
from app.config import get_settings
from app.schemas.shipping import ShippingQuoteResponse

settings = get_settings()
UPS_TOKEN_URL = "https://onlinetools.ups.com/security/v1/oauth/token"
UPS_RATE_URL = "https://onlinetools.ups.com/api/rates/v1/rates"


async def get_ups_token() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            UPS_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(settings.UPS_CLIENT_ID, settings.UPS_CLIENT_SECRET),
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def calculate_shipping(destination: dict, weight: float, dimensions: dict) -> ShippingQuoteResponse:
    token = await get_ups_token()
    origin = {
        "Address": {
            "AddressLine": ["110 Inner Campus Drive"],
            "City": "Austin",
            "State": "TX",
            "PostalCode": "78705",
            "CountryCode": "US",
        }
    }
    dest = {
        "Address": {
            "AddressLine": [destination.get("street", "")],
            "City": destination.get("city", ""),
            "State": destination.get("state", ""),
            "PostalCode": destination.get("zip", ""),
            "CountryCode": destination.get("country", "US"),
        }
    }
    payload = {
        "RateRequest": {
            "Request": {"TransactionReference": {"CustomerContext": "marketplace"}},
            "Shipment": {
                "Shipper": origin,
                "ShipTo": dest,
                "Package": {
                    "Dimensions": {
                        "UnitOfMeasurement": {"Code": "IN"},
                        "Length": str(dimensions.get("length", 10)),
                        "Width": str(dimensions.get("width", 10)),
                        "Height": str(dimensions.get("height", 10)),
                    },
                    "PackageWeight": {
                        "UnitOfMeasurement": {"Code": "LB"},
                        "Weight": str(weight),
                    },
                },
            },
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            UPS_RATE_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        rate = data["RateResponse"]["Shipment"]["Rate"][0]
        return ShippingQuoteResponse(
            service=rate["Service"]["Description"],
            estimated_delivery=rate.get("TimeInTransit", {}).get("ServiceDescription", "N/A"),
            cost=float(rate["RateCharge"][0]["MonetaryValue"]["Amount"]),
        )
