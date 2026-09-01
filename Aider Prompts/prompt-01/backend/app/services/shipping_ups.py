from typing import Sequence
import httpx
from decimal import Decimal
from app.core.config import settings
from app.models.product import Product
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

UPS_SANDBOX = "https://wwwcie.ups.com"
UPS_PROD = "https://onlinetools.ups.com"

ORIGIN = {
    "AddressLine": ["110 Inner Campus Drive"],
    "City": "Austin",
    "StateProvinceCode": "TX",
    "PostalCode": "78705",
    "CountryCode": "US",
}

def _billable_weight_lbs(w_lbs: Decimal, l_in: Decimal, w_in: Decimal, h_in: Decimal) -> str:
    dim_weight = (l_in * w_in * h_in) / Decimal(139)  # UPS dim divisor for inches/lbs
    billable = max(w_lbs, dim_weight).quantize(Decimal("1.0"))
    return str(billable)

async def _ups_token() -> str:
    base = UPS_SANDBOX if settings.UPS_ENV == "sandbox" else UPS_PROD
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            f"{base}/security/v1/oauth/token",
            data={"grant_type": "client_credentials"},
            auth=(settings.UPS_CLIENT_ID or "", (settings.UPS_CLIENT_SECRET.get_secret_value() if settings.UPS_CLIENT_SECRET else "")),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        return r.json()["access_token"]

async def get_ups_rates(db: AsyncSession, items: Sequence[tuple[int, int]], destination: dict) -> list[dict]:
    """
    items: list of (product_id, quantity)
    destination: {"AddressLine": [..], "City": "", "StateProvinceCode": "", "PostalCode": "", "CountryCode": "US"}
    """
    # Load products
    product_ids = [pid for pid, _ in items]
    products = (await db.execute(select(Product).where(Product.id.in_(product_ids)))).scalars().all()
    # Build packages (naive: one package per product type)
    packages = []
    for (pid, qty) in items:
        p = next((x for x in products if x.id == pid), None)
        if not p: continue
        for _ in range(qty):
            billable = _billable_weight_lbs(Decimal(p.weight_lbs), Decimal(p.length_in), Decimal(p.width_in), Decimal(p.height_in))
            packages.append({
                "PackagingType": {"Code": "02", "Description": "Customer Supplied"},
                "PackageWeight": {"UnitOfMeasurement": {"Code": "LBS"}, "Weight": billable},
                "Dimensions": {"UnitOfMeasurement": {"Code": "IN"}, "Length": str(p.length_in), "Width": str(p.width_in), "Height": str(p.height_in)},
            })
    if not packages:
        return []

    # Build RateRequest with "Shop" to return all services
    body = {
        "RateRequest": {
            "Request": {"RequestOption": "Shop"},
            "Shipment": {
                "Shipper": {
                    "ShipperNumber": settings.UPS_ACCOUNT_NUMBER or "",
                    "Address": ORIGIN
                },
                "ShipTo": {"Address": destination},
                "ShipFrom": {"Address": ORIGIN},
                "Package": packages
            }
        }
    }

    base = UPS_SANDBOX if settings.UPS_ENV == "sandbox" else UPS_PROD
    token = await _ups_token()
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            f"{base}/api/rating/v2205/Rate",
            json=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
        )
        r.raise_for_status()
        data = r.json()

    # Parse returned rates into cents
    rates = []
    for srvc in (data.get("RateResponse", {}).get("RatedShipment", []) or []):
        svc_code = srvc.get("Service", {}).get("Code")
        total = srvc.get("TotalCharges", {}).get("MonetaryValue", "0")
        name = srvc.get("Service", {}).get("Description", svc_code)
        try:
            cents = int(Decimal(total) * Decimal(100))
        except Exception:
            cents = 0
        rates.append({"service_code": svc_code, "service_name": name, "total_cents": cents})
    return rates
