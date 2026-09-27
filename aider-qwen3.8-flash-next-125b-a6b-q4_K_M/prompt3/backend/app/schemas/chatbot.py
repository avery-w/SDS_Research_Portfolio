import uuid
from pydantic import BaseModel


class ChatbotRequest(BaseModel):
    question: str
    context_type: str | None = None  # "product" | "order" | None
    context_id: uuid.UUID | None = None


class ChatbotResponse(BaseModel):
    answer: str
    suggest_seller_message: bool = False
    suggested_conversation_id: uuid.UUID | None = None
