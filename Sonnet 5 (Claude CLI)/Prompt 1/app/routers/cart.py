from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_customer
from ..models import CartItem, Product, User
from ..schemas import CartAddRequest, CartItemOut

router = APIRouter(prefix="/api/cart", tags=["cart"])


@router.get("", response_model=list[CartItemOut])
def get_cart(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    items = db.query(CartItem).options(joinedload(CartItem.product)).filter(CartItem.user_id == user.id).all()
    return [
        CartItemOut(id=i.id, product_id=i.product_id, name=i.product.name, price_cents=i.product.price_cents, quantity=i.quantity, store_id=i.product.store_id)
        for i in items
    ]


@router.post("", response_model=CartItemOut, status_code=status.HTTP_201_CREATED)
def add_to_cart(payload: CartAddRequest, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == payload.product_id, Product.is_active.is_(True)).first()
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    if product.stock_qty < payload.quantity:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Only {product.stock_qty} units in stock")

    item = db.query(CartItem).filter(CartItem.user_id == user.id, CartItem.product_id == product.id).first()
    if item is None:
        item = CartItem(user_id=user.id, product_id=product.id, quantity=payload.quantity)
        db.add(item)
    else:
        new_qty = item.quantity + payload.quantity
        if product.stock_qty < new_qty:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Only {product.stock_qty} units in stock")
        item.quantity = new_qty
    db.commit()
    db.refresh(item)
    return CartItemOut(id=item.id, product_id=product.id, name=product.name, price_cents=product.price_cents, quantity=item.quantity, store_id=product.store_id)


@router.patch("/{item_id}", response_model=CartItemOut)
def update_cart_item(item_id: int, payload: CartAddRequest, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    item = db.query(CartItem).options(joinedload(CartItem.product)).filter(CartItem.id == item_id, CartItem.user_id == user.id).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")
    if item.product.stock_qty < payload.quantity:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Only {item.product.stock_qty} units in stock")
    item.quantity = payload.quantity
    db.commit()
    db.refresh(item)
    return CartItemOut(id=item.id, product_id=item.product_id, name=item.product.name, price_cents=item.product.price_cents, quantity=item.quantity, store_id=item.product.store_id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cart_item(item_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == user.id).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")
    db.delete(item)
    db.commit()
