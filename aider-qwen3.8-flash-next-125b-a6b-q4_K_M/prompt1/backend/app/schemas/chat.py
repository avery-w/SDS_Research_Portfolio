from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    session_id: int
    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    reply: str
    suggested_action: str
    should_redirect_to_seller: bool


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    sender_id: int
    content: str
    is_ai_generated: bool
    created_at: datetime

    class Config:
        from_attributes = True
