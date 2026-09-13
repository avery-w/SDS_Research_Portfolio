"""Admin endpoints: user/store/product/order management, analytics, settings."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    AuditLog, Order, OrderStatus, PlatformSetting, Product, Store, User, UserRole,
)
from app.schemas import (
    AdminAnalytics,
    AnalyticsOverview,
    ProductRead,
    UserRead,
)
from app.permissions import AdminUser, get_current_user
from app.security import get_current_user as _a

router = APIRouter()


# ── Dashboard ──────────────────────────
@router.get("/dashboard", response_model=AdminAnalytics)
async def admin_dashboard(
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.execute(select(func.count()).select_from(User))
    total_users = total_users.scalar() or 0
    total_sellers = await db.execute(
        select(func.count()).where(User.role == UserRole.SELLER)
    )
    total_sellers = total_sellers.scalar() or 0
    total_products = await db.execute(select(func.count()).select_from(Product))
    total_products = total_products.scalar() or 0
    total_orders = await db.execute(select(func.count()).select_from(Order))
    total_orders = total_orders.scalar() or 0
    total_revenue = await db.execute(select(func.sum(Order.grand_total)))
    total_revenue = float(total_revenue.scalar() or 0)
    gross_profit = await db.execute(
        select(func.sum(Product.cost_price * Product.stock_quantity))
    )
    gross_profit = float(gross_profit.scalar() or 0)

    # Orders by status
    status_counts: dict[str, int] = {}
    for st in OrderStatus:
        count = await db.execute(
            select(func.count()).where(Order.status == st)
        )
        status_counts[st.value] = count.scalar() or 0

    # Revenue by last 7 days (stub)
    revenue_by_day = []
    for i in range(7):
        from datetime import timedelta
        day = datetime.now(timezone.utc) - timedelta(days=6 - i)
        revenue_by_day.append({
            "date": day.strftime("%Y-%m-%d"),
            "revenue": 0.0,  # simplified - in production would aggregate
        })

    # Top products stub
    top_products = []

    return AdminAnalytics(
        total_users=total_users,
        total_sellers=total_sellers,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        gross_profit=gross_profit,
        orders_by_status=status_counts,
        revenue_by_day=revenue_by_day,
        top_products=top_products,
    )


@router.get("/overview", response_model=AnalyticsOverview)
async def admin_overview(
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.execute(select(func.count()).select_from(User))
    total_sellers = await db.execute(
        select(func.count()).where(User.role == UserRole.SELLER)
    )
    total_products = await db.execute(select(func.count()).select_from(Product))
    total_orders = await db.execute(select(func.count()).select_from(Order))
    total_revenue = await db.execute(select(func.sum(Order.grand_total)))
    total_revenue = float(total_revenue.scalar() or 0)

    return AnalyticsOverview(
        total_users=total_users,
        total_sellers=total_sellers,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_orders_today=0,
        total_revenue_today=0.0,
        top_products=[],
    )


# ── Users ──────────────────────────────
@router.get("/users", response_model=list[UserRead])
async def admin_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.order_by(desc(User.created_at))
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    return [_user_read(u) for u in result.scalars().all()]


def _user_read(u: User) -> UserRead:
    return UserRead(
        id=u.id, email=u.email, full_name=u.full_name, role=u.role,
        is_active=u.is_active, is_email_verified=u.is_email_verified,
        phone=u.phone, address_line1=u.address_line1,
        address_line2=u.address_line2, city=u.city, state=u.state,
        postal_code=u.postal_code, country=u.country,
        created_at=u.created_at, last_login_at=u.last_login_at,
    )


@router.patch("/users/{user_id}", response_model=UserRead)
async def admin_update_user(
    user_id: int,
    is_active: Optional[bool] = Query(None),
    role: Optional[str] = Query(None),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if is_active is not None:
        user.is_active = is_active
    if role:
        try:
            user.role = UserRole(role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}",
            )
    await db.commit()
    return _user_read(user)


# ── Stores ─────────────────────────────
@router.get("/stores", response_model=list[dict])
async def admin_stores(
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Store)
    if is_active is not None:
        stmt = stmt.where(Store.is_active == is_active)
    stmt = stmt.order_by(desc(Store.created_at))
    total = await db.execute(select(func.count()).select_from(Store))
    total = total.scalar() or 0
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    stores = []
    for s in result.scalars().all():
        stores.append({
            "id": s.id, "name": s.name, "slug": s.slug,
            "is_active": s.is_active, "seller_id": s.seller_id,
            "created_at": s.created_at,
        })
    return stores


# ── Products ────────────────────────────
@router.get("/products", response_model=list[ProductRead])
async def admin_products(
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Product).options(
        selectinload(Product.store), selectinload(Product.category)
    )
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    stmt = stmt.order_by(desc(Product.created_at))
    result = await db.execute(stmt)
    return [
        ProductRead(
            id=p.id, store_id=p.store_id, category_id=p.category_id,
            category=None, name=p.name, slug=p.slug, description=p.description,
            price=float(p.price), cost_price=float(p.cost_price) if p.cost_price else None,
            sku=p.sku, stock_quantity=p.stock_quantity, is_active=p.is_active,
            is_featured=p.is_featured,
            weight=float(p.weight) if p.weight else None,
            length=float(p.length) if p.length else None,
            width=float(p.width) if p.width else None,
            height=float(p.height) if p.height else None,
            created_at=p.created_at, updated_at=p.updated_at,
            images=[], average_rating=None, review_count=0,
        )
        for p in result.scalars().all()
    ]


@router.patch("/products/{product_id}", response_model=ProductRead)
async def admin_update_product(
    product_id: int,
    is_active: Optional[bool] = Query(None),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if is_active is not None:
        product.is_active = is_active
    product.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(product)
    return ProductRead(
        id=product.id, name=product.name, slug=product.slug,
        description=product.description, price=float(product.price),
        cost_price=float(product.cost_price) if product.cost_price else None,
        sku=product.sku, stock_quantity=product.stock_quantity,
        is_active=product.is_active, is_featured=product.is_featured,
        created_at=product.created_at, updated_at=product.updated_at,
        images=[],
    )


# ── Orders ──────────────────────────────
@router.get("/orders", response_model=list[dict])
async def admin_orders(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Order).order_by(desc(Order.created_at))
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    total = await db.execute(select(func.count()).select_from(Order))
    total = total.scalar() or 0
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    orders = []
    for o in result.scalars().all():
        orders.append({
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status.value,
            "grand_total": float(o.grand_total),
            "customer": o.user.full_name,
            "store": o.store.name if o.store else None,
            "created_at": o.created_at,
        })
    return orders


@router.patch("/orders/{order_id}/status", response_model=dict)
async def admin_override_order(
    order_id: int,
    status: str,
    note: Optional[str] = Query(None),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        new_status = OrderStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status}",
        )
    order.status = new_status
    order.updated_at = datetime.now(timezone.utc)
    order.status_history.append(
        type("OH", (), {
            "status": new_status.value,
            "note": note or "Admin override",
            "created_by_id": current_user.id,
        })()
    )
    await db.commit()
    return {
        "order_id": order.id,
        "status": order.status.value,
        "note": "Admin override",
    }


# ── Settings ────────────────────────────
@router.get("/settings")
async def get_settings(current_user=AdminUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PlatformSetting))
    settings = {
        s.key: {"value": s.value, "type": s.type, "description": s.description}
        for s in result.scalars().all()
    }
    return {"settings": settings}


@router.put("/settings")
async def update_settings(
    data: dict,
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    for key, value in data.items():
        existing = await db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        ps = existing.scalar_one_or_none()
        if ps:
            ps.value = str(value)
            ps.updated_at = datetime.now(timezone.utc)
        else:
            ps = PlatformSetting(key=key, value=str(value), type="text")
            db.add(ps)
    await db.commit()
    return {"message": "Settings updated"}


# ── Audit logs ──────────────────────────
@router.get("/audit-logs", response_model=list[dict])
async def audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at))
    total = await db.execute(select(func.count()).select_from(AuditLog))
    total = total.scalar() or 0
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    logs = []
    for a in result.scalars().all():
        logs.append({
            "id": a.id, "user_id": a.user_id, "action": a.action,
            "resource": a.resource, "resource_id": a.resource_id,
            "details": a.details, "ip_address": a.ip_address,
            "created_at": a.created_at,
        })
    return logs

