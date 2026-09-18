"""Return request endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    Order, ReturnRequest, ReturnStatus, Store, User,
)
from app.schemas import ReturnCreate, ReturnRead, ReturnProcess
from app.permissions import CustomerUser, SellerUser, AdminUser, get_current_user

router = APIRouter()


@router.get("/", response_model=list[ReturnRead])
async def list_returns(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List returns for the current user (customer) or store (seller) or all (admin)."""
    if current_user.role.value == "customer":
        stmt = select(ReturnRequest).where(ReturnRequest.order.has(Order.user_id == current_user.id))
    elif current_user.role.value == "seller":
        stmt = select(ReturnRequest).where(
            ReturnRequest.order.has(Order.store.has(Store.seller_id == current_user.id))
        )
    else:
        stmt = select(ReturnRequest)
    result = await db.execute(stmt)
    return [_return_read(r) for r in result.scalars().all()]


@router.post("/", response_model=ReturnRead, status_code=status.HTTP_201_CREATED)
async def create_return(
    payload: ReturnCreate,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Customer: request a return."""
    result = await db.execute(select(Order).where(Order.id == payload.order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if order.status in (OrderStatus.CANCELLED, OrderStatus.RETURNED, OrderStatus.REFUNDED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be returned.",
        )

    if payload.order_item_id:
        result = await db.execute(
            select(ReturnRequest).where(
                ReturnRequest.order_item_id == payload.order_item_id,
                ReturnRequest.order_id == payload.order_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Return already requested for this item.",
            )

    number = f"RET-{datetime.now(timezone.utc).strftime('%Y')}-{uuid.uuid4().hex[:8].upper()}"
    ret = ReturnRequest(
        return_number=number,
        order_id=payload.order_id,
        order_item_id=payload.order_item_id,
        reason=payload.reason,
        description=payload.description,
        status=ReturnStatus.PENDING,
    )
    db.add(ret)
    await db.commit()
    await db.refresh(ret)
    return _return_read(ret)


@router.get("/{return_id}", response_model=ReturnRead)
async def get_return(
    return_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReturnRequest).where(ReturnRequest.id == return_id)
    )
    ret = result.scalar_one_or_none()
    if not ret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _return_read(ret)


@router.patch("/{return_id}/process", response_model=ReturnRead)
async def process_return(
    return_id: int,
    payload: ReturnProcess,
    current_user=SellerUser,
    db: AsyncSession = Depends(get_db),
):
    """Seller/Admin: process a return."""
    result = await db.execute(
        select(ReturnRequest).where(ReturnRequest.id == return_id)
    )
    ret = result.scalar_one_or_none()
    if not ret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    ret.status = payload.status
    ret.admin_note = payload.admin_note
    if payload.status in (ReturnStatus.REFUNDED, ReturnStatus.REJECTED, ReturnStatus.CANCELLED):
        ret.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ret)
    return _return_read(ret)


def _return_read(r) -> ReturnRead:
    return ReturnRead(
        id=r.id,
        return_number=r.return_number,
        order_id=r.order_id,
        order_item_id=r.order_item_id,
        reason=r.reason,
        description=r.description,
        status=r.status,
        admin_note=r.admin_note,
        requested_at=r.requested_at,
        resolved_at=r.resolved_at,
    )

