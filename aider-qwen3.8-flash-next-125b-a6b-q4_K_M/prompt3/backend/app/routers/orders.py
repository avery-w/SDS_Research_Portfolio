import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import get_current_user, get_current_seller, get_current_admin
from app.models.user import User, UserRole
from app.models.order import Order, OrderItem, OrderStatus
from app.models.store import Store
from app.schemas.order import OrderResponse, OrderItemResponse
from app.utils.pagination import PaginatedResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == UserRole.admin:
        query = select(Order)
    elif user.role == UserRole.seller:
        store_result = await db.execute(select(Store).where(Store.seller_id == user.id))
        store = store_result.scalar_one_or_none()
        if not store:
            raise HTTPException(status_code=400, detail="No store")
        query = select(Order).where(Order.store_id == store.id)
    else:
        query = select(Order).where(Order.customer_id == user.id)

    count_q = select(Order.id)
    if user.role != UserRole.admin:
        if user.role == UserRole.seller:
            store_result = await db.execute(select(Store).where(Store.seller_id == user.id))
            store = store_result.scalar_one_or_none()
            count_q = count_q.where(Order.store_id == store.id)
        else:
            count_q = count_q.where(Order.customer_id == user.id)
    total = len((await db.execute(count_q)).scalars().all())

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    orders = result.scalars().all()

    items = []
    for o in orders:
        oi_result = await db.execute(select(OrderItem).where(OrderItem.order_id == o.id))
        oi_list = oi_result.scalars().all()
        items.append(OrderResponse.model_validate({**o.__dict__, "items": [OrderItemResponse.model_validate(oi.__dict__) for oi in oi_list]}))

    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.role == UserRole.customer and order.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if user.role == UserRole.seller:
        store_result = await db.execute(select(Store).where(Store.seller_id == user.id))
        store = store_result.scalar_one_or_none()
        if not store or order.store_id != store.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    oi_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    oi_list = oi_result.scalars().all()
    return OrderResponse.model_validate({**order.__dict__, "items": [OrderItemResponse.model_validate(oi.__dict__) for oi in oi_list]})


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_status(order_id: uuid.UUID, status: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.role == UserRole.seller:
        store_result = await db.execute(select(Store).where(Store.seller_id == user.id))
        store = store_result.scalar_one_or_none()
        if not store or order.store_id != store.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    order.status = OrderStatus(status)
    await db.flush()
    oi_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    oi_list = oi_result.scalars().all()
    return OrderResponse.model_validate({**order.__dict__, "items": [OrderItemResponse.model_validate(oi.__dict__) for oi in oi_list]})


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(order_id: uuid.UUID, reason: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.role == UserRole.customer and order.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    order.status = OrderStatus.cancelled
    order.cancellation_reason = reason
    await db.flush()
    oi_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    oi_list = oi_result.scalars().all()
    return OrderResponse.model_validate({**order.__dict__, "items": [OrderItemResponse.model_validate(oi.__dict__) for oi in oi_list]})


@router.post("/{order_id}/return", response_model=OrderResponse)
async def request_return(order_id: uuid.UUID, reason: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.role == UserRole.customer and order.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    order.status = OrderStatus.return_requested
    order.return_reason = reason
    await db.flush()
    oi_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    oi_list = oi_result.scalars().all()
    return OrderResponse.model_validate({**order.__dict__, "items": [OrderItemResponse.model_validate(oi.__dict__) for oi in oi_list]})
