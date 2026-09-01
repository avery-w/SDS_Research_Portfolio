from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.deps.auth import require_roles
from app.db.session import get_session
from app.models.user import Role
from app.models.order import Order, OrderItem

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/sales-summary", responses={401: {"description": "Missing auth"}, 403: {"description": "Admin only"}})
async def sales_summary(db: AsyncSession = Depends(get_session), admin=Depends(require_roles(Role.admin))):
    gmv = (await db.execute(select(func.sum(Order.total_cents)))).scalar() or 0
    orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    units = (await db.execute(select(func.sum(OrderItem.quantity)))).scalar() or 0
    aov = int(gmv / orders) if orders else 0
    return {"gmv_cents": int(gmv), "orders": int(orders), "units": int(units), "aov_cents": aov}
