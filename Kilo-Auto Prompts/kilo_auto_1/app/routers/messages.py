"""Messaging endpoints: customer↔seller direct messaging."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    Message, Order, Product, User, UserRole,
)
from app.schemas import (
    ConversationRead,
    MessageRead,
    MessageSend,
)
from app.permissions import CustomerUser, SellerUser

router = APIRouter()


@router.post("/", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(
    payload: MessageSend,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Send a message (customer → seller) or (any → admin)."""
    recipient_result = await db.execute(
        select(User).where(User.id == payload.recipient_id)
    )
    recipient = recipient_result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found."
        )
    if recipient.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot message another customer.",
        )
    if recipient.role == UserRole.SELLER and current_user.role == UserRole.CUSTOMER:
        if recipient.store is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Seller has no store."
            )

    message = Message(
        order_id=payload.order_id,
        product_id=payload.product_id,
        sender_id=current_user.id,
        recipient_id=recipient.id,
        subject=payload.subject,
        body=payload.body,
        is_read=False,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return MessageRead(
        id=message.id,
        order_id=message.order_id,
        product_id=message.product_id,
        sender_id=message.sender_id,
        recipient_id=message.recipient_id,
        sender_name=current_user.full_name,
        subject=message.subject,
        body=message.body,
        is_read=False,
        sent_at=message.sent_at,
    )


@router.get("/", response_model=list[ConversationRead])
async def conversations(
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """List recent conversations for the current user."""
    stmt = (
        select(Message)
        .where(
            (Message.recipient_id == current_user.id) | (Message.sender_id == current_user.id),
        )
        .order_by(desc(Message.sent_at))
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    seen = set()
    convs = []
    for m in messages:
        peer_id = m.sender_id if m.recipient_id == current_user.id else m.recipient_id
        key = peer_id
        if key in seen:
            continue
        seen.add(key)
        peer_result = await db.execute(select(User).where(User.id == peer_id))
        peer = peer_result.scalar_one_or_none()
        convs.append(
            ConversationRead(
                id=m.id,
                order_id=m.order_id,
                product_id=m.product_id,
                sender_id=m.sender_id,
                recipient_id=m.recipient_id,
                sender_name=peer.full_name if peer else None,
                recipient_name=current_user.full_name,
                subject=m.subject,
                is_read=m.is_read,
                latest_body=m.body,
                latest_sent=m.sent_at,
            )
        )
    return convs


@router.get("/conversation", response_model=list[MessageRead])
async def conversation(
    with_user: int = Query(..., description="Recipient or sender user ID"),
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation thread."""
    stmt = (
        select(Message)
        .where(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == with_user))
            | ((Message.recipient_id == current_user.id) & (Message.sender_id == with_user)),
        )
        .order_by(Message.sent_at)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    # Mark as read
    for m in messages:
        if m.recipient_id == current_user.id and not m.is_read:
            m.is_read = True
    await db.commit()

    return [
        MessageRead(
            id=m.id,
            order_id=m.order_id,
            product_id=m.product_id,
            sender_id=m.sender_id,
            recipient_id=m.recipient_id,
            sender_name=m.sender.full_name if m.sender else None,
            subject=m.subject,
            body=m.body,
            is_read=m.is_read,
            sent_at=m.sent_at,
            read_at=m.read_at,
        )
        for m in messages
    ]

