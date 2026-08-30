from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_current_active_user
from app.database import get_session
from app.models import User
from app.schemas import ChatRequest, ChatResponse
from app.chatbot import generate_chatbot_reply

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("/", response_model=ChatResponse)
async def chatbot(request: ChatRequest, current_user: User = Depends(get_current_active_user)):
    reply = generate_chatbot_reply(request.message, request.context)
    return {"reply": reply}
