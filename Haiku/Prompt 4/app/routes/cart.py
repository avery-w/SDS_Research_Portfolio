from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_active_user

router = APIRouter(prefix="/cart", tags=["cart"])

@router.get("", response_model=list[schemas.CartItem])
def get_cart(current_user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    return items

@router.post("", response_model=schemas.CartItem)
def add_to_cart(
    item: schemas.CartItemBase,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.quantity_available < item.quantity:
        raise HTTPException(status_code=400, detail="Not enough inventory")

    existing_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == item.product_id
    ).first()

    if existing_item:
        existing_item.quantity += item.quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item

    cart_item = models.CartItem(
        user_id=current_user.id,
        product_id=item.product_id,
        quantity=item.quantity
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart_item

@router.put("/{cart_item_id}", response_model=schemas.CartItem)
def update_cart_item(
    cart_item_id: int,
    item: schemas.CartItemBase,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == cart_item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    product = db.query(models.Product).filter(models.Product.id == cart_item.product_id).first()
    if product.quantity_available < item.quantity:
        raise HTTPException(status_code=400, detail="Not enough inventory")

    cart_item.quantity = item.quantity
    db.commit()
    db.refresh(cart_item)
    return cart_item

@router.delete("/{cart_item_id}")
def remove_from_cart(
    cart_item_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == cart_item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(cart_item)
    db.commit()
    return {"message": "Item removed from cart"}

@router.delete("")
def clear_cart(current_user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Cart cleared"}
