"""User management endpoints (admin)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserRole
from app.schemas import ErrorResponse, UserRead, UserUpdate
from app.permissions import AdminUser, get_current_user
from app.security import get_current_user as _g

router = APIRouter()


@router.get("/", response_model=list[UserRead])
async def list_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Admin: list all users with optional filters."""
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.order_by(desc(User.created_at))
    total = await db.execute(select(count_(stmt)).limit(1))
    total = total.scalar() or 0
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    return [_user_read(u) for u in result.scalars().all()]


def count_(stmt):
    from sqlalchemy import func
    return select(func.count()).select_from(stmt.subquery())


def _user_read(u: User) -> UserRead:
    return UserRead(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        is_active=u.is_active,
        is_email_verified=u.is_email_verified,
        phone=u.phone,
        address_line1=u.address_line1,
        address_line2=u.address_line2,
        city=u.city,
        state=u.state,
        postal_code=u.postal_code,
        country=u.country,
        created_at=u.created_at,
        last_login_at=u.last_login_at,
    )


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Admin: get user details."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_read(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Admin: update user details. Can deactivate/reactivate."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for field in UserUpdate.model_fields:
        if getattr(payload, field) is not None:
            setattr(user, field, getattr(payload, field))
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return _user_read(user)


@router.post("/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: int,
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Admin: deactivate an account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    await db.commit()

