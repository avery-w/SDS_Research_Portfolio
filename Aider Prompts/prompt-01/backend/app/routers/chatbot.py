from fastapi import APIRouter, Depends
from app.deps.auth import get_current_user
from app.services.chatbot import ask_chatbot

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", responses={401: {"description": "Missing auth"}, 422: {"description": "Invalid"}})
async def chat(messages: list[dict], user=Depends(get_current_user)):
    # messages = [{"role": "user"|"assistant", "content": "..."}]
    answer = ask_chatbot(messages)
    return {"answer": answer, "cta": "If this is about a specific product or order, use 'Message Seller' to contact them directly."}
