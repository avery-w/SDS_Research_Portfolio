from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_current_active_user
from app.database import get_session
from app.models import Message, User, UserRole
from app.schemas import MessageCreate, MessageRead

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def send_message(message: MessageCreate, current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    receiver = session.get(User, message.receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")
    db_message = Message(sender_id=current_user.id, receiver_id=message.receiver_id, order_id=message.order_id, content=message.content)
    session.add(db_message)
    session.commit()
    session.refresh(db_message)
    return db_message


@router.get("/", response_model=list[MessageRead])
def list_messages(current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    return session.exec(
        select(Message).where((Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)).order_by(Message.created_at)
    ).all()


@router.get("/unread", response_model=list[MessageRead])
def unread_messages(current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    return session.exec(select(Message).where(Message.receiver_id == current_user.id, Message.is_read == False)).all()
