import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.order import OrderResponse
from app.services.order_service import create_order_from_cart
from app.services.shipping_service import calculate_shipping
from app.schemas.shipping import ShippingQuoteRequest, ShippingQuoteResponse

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post("", response_model=OrderResponse, status_code=201)
async def checkout(data: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    shipping_address = data.get("shipping_address")
    shipping_method = data.get("shipping_method")
    if not shipping_address:
        raise HTTPException(status_code=400, detail="shipping_address required")
    try:
        order = await create_order_from_cart(db, user.id, shipping_address, shipping_method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return OrderResponse.model_validate(order)


@router.post("/preview", response_model=ShippingQuoteResponse)
async def preview(data: ShippingQuoteRequest, user: User = Depends(get_current_user)):
    try:
        return await calculate_shipping(data.destination_address, data.weight, data.dimensions)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Shipping quote failed: {str(e)}")
