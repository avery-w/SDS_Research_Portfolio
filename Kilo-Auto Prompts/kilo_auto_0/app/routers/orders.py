import os
import shutil
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlmodel import Session, select

from app.auth import get_current_active_user, require_role
from app.database import get_session
from app.models import CartItem, Order, OrderItem, Product, ReturnRequest, Store, User, UserRole
from app.schemas import OrderCreate, OrderItemCreate, OrderRead, ReturnRequestCreate, ReturnRequestRead

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/checkout", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def checkout(order: OrderCreate, current_user: User = Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN)), session: Session = Depends(get_session)):
    if not order.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    first_product = session.get(Product, order.items[0].product_id)
    if not first_product:
        raise HTTPException(status_code=404, detail="Product not found")
    store_id = first_product.store_id
    total = 0.0
    total_weight = 0.0
    max_dim = {"length": 0.0, "width": 0.0, "height": 0.0}
    for item in order.items:
        product = session.get(Product, item.product_id)
        if not product or product.store_id != store_id:
            raise HTTPException(status_code=400, detail="All items must be from the same store")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
        total += item.price * item.quantity
        total_weight += 5.0 * item.quantity
        max_dim["length"] = max(max_dim["length"], 12.0)
        max_dim["width"] = max(max_dim["width"], 8.0)
        max_dim["height"] = max(max_dim["height"], 6.0)
        product.stock -= item.quantity
        session.add(product)
    from app.shipping import get_ups_shipping_rates
    shipping_rate = await get_ups_shipping_rates(
        dest_zip=order.shipping_zip,
        dest_country=order.shipping_country,
        weight_lbs=total_weight,
        length_in=max_dim["length"],
        width_in=max_dim["width"],
        height_in=max_dim["height"],
    )
    total += shipping_rate or 0.0
    db_order = Order(
        user_id=current_user.id,
        store_id=store_id,
        total=round(total, 2),
        shipping_address=order.shipping_address,
        shipping_city=order.shipping_city,
        shipping_state=order.shipping_state,
        shipping_zip=order.shipping_zip,
        shipping_country=order.shipping_country,
        shipping_rate=shipping_rate,
        status="confirmed",
    )
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    for item in order.items:
        db_item = OrderItem(order_id=db_order.id, product_id=item.product_id, quantity=item.quantity, price=item.price)
        session.add(db_item)
    session.commit()
    for item in order.items:
        cart_items = session.exec(select(CartItem).where(CartItem.user_id == current_user.id, CartItem.product_id == item.product_id)).all()
        for ci in cart_items:
            session.delete(ci)
    session.commit()
    session.refresh(db_order)
    return db_order


@router.get("/", response_model=list[OrderRead])
def list_orders(current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    stmt = select(Order).where(Order.user_id == current_user.id)
    if current_user.role == UserRole.SELLER:
        stmt = select(Order).join(Store).where(Store.owner_id == current_user.id)
    elif current_user.role == UserRole.ADMIN:
        stmt = select(Order)
    return session.exec(stmt).all()


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not permitted")
    if current_user.role == UserRole.SELLER:
        store = session.get(Store, order.store_id)
        if store.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not permitted")
    return order


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int, current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not permitted")
    if current_user.role == UserRole.SELLER:
        store = session.get(Store, order.store_id)
        if store.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not permitted")
    if order.status not in ("pending", "confirmed"):
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")
    order.status = "cancelled"
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()
    return {"message": "Order cancelled"}
