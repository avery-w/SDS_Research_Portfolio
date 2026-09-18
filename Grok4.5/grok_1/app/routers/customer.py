from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from ..database import get_db
from ..auth import require_role
from ..models import User, Product, CartItem, Order, OrderItem, OrderStatus, UserRole, Store
from ..schemas import ProductOut, CartItemCreate, CartItemOut, OrderOut

router = APIRouter(prefix="/customer", tags=["customer"])


@router.get("/products", response_model=list[ProductOut])
def browse_products(
    q: str | None = Query(None, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Public product catalog. 422 on bad pagination params."""
    query = (
        db.query(Product)
        .join(Store)
        .filter(Product.is_active == True, Store.is_active == True)
    )
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.ilike(like), Product.description.ilike(like)))
    return query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Public single product. 404 if not found or inactive."""
    product = (
        db.query(Product)
        .join(Store)
        .filter(Product.id == product_id, Product.is_active == True, Store.is_active == True)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/cart", response_model=list[CartItemOut])
def view_cart(
    current_user: User = Depends(require_role(UserRole.customer)),
    db: Session = Depends(get_db),
):
    """401/403 if not an authenticated customer."""
    return (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == current_user.id)
        .all()
    )


@router.post("/cart", response_model=CartItemOut, status_code=201)
def add_to_cart(
    body: CartItemCreate,
    current_user: User = Depends(require_role(UserRole.customer)),
    db: Session = Depends(get_db),
):
    """
    - 401/403: not customer
    - 404: product missing
    - 400: insufficient stock / inactive product
    - 422: invalid quantity
    """
    product = db.query(Product).filter(Product.id == body.product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.inventory < body.quantity:
        raise HTTPException(status_code=400, detail="Not enough inventory")

    existing = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user.id, CartItem.product_id == body.product_id)
        .first()
    )
    if existing:
        if product.inventory < existing.quantity + body.quantity:
            raise HTTPException(status_code=400, detail="Not enough inventory for requested quantity")
        existing.quantity += body.quantity
        db.commit()
        db.refresh(existing)
        return existing

    item = CartItem(user_id=current_user.id, product_id=body.product_id, quantity=body.quantity)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/cart/{item_id}", status_code=204)
def remove_from_cart(
    item_id: int,
    current_user: User = Depends(require_role(UserRole.customer)),
    db: Session = Depends(get_db),
):
    """401/403 if not customer; 404 if item not in this user's cart."""
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.user_id == current_user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()


@router.get("/orders", response_model=list[OrderOut])
def order_history(
    current_user: User = Depends(require_role(UserRole.customer)),
    db: Session = Depends(get_db),
):
    """401/403 if not customer."""
    return (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.customer_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def request_cancellation(
    order_id: int,
    current_user: User = Depends(require_role(UserRole.customer)),
    db: Session = Depends(get_db),
):
    """
    - 401/403: not customer
    - 404: order not found or not owned by user
    - 400: order not in cancellable state
    """
    order = db.query(Order).filter(Order.id == order_id, Order.customer_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in (OrderStatus.pending, OrderStatus.paid):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order in status '{order.status.value}'",
        )
    order.status = OrderStatus.cancelled
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/return", response_model=OrderOut)
def request_return(
    order_id: int,
    current_user: User = Depends(require_role(UserRole.customer)),
    db: Session = Depends(get_db),
):
    """
    - 401/403: not customer
    - 404: order not found / not owned
    - 400: order not shipped or delivered
    """
    order = db.query(Order).filter(Order.id == order_id, Order.customer_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in (OrderStatus.shipped, OrderStatus.delivered):
        raise HTTPException(status_code=400, detail="Returns only allowed for shipped or delivered orders")
    order.status = OrderStatus.return_requested
    db.commit()
    db.refresh(order)
    return order
