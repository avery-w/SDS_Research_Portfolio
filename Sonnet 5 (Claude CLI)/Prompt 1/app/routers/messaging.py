from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..deps import get_current_user
from ..models import SellerMessage, User
from ..schemas import MessageCreate, MessageOut

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(payload: MessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.recipient_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't message yourself")
    recipient = db.get(User, payload.recipient_id)
    if recipient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipient not found")

    msg = SellerMessage(
        sender_id=user.id, recipient_id=payload.recipient_id,
        product_id=payload.product_id, order_id=payload.order_id, body=payload.body,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.get("", response_model=list[MessageOut])
def list_my_messages(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(SellerMessage)
        .filter(or_(SellerMessage.sender_id == user.id, SellerMessage.recipient_id == user.id))
        .order_by(SellerMessage.created_at.asc())
        .all()
    )
