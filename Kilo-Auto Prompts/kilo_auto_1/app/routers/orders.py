"""Order endpoints: checkout, order history, status management."""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    Cart, CartItem, Order, OrderItem, OrderStatus, OrderStatusHistory,
    PaymentStatus, Product, Store, User,
)
from app.schemas import (
    CancelOrder,
    OrderItemRead,
    OrderPage,
    OrderRead,
    OrderStatusUpdate,
    CheckoutRequest,
)
from app.permissions import CustomerUser
from app.routers.cart import _get_or_create_cart

router = APIRouter()

TAX_RATE = 0.08  # simplified flat tax


@router.post("/checkout", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: CheckoutRequest,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Checkout the cart: create order with shipping rates (UPS), tax, total."""
    cart = await _get_or_create_cart(current_user, db)
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")
    product_ids = [ci.product_id for ci in cart.items]
    product_result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    products = {p.id: p for p in product_result.scalars().all()}

    weight = sum(
        (products[ci.product_id].weight or 1.0) * ci.quantity
        for ci in cart.items
        if ci.product_id in products
    )
    if weight <= 0:
        weight = 1.0

    dest_zip = payload.shipping_postal_code[:5]
    rates = calculate_ups_rates(
        weight, dest_zip, is_residential=False,
    )

    # Find selected service rate
    shipping_rate = 0.0
    service_name = None
    for r in rates.rates:
        if r.service == payload.shipping_service:
            shipping_rate = r.rate
            service_name = r.service_name
            break
    else:
        if rates.rates:
            shipping_rate = rates.rates[0].rate
            service_name = rates.rates[0].service_name

    subtotal = sum(ci.price_at_add * ci.quantity for ci in cart.items)
    tax = round(subtotal * TAX_RATE, 2)
    grand_total = round(subtotal + shipping_rate + tax, 2)

    shipping_addr = _format_address(
        payload.shipping_address_line1,
        payload.shipping_address_line2,
        payload.shipping_city,
        payload.shipping_state,
        payload.shipping_postal_code,
        payload.shipping_country,
    )
    billing_addr = shipping_addr
    if not payload.billing_same_as_shipping:
        billing_addr = _format_address(
            payload.billing_address_line1,
            payload.billing_address_line2,
            payload.billing_city,
            payload.billing_state,
            payload.billing_postal_code,
            payload.billing_country,
        )

    # Get store from first cart item's product
    first_product = None
    for ci in cart.items:
        first_product = products.get(ci.product_id)
        if first_product:
            break

    if not first_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    store_result = await db.execute(
        select(Store).where(Store.id == first_product.store_id)
    )
    store = store_result.scalar_one_or_none()

    order_number = f"ORD-{_uuid.uuid4().hex[:12].upper()}"
    order = Order(
        order_number=order_number,
        user_id=current_user.id,
        store_id=store.id if store else None,
        status=OrderStatus.PENDING,
        total_amount=round(subtotal, 2),
        shipping_cost=round(shipping_rate, 2),
        tax_amount=round(tax, 2),
        grand_total=round(grand_total, 2),
        shipping_address=shipping_addr,
        billing_address=billing_addr,
        shipping_method=service_name,
        payment_status=PaymentStatus.PENDING,
        payment_method="cart_checkout",
        note=payload.note,
    )
    db.add(order)
    await db.flush()

    for ci in cart.items:
        p = products.get(ci.product_id)
        if not p:
            continue
        order_item = OrderItem(
            order_id=order.id,
            product_id=p.id,
            quantity=ci.quantity,
            unit_price=float(p.price),
            total_price=float(p.price) * ci.quantity,
        )
        db.add(order_item)

    # Decrease stock
    for ci in cart.items:
        p = products.get(ci.product_id)
        if p:
            p.stock_quantity = max(0, p.stock_quantity - ci.quantity)

    # Status history
    order.status_history.append(
        OrderStatusHistory(status="pending", note="Order created via checkout")
    )

    # Clear cart
    cart.items.clear()

    await db.commit()
    await db.refresh(order)
    return await _order_read(order, db)


def count_(stmt):
    from sqlalchemy import func
    return select(func.count()).select_from(stmt.subquery())


@router.get("/", response_model=OrderPage)
async def list_orders(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Customer: order history."""
    stmt = select(Order).where(Order.user_id == current_user.id)
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    stmt = stmt.order_by(desc(Order.created_at))
    total = await db.execute(count_(stmt))
    total = total.scalar() or 0
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    items = []
    for o in result.scalars().all():
        items.append(await _order_read(o, db))
    return OrderPage(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Customer: order detail. Returns 403 if not owner."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
            selectinload(Order.user),
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return await _order_read(order, db)


@router.post("/{order_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: int,
    payload: CancelOrder,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Customer: cancel an order (only if pending/confirmed)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order in {order.status.value} status.",
        )
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.now(timezone.utc)
    order.status_history.append(
        OrderStatusHistory(status="cancelled", note=payload.reason, created_by_id=current_user.id)
    )
    await db.commit()


@router.patch("/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Customer: update status note (limited). For status changes use seller/admin endpoints."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if payload.tracking_number:
        order.tracking_number = payload.tracking_number
    order.status_history.append(
        OrderStatusHistory(
            status=order.status.value, note=payload.note, created_by_id=current_user.id
        )
    )
    order.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(order)
    return await _order_read(order, db)


def _format_address(line1, line2, city, state, postal, country):
    parts = [line1]
    if line2:
        parts.append(line2)
    parts.append(f"{city}, {state} {postal}")
    if country:
        parts.append(country)
    return " | ".join(parts)


async def _order_read(order, db) -> OrderRead:
    items = []
    for oi in order.items:
        items.append(
            OrderItemRead(
                id=oi.id,
                order_id=oi.order_id,
                product_id=oi.product_id,
                product_name=oi.product.name if oi.product else None,
                quantity=oi.quantity,
                unit_price=float(oi.unit_price),
                total_price=float(oi.total_price),
            )
        )
    status_history = [
        OrderStatusHistoryRead(
            id=h.id,
            order_id=h.order_id,
            status=h.status,
            note=h.note,
            created_at=h.created_at,
            created_by_id=h.created_by_id,
        )
        for h in order.status_history
    ]
    return OrderRead(
        id=order.id,
        order_number=order.order_number,
        user_id=order.user_id,
        store_id=order.store_id,
        store_name=order.store.name if order.store else None,
        status=order.status,
        total_amount=float(order.total_amount),
        shipping_cost=float(order.shipping_cost),
        tax_amount=float(order.tax_amount),
        grand_total=float(order.grand_total),
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        shipping_method=order.shipping_method,
        tracking_number=order.tracking_number,
        payment_status=order.payment_status,
        payment_method=order.payment_method,
        note=order.note,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
        status_history=status_history,
    )

