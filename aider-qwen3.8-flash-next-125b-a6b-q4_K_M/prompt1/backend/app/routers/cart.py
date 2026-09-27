from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse, CartItemResponse
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/cart", tags=["cart"])


async def _get_or_create_cart(user_id: int, db: AsyncSession) -> Cart:
    result = await db.execute(select(Cart).where(Cart.user_id == user_id))
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.flush()
        await db.refresh(cart)
    return cart


@router.get("", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart = await _get_or_create_cart(current_user.id, db)
    return cart


@router.post("/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    data: CartItemAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == data.product_id, Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock_quantity < data.quantity:
        raise HTTPException(status_code=409, detail="Insufficient stock")

    cart = await _get_or_create_cart(current_user.id, db)

    existing = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == data.product_id)
    )
    existing_item = existing.scalar_one_or_none()
    if existing_item:
        existing_item.quantity += data.quantity
        await db.flush()
        await db.refresh(existing_item)
        return existing_item

    cart_item = CartItem(cart_id=cart.id, product_id=data.product_id, quantity=data.quantity)
    db.add(cart_item)
    await db.flush()
    await db.refresh(cart_item)
    return cart_item


@router.patch("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int,
    data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CartItem).where(CartItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if item.cart.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    item.quantity = data.quantity
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CartItem).where(CartItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if item.cart.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(item)
    await db.flush()
