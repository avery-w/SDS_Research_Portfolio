from pydantic import BaseModel, Field
from datetime import datetime


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    description: str | None = None
    logo_url: str | None = None
    banner_url: str | None = None


class StoreUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    logo_url: str | None = None
    banner_url: str | None = None
    is_active: bool | None = None


class StoreResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    logo_url: str | None
    banner_url: str | None
    is_active: bool
    rating: int
    total_reviews: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
