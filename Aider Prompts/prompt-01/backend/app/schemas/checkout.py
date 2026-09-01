from pydantic import BaseModel, Field
from typing import List

class PackageItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)

class AddressIn(BaseModel):
    name: str
    line1: str
    line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    phone: str | None = None

class ShippingRateRequest(BaseModel):
    items: List[PackageItem]
    destination: AddressIn

class ShippingRate(BaseModel):
    service_code: str
    service_name: str
    total_cents: int
    eta_days: int | None = None

class ShippingRatesResponse(BaseModel):
    rates: list[ShippingRate]
