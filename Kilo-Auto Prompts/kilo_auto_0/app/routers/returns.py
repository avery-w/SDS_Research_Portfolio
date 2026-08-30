from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_current_active_user, require_role
from app.database import get_session
from app.models import Order, ReturnRequest, Store, User, UserRole
from app.schemas import ReturnRequestCreate, ReturnRequestRead

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/{order_id}/return", response_model=ReturnRequestRead, status_code=status.HTTP_201_CREATED)
def request_return(order_id: int, request_in: ReturnRequestCreate, current_user: User = Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN)), session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    existing = session.exec(select(ReturnRequest).where(ReturnRequest.order_id == order_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Return request already exists")
    db_return = ReturnRequest(order_id=order_id, reason=request_in.reason)
    session.add(db_return)
    session.commit()
    session.refresh(db_return)
    return db_return
