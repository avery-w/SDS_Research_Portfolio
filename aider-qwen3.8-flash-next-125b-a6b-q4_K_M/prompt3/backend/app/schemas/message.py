import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    seller_id: uuid.UUID
    product_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    seller_id: uuid.UUID
    product_id: uuid.UUID | None
    order_id: uuid.UUID | None
    created_at: datetime
    messages: list["MessageResponse"] = []

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    attachments: list[str] | None = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    attachments: list[str] | None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
