import uuid
from datetime import datetime
from pydantic import BaseModel


class StoreCreate(BaseModel):
    store_name: str
    description: str | None = None
    address: dict | None = None


class StoreResponse(BaseModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    store_name: str
    description: str | None
    logo_url: str | None
    banner_url: str | None
    address: dict | None
    is_active: bool
    rating: float
    created_at: datetime

    class Config:
        from_attributes = True
