"""Review endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Product, Review, User
from app.schemas import ReviewCreate, ReviewRead
from app.permissions import CustomerUser

router = APIRouter()


@router.get("/", response_model=list[ReviewRead])
async def list_reviews(
    product_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List reviews, optionally filtered by product."""
    stmt = select(Review).options(
        selectinload(Review.product), selectinload(Review.user),
    ).order_by(desc(Review.created_at)).limit(limit)
    if product_id is not None:
        stmt = stmt.where(Review.product_id == product_id)
    result = await db.execute(stmt)
    return [
        ReviewRead(
            id=r.id,
            product_id=r.product_id,
            product_name=r.product.name if r.product else None,
            user_id=r.user_id,
            user_name=r.user.full_name if r.user else None,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in result.scalars().all()
    ]


@router.post("/", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewCreate,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Create or update a review for a product."""
    result = await db.execute(select(Product).where(Product.id == payload.product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    result = await db.execute(
        select(Review).where(
            Review.product_id == payload.product_id,
            Review.user_id == current_user.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.rating = payload.rating
        existing.comment = payload.comment
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        return ReviewRead(
            id=existing.id,
            product_id=existing.product_id,
            product_name=existing.product.name,
            user_id=existing.user_id,
            rating=existing.rating,
            comment=existing.comment,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )

    review = Review(
        product_id=payload.product_id,
        user_id=current_user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return ReviewRead(
        id=review.id,
        product_id=review.product_id,
        product_name=review.product.name,
        user_id=review.user_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )

