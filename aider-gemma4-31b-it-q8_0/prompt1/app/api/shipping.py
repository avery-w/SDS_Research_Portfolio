from fastapi import APIRouter, Depends
from app.schemas.schemas import ShippingRequest, ShippingResponse
from app.services.shipping_service import ShippingService
from app.api.deps import get_db

router = APIRouter()
shipping_service = ShippingService()

@router.post("/calculate", response_model=ShippingResponse)
async def calculate_shipping(request: ShippingRequest):
    rate_data = await shipping_service.calculate_lowest_rate(
        request.destination_zip, 
        request.weight
    )
    return rate_data
