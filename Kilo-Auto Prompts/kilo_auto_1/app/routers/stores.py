"""Store management endpoints (seller + admin)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Store, User, UserRole
from app.schemas import (
    StoreRead,
    StoreCreate,
    StoreUpdate,
    UserMiniRead,
)
from app.permissions import SellerUser

router = APIRouter()


@router.get("/", response_model=list[StoreRead])
async def list_stores(
    is_active: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Browse all active stores."""
    stmt = select(Store).where(Store.is_active == is_active)
    result = await db.execute(stmt)
    stores = result.scalars().all()
    return [_store_read(s, db) for s in stores]


@router.get("/{store_id}", response_model=StoreRead)
async def get_store(
    store_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Store detail."""
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return await _store_read(store, db)


@router.get("/slug/{slug}", response_model=StoreRead)
async def get_store_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Store).where(Store.slug == slug))
    store = result.scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return await _store_read(store, db)


# ── Seller endpoints ───────────────────────────────
@router.get("/my-store", response_model=StoreRead)
async def my_store(
    current_user: User = SellerUser,
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated seller's own store."""
    if current_user.store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have a store yet.",
        )
    return await _store_read(current_user.store, db)


@router.post("/my-store", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
async def create_store(
    payload: StoreCreate,
    current_user: User = SellerUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a store for the authenticated seller."""
    if current_user.store is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a store.",
        )
    store = Store(
        seller_id=current_user.id,
        name=payload.name,
        slug=_slug(payload.name),
        description=payload.description,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
    )
    db.add(store)
    await db.commit()
    await db.refresh(store)
    return await _store_read(store, db)


@router.patch("/my-store", response_model=StoreRead)
async def update_store(
    payload: StoreUpdate,
    current_user: User = SellerUser,
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated seller's store."""
    if current_user.store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have a store yet.",
        )
    store = current_user.store
    for field in StoreUpdate.model_fields:
        if field == "logo_image" and payload.logo_image is not None:
            setattr(store, field, payload.logo_image)
        elif field != "logo_image" and getattr(payload, field) is not None:
            setattr(store, field, getattr(payload, field))
    store.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(store)
    return await _store_read(store, db)


@router.get("/my-store/products", response_model=list[StoreRead])
async def seller_products_list_placeholder(
    current_user: User = SellerUser,
):
    """Placeholder - use /products with seller filter."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Use /products endpoint with seller_id filter.",
    )


async def _store_read(store: Store, db: AsyncSession) -> StoreRead:
    result = await db.execute(select(User).where(User.id == store.seller_id))
    seller = result.scalar_one_or_none()
    return StoreRead(
        id=store.id,
        seller_id=store.seller_id,
        name=store.name,
        slug=store.slug,
        description=store.description,
        logo_image=store.logo_image,
        address_line1=store.address_line1,
        address_line2=store.address_line2,
        city=store.city,
        state=store.state,
        postal_code=store.postal_code,
        country=store.country,
        is_active=store.is_active,
        created_at=store.created_at,
        updated_at=store.updated_at,
        seller=UserMiniRead(
            id=seller.id, email=seller.email, full_name=seller.full_name, role=seller.role
        ) if seller else None,
    )


def _slug(name: str) -> str:
    import re
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", name).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "store"

