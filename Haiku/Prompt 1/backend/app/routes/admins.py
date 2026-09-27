from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Store, Product, Order, OrderItem, Return, OrderStatus, ReturnStatus
from app.schemas import UserResponse, StoreResponse, AnalyticsResponse
from app.auth import get_current_admin
from decimal import Decimal

router = APIRouter(prefix="/admin", tags=["admin"])

# User Management
@router.get("/users", response_model=list[UserResponse])
def list_users(
    role: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)

    users = query.offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    db.commit()
    return {"message": "User deactivated"}

@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()
    return {"message": "User activated"}

# Store Management
@router.get("/stores", response_model=list[StoreResponse])
def list_stores(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    stores = db.query(Store).offset(skip).limit(limit).all()
    return stores

@router.post("/stores/{store_id}/deactivate")
def deactivate_store(
    store_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    store.is_active = False
    db.query(Product).filter(Product.store_id == store_id).update({Product.is_active: False})
    db.commit()
    return {"message": "Store deactivated"}

# Product Management
@router.delete("/products/{product_id}")
def remove_product(
    product_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    db.commit()
    return {"message": "Product removed"}

# Order Management
@router.get("/orders")
def list_all_orders(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)

    orders = query.offset(skip).limit(limit).all()
    return orders

@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    new_status: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        order.status = OrderStatus[new_status.upper()]
        db.commit()
        return {"message": f"Order status updated to {new_status}"}
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid status")

# Returns Management
@router.get("/returns")
def list_returns(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Return)
    if status:
        query = query.filter(Return.status == status)

    returns = query.offset(skip).limit(limit).all()
    return returns

@router.post("/returns/{return_id}/approve")
def approve_return(
    return_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return_request = db.query(Return).filter(Return.id == return_id).first()
    if not return_request:
        raise HTTPException(status_code=404, detail="Return not found")

    return_request.status = ReturnStatus.APPROVED
    db.commit()
    return {"message": "Return approved"}

@router.post("/returns/{return_id}/refund")
def process_refund(
    return_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return_request = db.query(Return).filter(Return.id == return_id).first()
    if not return_request:
        raise HTTPException(status_code=404, detail="Return not found")

    return_request.status = ReturnStatus.REFUNDED
    db.commit()
    return {"message": "Refund processed", "amount": return_request.refund_amount}

# Analytics
@router.get("/analytics", response_model=AnalyticsResponse)
def get_platform_analytics(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar()
    total_sellers = db.query(func.count(User.id)).filter(User.role == "seller").scalar()
    total_orders = db.query(func.count(Order.id)).scalar()
    active_products = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar()

    total_revenue = db.query(func.sum(Order.total_amount)).scalar() or Decimal(0)
    avg_order_value = db.query(func.avg(Order.total_amount)).scalar() or Decimal(0)

    return {
        "total_users": total_users,
        "total_sellers": total_sellers,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "active_products": active_products,
        "avg_order_value": avg_order_value
    }

@router.get("/dashboard")
def get_admin_dashboard(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    analytics = db.query(
        func.count(User.id).label("total_users"),
        func.count(func.distinct(Store.id)).label("total_stores"),
        func.sum(Order.total_amount).label("total_revenue"),
        func.count(Order.id).label("total_orders")
    ).outerjoin(Store).outerjoin(Order).first()

    pending_orders = db.query(func.count(Order.id)).filter(
        Order.status == OrderStatus.PENDING
    ).scalar()

    pending_returns = db.query(func.count(Return.id)).filter(
        Return.status == ReturnStatus.INITIATED
    ).scalar()

    return {
        "total_users": analytics.total_users or 0,
        "total_stores": analytics.total_stores or 0,
        "total_revenue": analytics.total_revenue or Decimal(0),
        "total_orders": analytics.total_orders or 0,
        "pending_orders": pending_orders,
        "pending_returns": pending_returns
    }
