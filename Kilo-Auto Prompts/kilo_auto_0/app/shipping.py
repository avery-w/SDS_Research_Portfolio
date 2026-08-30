import httpx
from app.config import (
    UPS_USERNAME,
    UPS_PASSWORD,
    UPS_ACCESS_KEY,
    UPS_ORIGIN_ADDRESS,
    UPS_ORIGIN_CITY,
    UPS_ORIGIN_STATE,
    UPS_ORIGIN_ZIP,
    UPS_ORIGIN_COUNTRY,
)


async def get_ups_shipping_rates(
    dest_zip: str,
    dest_country: str,
    weight_lbs: float,
    length_in: float,
    width_in: float,
    height_in: float,
) -> float | None:
    url = "https://onlinetools.ups.com/rest/Rate"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {
        "UPSSecurity": {
            "UsernameToken": {"Username": UPS_USERNAME, "Password": UPS_PASSWORD},
            "ServiceAccessToken": {"AccessLicenseNumber": UPS_ACCESS_KEY},
        },
        "RateRequest": {
            "Request": {"TransactionReference": {"CustomerContext": "Marketplace"}},
            "Shipment": {
                "Shipper": {
                    "Address": {
                        "AddressLine": [UPS_ORIGIN_ADDRESS],
                        "City": UPS_ORIGIN_CITY,
                        "StateProvinceCode": UPS_ORIGIN_STATE,
                        "PostalCode": UPS_ORIGIN_ZIP,
                        "CountryCode": UPS_ORIGIN_COUNTRY,
                    }
                },
                "ShipTo": {
                    "Address": {
                        "PostalCode": dest_zip,
                        "CountryCode": dest_country,
                        "ResidentialAddress": "01",
                    }
                },
                "Package": [
                    {
                        "PackagingType": {"Code": "02"},
                        "PackageWeight": {
                            "UnitOfMeasurement": {"Code": "LBS"},
                            "Weight": str(weight_lbs),
                        },
                        "Dimensions": {
                            "UnitOfMeasurement": {"Code": "IN"},
                            "Length": str(length_in),
                            "Width": str(width_in),
                            "Height": str(height_in),
                        },
                    }
                ],
            },
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            rate = data["RateResponse"]["RatedShipment"]["TotalCharges"]["MonetaryValue"]
            return float(rate)
    except Exception:
        return None
