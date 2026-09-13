"""Shipping rate endpoint (UPS)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.shipping import calculate_ups_rates


class ShippingRequest(BaseModel):
    weight_lbs: float = Field(..., gt=0, description="Package weight in lbs")
    destination_zip: str = Field(..., min_length=5, max_length=5, description="Destination 5-digit ZIP code")
    length: Optional[float] = Field(None, ge=0, description="Length in inches")
    width: Optional[float] = Field(None, ge=0, description="Width in inches")
    height: Optional[float] = Field(None, ge=0, description="Height in inches")
    is_residential: bool = Field(False, description="Residential delivery")
    services: Optional[str] = Field(None, description="Comma-separated service keys")

router = APIRouter()


@router.post("/rates", response_model=dict)
async def shipping_rates(payload: ShippingRequest):
    """Calculate UPS shipping rates from Austin, TX 78705."""
    import re
    if not re.match(r"^\d{5}$", payload.destination_zip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="destination_zip must be a 5-digit US ZIP code.",
        )
    svc_list = None
    if payload.services:
        svc_list = [s.strip() for s in payload.services.split(",") if s.strip()]
    try:
        estimate = calculate_ups_rates(
            weight_lbs=payload.weight_lbs,
            destination_zip=payload.destination_zip,
            length=payload.length,
            width=payload.width,
            height=payload.height,
            is_residential=payload.is_residential,
            services=svc_list,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return {
        "origin": estimate.origin,
        "destination_zip": estimate.destination_zip,
        "rates": [
            {
                "service": r.service,
                "service_name": r.service_name,
                "rate": r.rate,
                "estimated_days": r.estimated_business_days,
                "currency": r.currency,
            }
            for r in estimate.rates
        ],
        "package": estimate.package,
    }
