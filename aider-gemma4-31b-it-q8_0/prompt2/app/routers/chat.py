from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .database import get_db
from . import models, schemas
from .services.ai_bot import ChatBotService

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])

@router.post("/", response_model=schemas.ChatResponse)
def chat(
    request: schemas.ChatRequest, 
    db: Session = Depends(get_db)
):
    product_desc = None
    if request.product_id:
        product = db.query(models.Product).filter(models.Product.id == request.product_id).first()
        if product:
            product_desc = product.description

    response_text = ChatBotService.get_response(request.message, product_desc)
    return {"response": response_text}
