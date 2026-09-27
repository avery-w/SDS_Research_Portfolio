from fastapi import APIRouter, Depends, HTTPException
from app.services.shipping_service import ShippingService
from app.utils.validators import validate_zip
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/shipping", tags=["shipping"])
shipping_service = ShippingService()


@router.get("/estimate")
async def estimate_shipping(
    zip_code: str,
    weight_oz: float = 16.0,
    current_user: User = Depends(get_current_user),
):
    if not validate_zip(zip_code):
        raise HTTPException(status_code=422, detail="Invalid zip code format")
    if weight_oz <= 0 or weight_oz > 150:
        raise HTTPException(status_code=422, detail="Weight must be between 0 and 150 oz")
    try:
        result = await shipping_service.calculate_shipping(destination_zip=zip_code, weight_oz=weight_oz)
        return result
    except Exception:
        cost = shipping_service.calculate_fallback_rate(weight_oz, zip_code)
        return {"cost": cost, "currency": "USD", "service": "fallback", "origin": "110 Inner Campus Drive, Austin, TX 78705"}
