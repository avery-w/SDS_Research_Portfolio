import httpx
from app.config import settings


class ShippingService:
    UPS_API_BASE = "https://onlinetools.ups.com/api/rating/v2405/Rate"

    async def calculate_shipping(
        self,
        destination_zip: str,
        destination_country: str = "US",
        weight_oz: float = 16.0,
        dimensions: dict | None = None,
        service_code: str = "03",
    ) -> dict:
        payload = {
            "RateRequest": {
                "Request": {
                    "TransactionReference": {"CustomerContext": "Marketplace"},
                    "RequestAction": "Rate",
                    "RequestOption": "Shop",
                },
                "Shipment": {
                    "Shipper": {
                        "Address": {
                            "AddressLine": ["110 Inner Campus Drive"],
                            "City": "Austin",
                            "State": "TX",
                            "PostalCode": "78705",
                            "Country": "US",
                        }
                    },
                    "ShipTo": {
                        "Address": {
                            "PostalCode": destination_zip,
                            "Country": destination_country,
                        }
                    },
                    "Package": [
                        {
                            "PackageService": {"Code": service_code},
                            "Packaging": {"Code": "02"},
                            "Dimensions": dimensions or {"Length": "10", "Width": "10", "Height": "10"},
                            "Weight": {"Code": "2", "Weight": str(weight_oz)},
                        }
                    ],
                },
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.UPS_API_BASE,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "AccessLicenseNumber": settings.UPS_ACCESS_KEY,
                    "Username": settings.UPS_API_KEY,
                    "Password": settings.UPS_API_PASSWORD,
                },
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_ups_response(data)

    def _parse_ups_response(self, data: dict) -> dict:
        try:
            rate_response = data["RateResponse"]["Shipment"]["ShipmentResponse"]
            service = rate_response["Service"]["Code"]
            cost = float(rate_response["RateCharge"]["MonetaryValue"])
            currency = rate_response["RateCharge"]["CurrencyCode"]
            return {
                "cost": cost,
                "currency": currency,
                "service": service,
                "origin": settings.UPS_ORIGIN_ADDRESS,
            }
        except (KeyError, TypeError, ValueError):
            return {"cost": 0.0, "currency": "USD", "service": "unknown", "origin": settings.UPS_ORIGIN_ADDRESS}

    def calculate_fallback_rate(self, weight_oz: float, destination_zip: str) -> float:
        base = 5.99
        weight_surcharge = max(0, (weight_oz - 16) / 16) * 1.50
        return round(base + weight_surcharge, 2)
