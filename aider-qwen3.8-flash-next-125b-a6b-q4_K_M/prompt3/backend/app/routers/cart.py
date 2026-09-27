import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.schemas.cart import CartItemCreate, CartItemResponse, CartResponse

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartResponse)
async def get_cart(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Cart).where(Cart.user_id == user.id))
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()
    items_result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    items = items_result.scalars().all()
    item_responses = []
    for ci in items:
        prod_result = await db.execute(select(Product).where(Product.id == ci.product_id))
        prod = prod_result.scalar_one_or_none()
        item_responses.append(CartItemResponse(
            id=ci.id, product_id=ci.product_id, variant_id=ci.variant_id,
            quantity=ci.quantity, product_title=prod.title if prod else None,
            product_price=prod.price if prod else None, added_at=ci.added_at,
        ))
    return CartResponse.model_validate({**cart.__dict__, "items": item_responses})


@router.post("/items", status_code=201)
async def add_item(data: CartItemCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    cart_result = await db.execute(select(Cart).where(Cart.user_id == user.id))
    cart = cart_result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()
    item = CartItem(cart_id=cart.id, product_id=data.product_id, variant_id=data.variant_id, quantity=data.quantity)
    db.add(item)
    await db.flush()
    return {"id": str(item.id)}


@router.put("/items/{item_id}")
async def update_item(item_id: uuid.UUID, quantity: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(CartItem).where(CartItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.quantity = quantity
    await db.flush()
    return {"id": str(item.id), "quantity": item.quantity}


@router.delete("/items/{item_id}", status_code=204)
async def remove_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(CartItem).where(CartItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.flush()


@router.delete("", status_code=204)
async def clear_cart(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Cart).where(Cart.user_id == user.id))
    cart = result.scalar_one_or_none()
    if cart:
        items_result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
        for item in items_result.scalars().all():
            await db.delete(item)
        await db.delete(cart)
        await db.flush()
