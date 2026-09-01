from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from app.db.session import get_session
from app.deps.auth import get_current_user
from app.models.cart import Cart, CartItem

router = APIRouter(prefix="/cart", tags=["cart"])

@router.get("", responses={401: {"description": "Missing auth"}})
async def get_cart(db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    cart = (await db.execute(select(Cart).where(Cart.user_id == user.id))).scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user.id); db.add(cart); await db.commit(); await db.refresh(cart)
    items = (await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))).scalars().all()
    return {"id": cart.id, "items": [{"id": i.id, "product_id": i.product_id, "quantity": i.quantity} for i in items]}

@router.post("/items", responses={401: {"description": "Missing auth"}, 422: {"description": "Invalid"}})
async def add_item(product_id: int, quantity: int = 1, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    if quantity <= 0: raise HTTPException(status_code=422, detail="Quantity must be > 0")
    cart = (await db.execute(select(Cart).where(Cart.user_id == user.id))).scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user.id); db.add(cart); await db.flush()
    existing = (await db.execute(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id))).scalar_one_or_none()
    if existing:
        await db.execute(update(CartItem).where(CartItem.id == existing.id).values(quantity=existing.quantity + quantity))
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity))
    await db.commit()
    return {"ok": True}
