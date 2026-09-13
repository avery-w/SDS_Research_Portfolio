from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ChatMessage, User
from ..schemas import ChatRequest, ChatResponse
from ..chatbot import get_reply

router = APIRouter(prefix="/api/chat", tags=["chat"])

HISTORY_LIMIT = 10


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in reversed(history_rows)]

    reply, suggest = get_reply(payload.message, history)

    db.add(ChatMessage(user_id=user.id, role="user", content=payload.message))
    db.add(ChatMessage(user_id=user.id, role="assistant", content=reply))
    db.commit()

    return ChatResponse(reply=reply, suggest_contact_seller=suggest)
