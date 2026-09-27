from fastapi import APIRouter, HTTPException
from app.schemas.shipping import ShippingQuoteRequest, ShippingQuoteResponse
from app.services.shipping_service import calculate_shipping

router = APIRouter(prefix="/shipping", tags=["shipping"])


@router.post("/quote", response_model=ShippingQuoteResponse)
async def get_shipping_quote(data: ShippingQuoteRequest):
    try:
        return await calculate_shipping(data.destination_address, data.weight, data.dimensions)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Shipping quote failed: {str(e)}")
