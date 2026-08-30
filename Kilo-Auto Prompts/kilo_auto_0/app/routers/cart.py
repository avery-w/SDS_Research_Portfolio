from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import require_role, get_current_active_user
from app.database import get_session
from app.models import CartItem, Product, User, UserRole
from app.schemas import CartItemCreate, CartItemRead

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
def add_to_cart(item: CartItemCreate, current_user: User = Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN)), session: Session = Depends(get_session)):
    product = session.get(Product, item.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock < item.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    existing = session.exec(select(CartItem).where(CartItem.user_id == current_user.id, CartItem.product_id == item.product_id)).first()
    if existing:
        existing.quantity += item.quantity
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    db_item = CartItem(user_id=current_user.id, product_id=item.product_id, quantity=item.quantity)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@router.get("/", response_model=list[CartItemRead])
def get_cart(current_user: User = Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN)), session: Session = Depends(get_session)):
    return session.exec(select(CartItem).where(CartItem.user_id == current_user.id)).all()


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart_item(item_id: int, current_user: User = Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN)), session: Session = Depends(get_session)):
    item = session.get(CartItem, item_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(item)
    session.commit()
