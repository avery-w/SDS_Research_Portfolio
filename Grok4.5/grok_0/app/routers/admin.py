from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..database import get_db
from ..auth import require_role
from ..models import (
    User, Store, Product, Order, OrderItem, OrderStatus, UserRole
)
from ..schemas import UserOut, StoreOut, ProductOut, OrderOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Cannot deactivate an admin")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/activate", response_model=UserOut)
def activate_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/role", response_model=UserOut)
def set_user_role(
    user_id: int,
    role: UserRole,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    # Ensure seller has a store
    if role == UserRole.seller:
        store = db.query(Store).filter(Store.owner_id == user.id).first()
        if not store:
            store = Store(owner_id=user.id, name=f"{user.full_name or user.email}'s Store")
            db.add(store)
    db.commit()
    db.refresh(user)
    return user


@router.get("/stores", response_model=list[StoreOut])
def list_stores(
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    return db.query(Store).order_by(Store.created_at.desc()).all()


@router.patch("/stores/{store_id}/deactivate", response_model=StoreOut)
def deactivate_store(
    store_id: int,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    store.is_active = False
    db.commit()
    db.refresh(store)
    return store


@router.get("/products", response_model=list[ProductOut])
def list_all_products(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    return (
        db.query(Product)
        .order_by(Product.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.patch("/products/{product_id}/deactivate", response_model=ProductOut)
def deactivate_product(
    product_id: int,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()
    db.refresh(product)
    return product


@router.get("/orders", response_model=list[OrderOut])
def list_all_orders(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    return (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def override_order_status(
    order_id: int,
    status: OrderStatus,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status
    db.commit()
    db.refresh(order)
    return order


@router.get("/analytics")
def sales_analytics(
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    paid_statuses = [
        OrderStatus.paid,
        OrderStatus.shipped,
        OrderStatus.delivered,
    ]
    total_revenue = (
        db.query(func.coalesce(func.sum(Order.total), 0.0))
        .filter(Order.status.in_(paid_statuses))
        .scalar()
    )
    order_count = db.query(func.count(Order.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    active_stores = db.query(func.count(Store.id)).filter(Store.is_active == True).scalar()
    active_products = (
        db.query(func.count(Product.id)).filter(Product.is_active == True).scalar()
    )

    # Revenue by seller (top 10)
    top_sellers = (
        db.query(
            OrderItem.seller_id,
            func.sum(OrderItem.unit_price * OrderItem.quantity).label("revenue"),
        )
        .join(Order)
        .filter(Order.status.in_(paid_statuses))
        .group_by(OrderItem.seller_id)
        .order_by(func.sum(OrderItem.unit_price * OrderItem.quantity).desc())
        .limit(10)
        .all()
    )

    return {
        "total_revenue": float(total_revenue),
        "order_count": order_count,
        "active_users": active_users,
        "active_stores": active_stores,
        "active_products": active_products,
        "top_sellers": [
            {"seller_id": s[0], "revenue": float(s[1])} for s in top_sellers
        ],
    }
