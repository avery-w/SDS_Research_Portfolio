"""Seller-specific endpoints: dashboard, product management, order fulfillment, analytics."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    Order, OrderStatus, Product, ProductImage, Store, User, UserRole,
)
from app.schemas import (
    ProductImageRead,
    ProductRead,
    ProductUpdate,
    SellerAnalytics,
)
from app.permissions import SellerUser

router = APIRouter()


# ── Dashboard summary ────────────────────────
@router.get("/dashboard", response_model=SellerAnalytics)
async def seller_dashboard(
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    if current_user.store is None:
        return SellerAnalytics(
            total_orders=0, total_revenue=0.0, pending_orders=0,
            shipped_orders=0, cancelled_orders=0,
            revenue_by_day=[], top_products=[],
        )
    store = current_user.store
    total_orders = await db.execute(
        select(func.count()).where(Order.store_id == store.id)
    )
    total_orders = total_orders.scalar() or 0

    total_rev = await db.execute(
        select(func.sum(Order.grand_total)).where(Order.store_id == store.id)
    )
    total_rev = float(total_rev.scalar() or 0)

    pending = await db.execute(
        select(func.count()).where(
            Order.store_id == store.id, Order.status == OrderStatus.PENDING
        )
    )
    pending = pending.scalar() or 0
    shipped = await db.execute(
        select(func.count()).where(
            Order.store_id == store.id, Order.status == OrderStatus.SHIPPED
        )
    )
    shipped = shipped.scalar() or 0
    cancelled = await db.execute(
        select(func.count()).where(
            Order.store_id == store.id, Order.status == OrderStatus.CANCELLED
        )
    )
    cancelled = cancelled.scalar() or 0

    return SellerAnalytics(
        total_orders=total_orders,
        total_revenue=total_rev,
        pending_orders=pending,
        shipped_orders=shipped,
        cancelled_orders=cancelled,
        revenue_by_day=[],
        top_products=[],
    )


# ── Products (seller) ────────────────────────
@router.get("/products", response_model=list[ProductRead])
async def seller_products(
    is_active: Optional[bool] = Query(None),
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    if current_user.store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No store yet."
        )
    stmt = select(Product).where(Product.store_id == current_user.store.id).options(
        selectinload(Product.images), selectinload(Product.category)
    )
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    result = await db.execute(stmt)
    return [_product_full(p) for p in result.scalars().all()]


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    if current_user.store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No store yet."
        )
    product = Product(
        store_id=current_user.store.id,
        category_id=payload.category_id,
        name=payload.name,
        slug=payload.sku or payload.name.lower().replace(" ", "-"),
        description=payload.description,
        price=payload.price,
        cost_price=payload.cost_price,
        sku=payload.sku,
        stock_quantity=payload.stock_quantity,
        is_active=payload.is_active,
        is_featured=payload.is_featured,
        weight=payload.weight,
        length=payload.length,
        width=payload.width,
        height=payload.height,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return _product_full(product)


@router.get("/products/{product_id}", response_model=ProductRead)
async def seller_product_detail(
    product_id: int,
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.store.has(Store.seller_id == current_user.id))
        .options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _product_full(product)


@router.patch("/products/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.store.has(Store.seller_id == current_user.id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    for field in ProductUpdate.model_fields:
        if getattr(payload, field) is not None:
            setattr(product, field, getattr(payload, field))
    product.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(product)
    return _product_full(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.store.has(Store.seller_id == current_user.id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await db.delete(product)
    await db.commit()


# ── Product images ────────────────────────────
@router.post("/products/{product_id}/images", response_model=list[ProductImageRead])
async def upload_product_images(
    product_id: int,
    urls: list[str],
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    """Upload product images (URLs for simplicity)."""
    result = await db.execute(
        select(Product)
        .where(
            Product.id == product_id,
            Product.store.has(Store.seller_id == current_user.id),
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    existing_images = await db.execute(
        select(ProductImage).where(ProductImage.product_id == product_id)
    )
    existing = existing_images.scalars().all()
    for img in existing:
        if img.is_primary:
            img.is_primary = False

    images = []
    for i, url in enumerate(urls[:10]):
        img = ProductImage(
            product_id=product_id,
            image_url=url,
            is_primary=(i == 0),
            position=i,
        )
        db.add(img)
        images.append(img)
    await db.commit()
    return [
        ProductImageRead(
            id=img.id,
            image_url=img.image_url,
            alt_text=img.alt_text,
            is_primary=img.is_primary,
            position=img.position,
        )
        for img in images
    ]


# ── Orders (seller) ───────────────────────────
@router.get("/orders", response_model=list[dict])
async def seller_orders(
    status_filter: Optional[str] = Query(None),
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    if current_user.store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No store yet."
        )
    stmt = select(Order).where(Order.store_id == current_user.store.id)
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    stmt = stmt.order_by(desc(Order.created_at))
    result = await db.execute(stmt)
    orders = []
    for o in result.scalars().all():
        orders.append({
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status.value,
            "total": float(o.grand_total),
            "customer_name": o.user.full_name,
            "created_at": o.created_at,
            "items_count": len(o.items),
        })
    return orders


@router.patch("/orders/{order_id}/status", response_model=dict)
async def seller_update_order_status(
    order_id: int,
    status: str,
    tracking_number: Optional[str] = Query(None),
    note: Optional[str] = Query(None),
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    if current_user.store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No store yet."
        )
    result = await db.execute(
        select(Order)
        .where(
            Order.id == order_id,
            Order.store.has(Store.seller_id == current_user.id),
        )
    )
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
    allowed_transitions = {
        OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
        OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
        OrderStatus.PROCESSING: {OrderStatus.SHIPPED},
        OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
        OrderStatus.DELIVERED: {OrderStatus.RETURNED, OrderStatus.REFUNDED},
    }
    if new_status not in allowed_transitions.get(order.status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {order.status.value} to {new_status.value}",
        )

    order.status = new_status
    order.updated_at = datetime.now(timezone.utc)
    if tracking_number:
        order.tracking_number = tracking_number
    order.status_history.append(
        type("OH", (), {
            "status": new_status.value,
            "note": note or f"Status changed to {new_status.value}",
            "created_by_id": current_user.id,
        })()
    )
    await db.commit()
    return {
        "order_id": order.id,
        "status": order.status.value,
        "tracking_number": order.tracking_number,
    }


def _product_full(p):
    from app.schemas import ProductRead as PR, CategoryRead as CR, ProductImageRead as PIR
    images = [
        PIR(
            id=img.id, image_url=img.image_url, alt_text=img.alt_text,
            is_primary=img.is_primary, position=img.position,
        )
        for img in p.images
    ]
    category = None
    if p.category:
        category = CR(
            id=p.category.id, name=p.category.name, slug=p.category.slug,
            parent_id=p.category.parent_id,
        )
    return PR(
        id=p.id, store_id=p.store_id, category_id=p.category_id,
        category=category, name=p.name, slug=p.slug, description=p.description,
        price=float(p.price), cost_price=float(p.cost_price) if p.cost_price else None,
        sku=p.sku, stock_quantity=p.stock_quantity, is_active=p.is_active,
        is_featured=p.is_featured,
        weight=float(p.weight) if p.weight else None,
        length=float(p.length) if p.length else None,
        width=float(p.width) if p.width else None,
        height=float(p.height) if p.height else None,
        created_at=p.created_at, updated_at=p.updated_at,
        images=images,
        average_rating=None, review_count=0,
    )

