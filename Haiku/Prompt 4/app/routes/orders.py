from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_active_user, require_role

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("", response_model=list[schemas.Order])
def get_my_orders(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role == models.UserRole.CUSTOMER:
        orders = db.query(models.Order).filter(models.Order.customer_id == current_user.id).all()
    elif current_user.role == models.UserRole.SELLER:
        seller_stores = db.query(models.Store).filter(models.Store.owner_id == current_user.id).all()
        store_ids = [s.id for s in seller_stores]
        orders = db.query(models.Order).filter(models.Order.store_id.in_(store_ids)).all()
    else:
        orders = db.query(models.Order).all()

    return orders

@router.get("/{order_id}", response_model=schemas.Order)
def get_order(
    order_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.customer_id != current_user.id and current_user.role == models.UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Not authorized")

    if current_user.role == models.UserRole.SELLER:
        seller_stores = db.query(models.Store).filter(models.Store.owner_id == current_user.id).all()
        if order.store_id not in [s.id for s in seller_stores]:
            raise HTTPException(status_code=403, detail="Not authorized")

    return order

@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.customer_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    if order.status in [models.OrderStatus.SHIPPED, models.OrderStatus.DELIVERED]:
        raise HTTPException(status_code=400, detail="Cannot cancel shipped/delivered order")

    order.status = models.OrderStatus.CANCELLED
    db.commit()
    return {"message": "Order cancelled"}

@router.post("/{order_id}/request-return")
def request_return(
    order_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if order.status != models.OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Only delivered orders can be returned")

    order.status = models.OrderStatus.RETURN_REQUESTED
    db.commit()
    return {"message": "Return request submitted"}

@router.post("/{order_id}/approve-return")
def approve_return(
    order_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.SELLER, models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == models.UserRole.SELLER:
        seller_stores = db.query(models.Store).filter(models.Store.owner_id == current_user.id).all()
        if order.store_id not in [s.id for s in seller_stores]:
            raise HTTPException(status_code=403, detail="Not authorized")

    if order.status != models.OrderStatus.RETURN_REQUESTED:
        raise HTTPException(status_code=400, detail="Order is not return requested")

    order.status = models.OrderStatus.RETURNED
    db.commit()
    return {"message": "Return approved"}

@router.post("/{order_id}/mark-shipped")
def mark_shipped(
    order_id: int,
    tracking_number: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    store = db.query(models.Store).filter(models.Store.id == order.store_id).first()
    if store.owner_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    order.status = models.OrderStatus.SHIPPED
    order.tracking_number = tracking_number
    db.commit()
    return {"message": "Order marked as shipped"}
