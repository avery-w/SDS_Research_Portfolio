from fastapi import APIRouter, Depends
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.ai_service import AIService

router = APIRouter()
ai_service = AIService()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # In a real app, we would fetch product metadata from DB using request.product_id
    product_metadata = f"Product ID {request.product_id}" if request.product_id else None
    
    response_text = await ai_service.get_chat_response(
        request.message, 
        product_metadata
    )
    return ChatResponse(response=response_text)
