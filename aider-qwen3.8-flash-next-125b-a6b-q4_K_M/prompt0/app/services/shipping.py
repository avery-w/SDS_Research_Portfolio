import requests
import json
from flask import current_app

class ShippingService:
    """
    Calculates shipping rates using the UPS Rating API.
    Origin is fixed at 110 Inner Campus Drive, Austin, TX 78705.
    """

    UPS_RATING_URL = "https://onlinetools.ups.com/api/rating/v2405/Rate"

    @classmethod
    def get_shipping_rates(cls, dest_street, dest_city, dest_state, dest_zip,
                           weight_oz, length_in, width_in, height_in):
        """
        Call UPS Rating API and return a list of rate dicts:
        [{"service": "Ground", "cost": 12.50, "days": 5}, ...]
        """
        cfg = current_app.config
        origin = cfg["UPS_ORIGIN_ADDRESS"]

        payload = {
            "Request": {
                "RequestOption": "shop",
                "TransactionReference": {"CustomerContext": "Marketplace"}
            },
            "Shipment": {
                "Description": "Marketplace Shipment",
                "Shipper": {
                    "Name": "Marketplace",
                    "Address": {
                        "AddressLine": origin["street"],
                        "City": origin["city"],
                        "StateProvince": origin["state"],
                        "PostalCode": origin["zip"],
                        "CountryCode": origin["country"]
                    }
                },
                "ShipTo": {
                    "Name": "Customer",
                    "Address": {
                        "AddressLine": dest_street,
                        "City": dest_city,
                        "StateProvince": dest_state,
                        "PostalCode": dest_zip,
                        "CountryCode": "US"
                    }
                },
                "Package": {
                    "Description": "Package",
                    "PackagingType": {"Code": "02"},
                    "Dimensions": {
                        "Unit": "IN",
                        "Length": str(length_in),
                        "Width": str(width_in),
                        "Height": str(height_in)
                    },
                    "PackageWeight": {
                        "Unit": "LB",
                        "Weight": str(round(weight_oz / 16, 2))
                    }
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "AccessLicenseNumber": cfg["UPS_ACCESS_KEY"],
            "Username": cfg["UPS_API_USERNAME"],
            "Password": cfg["UPS_API_PASSWORD"],
        }

        try:
            resp = requests.post(
                cls.UPS_RATING_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            return cls._parse_rates(data)
        except requests.RequestException as e:
            current_app.logger.error(f"UPS API error: {e}")
            return cls._fallback_rates(weight_oz)

    @classmethod
    def _parse_rates(cls, data):
        """Parse UPS Rating response into simplified rate list."""
        rates = []
        try:
            shipment = data["RateResponse"]["Shipment"]
            for rate in shipment.get("Rate", []):
                service_code = rate.get("Service", {}).get("Code", "")
                service_desc = rate.get("Service", {}).get("Description", "")
                cost_str = rate.get("RateChargeSummary", {}).get("TotalCharge", {}).get("MonetaryValue", "0")
                rates.append({
                    "service_code": service_code,
                    "service": service_desc,
                    "cost": float(cost_str),
                    "days": cls._estimate_days(service_code),
                })
        except (KeyError, TypeError) as e:
            current_app.logger.error(f"UPS response parse error: {e}")
        return rates

    @classmethod
    def _estimate_days(cls, service_code):
        mapping = {"03": 1, "14": 2, "13": 3, "12": 4, "01": 5, "02": 5}
        return mapping.get(service_code, 5)

    @classmethod
    def _fallback_rates(cls, weight_oz):
        """Return estimated rates when UPS API is unavailable."""
        weight_lb = weight_oz / 16
        base = 5.00
        return [
            {"service_code": "03", "service": "UPS Next Day Air", "cost": round(base + weight_lb * 2.5, 2), "days": 1},
            {"service_code": "14", "service": "UPS 2nd Day Air", "cost": round(base + weight_lb * 1.5, 2), "days": 2},
            {"service_code": "02", "service": "UPS Ground", "cost": round(base + weight_lb * 0.8, 2), "days": 5},
        ]
