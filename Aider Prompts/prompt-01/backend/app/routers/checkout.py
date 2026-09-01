from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.deps.auth import get_current_user
from app.schemas.checkout import ShippingRateRequest, ShippingRatesResponse
from app.services.shipping_ups import get_ups_rates
import httpx

router = APIRouter(prefix="/checkout", tags=["checkout"])

@router.post("/shipping-rates", response_model=ShippingRatesResponse, responses={401: {"description": "Missing auth"}, 422: {"description": "Invalid"}})
async def shipping_rates(req: ShippingRateRequest, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    dest = {
        "AddressLine": [req.destination.line1] + ([req.destination.line2] if req.destination.line2 else []),
        "City": req.destination.city,
        "StateProvinceCode": req.destination.state,
        "PostalCode": req.destination.postal_code,
        "CountryCode": req.destination.country,
    }
    try:
        item_pairs = [(it.product_id, it.quantity) for it in req.items]
        rates = await get_ups_rates(db, item_pairs, dest)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"UPS error: {e.response.text}")
    return {"rates": rates}
