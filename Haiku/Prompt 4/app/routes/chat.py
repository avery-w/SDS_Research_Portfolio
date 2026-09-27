from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_active_user
from app.services.chatbot import get_chatbot_response

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/message", response_model=schemas.Message)
def send_message(
    message: schemas.MessageBase,
    order_id: int = None,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if order_id:
        order = db.query(models.Order).filter(models.Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.customer_id != current_user.id and current_user.role == models.UserRole.CUSTOMER:
            raise HTTPException(status_code=403, detail="Not authorized")

    db_message = models.Message(
        user_id=current_user.id,
        order_id=order_id,
        sender_role=current_user.role,
        content=message.content,
        is_from_chatbot=False
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    if current_user.role == models.UserRole.CUSTOMER and not order_id:
        response = get_chatbot_response(message.content)
        chatbot_msg = models.Message(
            user_id=current_user.id,
            order_id=None,
            sender_role=models.UserRole.CUSTOMER,
            content=response,
            is_from_chatbot=True
        )
        db.add(chatbot_msg)
        db.commit()

    return db_message

@router.get("/messages", response_model=list[schemas.Message])
def get_messages(
    order_id: int = None,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Message)

    if order_id:
        order = db.query(models.Order).filter(models.Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.customer_id != current_user.id and current_user.role == models.UserRole.CUSTOMER:
            raise HTTPException(status_code=403, detail="Not authorized")
        query = query.filter(models.Message.order_id == order_id)
    else:
        query = query.filter(models.Message.user_id == current_user.id)

    messages = query.all()
    return messages

@router.get("/suggestions")
def get_chatbot_suggestions(current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != models.UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Only customers can use chatbot")

    return {
        "suggestions": [
            "How do I track my order?",
            "What is your return policy?",
            "How long does shipping take?",
            "Can I contact a seller?",
            "How do I reset my password?"
        ]
    }
