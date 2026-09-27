from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessageResponse
from app.utils.security import get_current_user
from app.services.chatbot_service import ChatbotService

router = APIRouter(prefix="/api/chat", tags=["chatbot"])
chatbot = ChatbotService()


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    seller_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == seller_id, User.role == UserRole.SELLER))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    session = ChatSession(customer_id=current_user.id, seller_id=seller_id)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return {"session_id": session.id}


@router.get("/sessions", response_model=list[dict])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            (ChatSession.customer_id == current_user.id) | (ChatSession.seller_id == current_user.id)
        )
    )
    sessions = result.scalars().all()
    return [{"id": s.id, "customer_id": s.customer_id, "seller_id": s.seller_id, "is_active": s.is_active} for s in sessions]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.id not in (session.customer_id, session.seller_id) and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()


@router.post("/ai", response_model=ChatResponse)
async def ai_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = await db.execute(select(ChatSession).where(ChatSession.id == request.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.id not in (session.customer_id, session.seller_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    msg_result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == request.session_id).order_by(ChatMessage.created_at.desc()).limit(20)
    )
    history = [
        {"role": "user" if m.sender_id == current_user.id else "assistant", "content": m.content}
        for m in reversed(msg_result.scalars().all())
    ]

    ai_response = await chatbot.generate_response(request.message, history)

    user_msg = ChatMessage(session_id=request.session_id, sender_id=current_user.id, content=request.message)
    ai_msg = ChatMessage(session_id=request.session_id, sender_id=current_user.id, content=ai_response["reply"], is_ai_generated=True)
    db.add_all([user_msg, ai_msg])
    await db.flush()

    return ChatResponse(
        reply=ai_response["reply"],
        suggested_action=ai_response["suggested_action"],
        should_redirect_to_seller=ai_response["should_redirect_to_seller"],
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    session_id: int,
    content: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.id not in (session.customer_id, session.seller_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    msg = ChatMessage(session_id=session_id, sender_id=current_user.id, content=content)
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg
