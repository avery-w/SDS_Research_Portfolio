from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.deps.auth import get_current_user
from app.models.messaging import Conversation, Message, ParticipantRole

router = APIRouter(prefix="/messages", tags=["messages"])

@router.post("/start", responses={401: {"description": "Missing auth"}, 422: {"description": "Invalid"}})
async def start_conversation(seller_user_id: int, product_id: int | None = None, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    convo = Conversation(customer_id=user.id, seller_user_id=seller_user_id, product_id=product_id)
    db.add(convo); await db.commit(); await db.refresh(convo)
    return {"id": convo.id}

@router.post("/{conversation_id}/send", responses={401: {"description": "Missing auth"}, 403: {"description": "Unauthorized"}})
async def send_message(conversation_id: int, body: str, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    convo = (await db.execute(select(Conversation).where(Conversation.id == conversation_id))).scalar_one_or_none()
    if not convo: raise HTTPException(status_code=404, detail="Conversation not found")
    if user.id not in (convo.customer_id, convo.seller_user_id):
        raise HTTPException(status_code=403, detail="Not a participant")
    role = ParticipantRole.customer if user.id == convo.customer_id else ParticipantRole.seller
    msg = Message(conversation_id=convo.id, sender_id=user.id, sender_role=role, body=body)
    db.add(msg); await db.commit(); await db.refresh(msg)
    return {"id": msg.id}
