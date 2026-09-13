"""Shopping cart endpoints (customer)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Cart, CartItem, Product
from app.schemas import CartItemAdd, CartItemRead, CartRead, CartItemUpdate
from app.permissions import CustomerUser, get_current_user
from app.security import get_current_user as _c

router = APIRouter()


@router.get("/", response_model=CartRead)
async def get_cart(
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Get the customer's cart (creates one if needed)."""
    cart = await _get_or_create_cart(current_user, db)
    return await _cart_read(cart, db)


@router.post("/items", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    payload: CartItemAdd,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Add a product to the cart."""
    cart = await _get_or_create_cart(current_user, db)
    result = await db.execute(select(Product).where(Product.id == payload.product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not product.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product is unavailable")
    if product.stock_quantity < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock",
        )

    # Check if already in cart
    for item in cart.items:
        if item.product_id == payload.product_id:
            item.quantity = min(item.quantity + payload.quantity, 999)
            await db.commit()
            await db.refresh(item)
            return item

    item = CartItem(
        cart_id=cart.id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        price_at_add=float(product.price),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/items/{item_id}", response_model=CartItemRead)
async def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Update item quantity in cart."""
    cart = await _get_or_create_cart(current_user, db)
    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    item.quantity = payload.quantity
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cart_item(
    item_id: int,
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Remove item from cart."""
    cart = await _get_or_create_cart(current_user, db)
    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    await db.delete(item)
    await db.commit()


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user=CustomerUser,
    db: AsyncSession = Depends(get_db),
):
    """Clear all items from cart."""
    cart = await _get_or_create_cart(current_user, db)
    cart.items.clear()
    await db.commit()


async def _get_or_create_cart(user, db: AsyncSession) -> Cart:
    if user.cart:
        return user.cart
    cart = Cart(user_id=user.id)
    db.add(cart)
    await db.commit()
    await db.refresh(cart)
    return cart


async def _cart_read(cart: Cart, db: AsyncSession) -> CartRead:
    result = await db.execute(
        select(Product).where(Product.id.in_(ci.product_id for ci in cart.items))
    )
    products = {p.id: p for p in result.scalars().all()}
    items = []
    subtotal = 0.0
    total_items = 0
    for ci in cart.items:
        p = products.get(ci.product_id)
        items.append(
            CartItemRead(
                id=ci.id,
                cart_id=ci.cart_id,
                product_id=ci.product_id,
                quantity=ci.quantity,
                price_at_add=ci.price_at_add,
                product=_product_read(p) if p else None,
            )
        )
        subtotal += ci.price_at_add * ci.quantity
        total_items += ci.quantity
    return CartRead(
        id=cart.id,
        user_id=cart.user_id,
        items=items,
        total_items=total_items,
        subtotal=subtotal,
    )


def _product_read(p):
    if not p:
        return None
    return {
        "id": p.id, "name": p.name, "price": float(p.price),
        "images": [{"image_url": i.image_url} for i in p.images],
        "stock_quantity": p.stock_quantity, "slug": p.slug,
    }

