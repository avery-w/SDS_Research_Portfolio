import requests
from app.config import Config

def calculate_ups_shipping(origin_zip: str, dest_zip: str, weight_lbs: float, dimensions: tuple) -> dict:
    """
    Call UPS Rating API v2405.
    origin_zip is always Config.UPS_ORIGIN_ZIP ("78705").
    Returns dict with cost, service, estimated_delivery.
    """
    payload = {
        "Request": {
            "RequestOption": "shop",
            "TransactionReference": {"CustomerContext": "marketplace"}
        },
        "Shipment": {
            "Shipper": {
                "Address": {
                    "AddressLine": ["110 Inner Campus Drive"],
                    "City": "Austin",
                    "State": "TX",
                    "PostalCode": origin_zip,
                    "Country": "US"
                }
            },
            "ShipTo": {
                "Address": {
                    "PostalCode": dest_zip,
                    "Country": "US"
                }
            },
            "Package": [{
                "Dimensions": {
                    "UnitOfMeasurement": {"Code": "IN"},
                    "Length": str(dimensions[0]),
                    "Width": str(dimensions[1]),
                    "Height": str(dimensions[2])
                },
                "PackageWeight": {
                    "UnitOfMeasurement": {"Code": "LB"},
                    "Weight": str(weight_lbs)
                }
            }]
        }
    }
    headers = {
        "Content-Type": "application/json",
        "AccessLicenseNumber": Config.UPS_API_KEY,
        "transId": "marketplace",
        "transactionSrc": "marketplace"
    }
    resp = requests.post(Config.UPS_API_URL, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # Parse UPS response into simplified structure
    rate = data["RateResponse"]["RatedShipment"]
    return {
        "cost": float(rate["TotalCharges"]["MonetaryValue"]),
        "currency": rate["TotalCharges"]["CurrencyCode"],
        "service": rate["Service"]["Code"],
        "estimated_delivery": rate.get("Service", {}).get("Description", "N/A")
    }
