from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_customer, verify_csrf
from app.limiter import limiter
from app.models import ChatMessage, User
from app.services.ai_chat import get_chat_reply

router = APIRouter()
templates = Jinja2Templates(directory="templates")

HISTORY_LIMIT = 20


@router.get("/chat")
def chat_page(request: Request, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    history = db.scalars(
        select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.created_at)
    ).all()
    return templates.TemplateResponse(request, "chat.html", {"user": user, "history": history})


@router.post("/chat", dependencies=[Depends(verify_csrf)])
@limiter.limit("20/minute")
def chat_send(
    request: Request,
    message: str = Form(...),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    message = message.strip()[:2000]
    if not message:
        return chat_page(request, user, db)

    db.add(ChatMessage(user_id=user.id, role="user", content=message))
    db.commit()

    recent = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
    ).all()
    recent = list(reversed(recent))
    history = [{"role": m.role, "content": m.content} for m in recent]

    reply = get_chat_reply(history)
    db.add(ChatMessage(user_id=user.id, role="assistant", content=reply))
    db.commit()

    return chat_page(request, user, db)
