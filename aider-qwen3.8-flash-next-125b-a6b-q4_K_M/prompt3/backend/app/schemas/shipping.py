from pydantic import BaseModel


class ShippingQuoteRequest(BaseModel):
    destination_address: dict
    weight: float
    dimensions: dict  # {"length": float, "width": float, "height": float}


class ShippingQuoteResponse(BaseModel):
    service: str
    estimated_delivery: str
    cost: float
    currency: str = "USD"
