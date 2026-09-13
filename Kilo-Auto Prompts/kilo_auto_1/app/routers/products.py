"""Product catalog endpoints: public product listing, search, and detail."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Category, Product, ProductImage, Store, Review
from app.schemas import (
    ProductPage,
    ProductRead,
    CategoryRead,
    ReviewCreate,
    ReviewRead,
)
from app.security import get_current_user

router = APIRouter()


@router.get("/", response_model=ProductPage)
async def list_products(
    q: Optional[str] = Query(None, description="Search query"),
    category_id: Optional[int] = Query(None),
    store_id: Optional[int] = Query(None),
    is_active: bool = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Browse / search / filter products."""
    stmt = select(Product).options(
        selectinload(Product.images),
        selectinload(Product.category),
        selectinload(Product.store),
    )
    conditions = []
    if q:
        conditions.append(Product.name.ilike(f"%{q}%"))
    if category_id is not None:
        conditions.append(Product.category_id == category_id)
    if store_id is not None:
        conditions.append(Product.store_id == store_id)
    if is_active is not None:
        conditions.append(Product.is_active == is_active)
    if conditions:
        stmt = stmt.where(*conditions)

    total = await db.execute(count_for(stmt))
    total = total.scalar() or 0
    offset = (page - 1) * per_page
    stmt = stmt.order_by(desc(Product.created_at)).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    items = result.scalars().all()

    enriched = []
    for p in items:
        enriched.append(_enrich(p))

    return ProductPage(
        items=enriched,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


from sqlalchemy import func as _func

def count_for(stmt):
    return select(_func.count()).select_from(stmt.subquery())


def _enrich(product: Product) -> ProductRead:
    avg = None
    count = 0
    if product.reviews:
        vals = [r.rating for r in product.reviews if r.rating]
        if vals:
            avg = round(sum(vals) / len(vals), 1)
            count = len(vals)
    return ProductRead(
        id=product.id,
        store_id=product.store_id,
        category_id=product.category_id,
        category=CategoryRead(
            id=product.category.id,
            name=product.category.name,
            slug=product.category.slug,
            parent_id=product.category.parent_id,
        ) if product.category else None,
        name=product.name,
        slug=product.slug,
        description=product.description,
        price=float(product.price),
        cost_price=float(product.cost_price) if product.cost_price else None,
        sku=product.sku,
        stock_quantity=product.stock_quantity,
        is_active=product.is_active,
        is_featured=product.is_featured,
        weight=float(product.weight) if product.weight else None,
        length=float(product.length) if product.length else None,
        width=float(product.width) if product.width else None,
        height=float(product.height) if product.height else None,
        created_at=product.created_at,
        updated_at=product.updated_at,
        images=[
            ProductImageRead(
                id=img.id,
                image_url=img.image_url,
                alt_text=img.alt_text,
                is_primary=img.is_primary,
                position=img.position,
            )
            for img in product.images
        ],
        average_rating=avg,
        review_count=count,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Product detail page data."""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.store),
            selectinload(Product.reviews),
        )
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _enrich(product)


@router.get("/{product_id}/similar", response_model=list[ProductRead])
async def similar_products(
    product_id: int,
    limit: int = Query(4, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Products from the same store/category."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    stmt = select(Product).where(
        Product.id != product_id,
        Product.is_active == True,
    )
    if product.store_id:
        stmt = stmt.where(Product.store_id == product.store_id)
    elif product.category_id:
        stmt = stmt.where(Product.category_id == product.category_id)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return [_enrich(p) for p in result.scalars().all()]
