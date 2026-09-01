from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.deps.auth import require_roles
from app.models.user import Role, User
from app.db.session import get_session
from app.models.product import Product
from app.models.order import Order, OrderStatus

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/users/{user_id}/deactivate", responses={401: {"description": "Missing auth"}, 403: {"description": "Admin only"}})
async def deactivate_user(user_id: int, db: AsyncSession = Depends(get_session), admin=Depends(require_roles(Role.admin))):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    return {"ok": True}

@router.post("/orders/{order_id}/force-status")
async def force_order_status(order_id: int, status: str, db: AsyncSession = Depends(get_session), admin=Depends(require_roles(Role.admin))):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    try:
        order.status = OrderStatus(status)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid status")
    await db.commit(); return {"ok": True}

@router.post("/products/{product_id}/force-visibility")
async def force_visibility(product_id: int, active: bool, db: AsyncSession = Depends(get_session), admin=Depends(require_roles(Role.admin))):
    p = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if not p: raise HTTPException(status_code=404, detail="Product not found")
    p.is_active = active; await db.commit(); return {"ok": True}
