from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.deps.auth import get_current_user, require_roles
from app.models.returns import ReturnRequest, ReturnStatus
from app.models.order import Order
from app.models.user import Role, User

router = APIRouter(prefix="/returns", tags=["returns"])

@router.post("", responses={401: {"description": "Missing auth"}, 422: {"description": "Invalid"}})
async def request_return(order_id: int, reason: str, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order or order.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")
    rr = ReturnRequest(order_id=order_id, customer_id=user.id, reason=reason)
    db.add(rr); await db.commit(); await db.refresh(rr)
    return {"id": rr.id, "status": rr.status}

@router.post("/{return_id}/decision", responses={401: {"description": "Missing auth"}, 403: {"description": "Unauthorized"}})
async def decide_return(return_id: int, approve: bool, db: AsyncSession = Depends(get_session), user: User = Depends(require_roles(Role.seller, Role.admin))):
    rr = (await db.execute(select(ReturnRequest).where(ReturnRequest.id == return_id))).scalar_one_or_none()
    if not rr: raise HTTPException(status_code=404, detail="Return not found")
    rr.status = ReturnStatus.approved if approve else ReturnStatus.rejected
    await db.commit()
    return {"status": rr.status}
