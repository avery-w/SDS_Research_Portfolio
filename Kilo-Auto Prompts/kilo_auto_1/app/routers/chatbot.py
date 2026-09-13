"""AI Chatbot endpoint."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ChatbotConversation, ChatbotMessage, User
from app.schemas import ChatbotMessageCreate, ChatbotMessageRead
from app.chatbot import chatbot_respond
from app.permissions import get_current_user, role_required
from app.security import get_current_user as _cb

router = APIRouter()


@router.post("/chat", response_model=ChatbotMessageRead)
async def chatbot_chat(
    payload: ChatbotMessageCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the AI chatbot."""
    session_id = payload.session_id
    if not session_id:
        import uuid as _uuid
        session_id = str(_uuid.uuid4())
    else:
        result = await db.execute(
            select(ChatbotConversation).where(
                ChatbotConversation.session_id == session_id
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            conv = ChatbotConversation(
                session_id=session_id, user_id=current_user.id
            )
            db.add(conv)
            await db.flush()

    result = await db.execute(
        select(ChatbotConversation).where(
            ChatbotConversation.session_id == session_id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        conv = ChatbotConversation(
            session_id=session_id, user_id=current_user.id
        )
        db.add(conv)
        await db.flush()

    bot_message = ChatbotMessage(
        conversation_id=conv.id, sender="user", message=payload.message
    )
    db.add(bot_message)
    await db.flush()

    response = await chatbot_respond(
        payload.message,
        user_id=current_user.id,
        session_id=session_id,
        product_id=payload.product_id,
        order_id=payload.order_id,
        history=[
            {"sender": m.sender, "message": m.message}
            for m in conv.messages
        ],
    )

    bot_msg = ChatbotMessage(
        conversation_id=conv.id, sender="bot", message=response["response"]
    )
    db.add(bot_msg)
    conv.updated_at = conv.updated_at
    await db.commit()

    return ChatbotMessageRead(
        sender=bot_msg.sender,
        message=bot_msg.message,
        created_at=bot_msg.created_at,
    )


@router.get("/history", response_model=list[ChatbotMessageRead])
async def chatbot_history(
    session_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for the current user."""
    stmt = select(ChatbotConversation)
    if session_id:
        stmt = stmt.where(ChatbotConversation.session_id == session_id)
    else:
        stmt = stmt.where(ChatbotConversation.user_id == current_user.id)
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    messages = []
    for conv in conversations:
        for msg in conv.messages:
            messages.append(
                ChatbotMessageRead(
                    sender=msg.sender,
                    message=msg.message,
                    created_at=msg.created_at,
                )
            )
    return messages
