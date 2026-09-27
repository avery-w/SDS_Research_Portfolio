from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.database import get_db
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.store import Store
from app.utils.security import require_role
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin_dep = require_role(UserRole.ADMIN)
analytics = AnalyticsService()


@router.get("/analytics/sales")
async def sales_analytics(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(admin_dep),
    db: AsyncSession = Depends(get_db),
):
    summary = await analytics.get_sales_summary(db, start_date, end_date)
    top_products = await analytics.get_top_products(db)
    user_stats = await analytics.get_user_stats(db)
    return {"summary": summary, "top_products": top_products, "user_stats": user_stats}


@router.get("/users")
async def list_all_users(
    page: int = 1,
    per_page: int = 50,
    current_user: User = Depends(admin_dep),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    result = await db.execute(select(User).offset(offset).limit(per_page))
    users = result.scalars().all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active} for u in users]


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(admin_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Cannot deactivate admin")
    user.is_active = False
    await db.flush()
    return {"message": f"User {user_id} deactivated"}


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(admin_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await db.flush()
    return {"message": f"User {user_id} activated"}


@router.patch("/orders/{order_id}/override")
async def admin_override_order(
    order_id: int,
    new_status: OrderStatus,
    current_user: User = Depends(admin_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = new_status
    await db.flush()
    return {"message": "Order status overridden", "order_id": order.id, "status": new_status}


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_product(
    product_id: int,
    current_user: User = Depends(admin_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    await db.flush()


@router.delete("/stores/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_store(
    store_id: int,
    current_user: User = Depends(admin_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    store.is_active = False
    await db.flush()
