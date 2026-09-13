"""Category management endpoints (public browse + admin management)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Category
from app.schemas import CategoryRead
from app.permissions import AdminUser, get_current_user

router = APIRouter()


@router.get("/", response_model=list[CategoryRead])
async def list_categories(
    parent_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List categories (nested)."""
    stmt = select(Category)
    if parent_id is not None:
        stmt = stmt.where(Category.parent_id == parent_id)
    else:
        stmt = stmt.where(Category.parent_id.is_(None))
    result = await db.execute(stmt.order_by(Category.name))
    return [
        CategoryRead(
            id=c.id, name=c.name, slug=c.slug, parent_id=c.parent_id
        )
        for c in result.scalars().all()
    ]


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return CategoryRead(
        id=cat.id, name=cat.name, slug=cat.slug, parent_id=cat.parent_id
    )


# ── Admin: manage categories ───────────────
@router.post("/admin", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category_admin(
    name: str = Query(..., min_length=1, max_length=100),
    parent_id: Optional[int] = Query(None),
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Admin: create a category."""
    from app.schemas import CategoryRead as CR
    from app.models import Category as Cat
    slug = name.lower().replace(" ", "-")
    cat = Cat(name=name, slug=slug, parent_id=parent_id)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CR(id=cat.id, name=cat.name, slug=cat.slug, parent_id=cat.parent_id)


@router.delete("/admin/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category_admin(
    category_id: int,
    current_user=AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Admin: delete a category."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await db.delete(cat)
    await db.commit()

