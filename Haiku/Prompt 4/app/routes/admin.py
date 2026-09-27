from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.auth import require_role

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=list[schemas.User])
def get_all_users(
    skip: int = 0,
    limit: int = 20,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    new_role: models.UserRole,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = new_role
    db.commit()
    return {"message": f"User {user_id} role updated to {new_role}"}

@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()
    return {"message": f"User {user_id} deactivated"}

@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()
    return {"message": f"User {user_id} activated"}

@router.get("/stores", response_model=list[schemas.Store])
def get_all_stores(
    skip: int = 0,
    limit: int = 20,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    stores = db.query(models.Store).offset(skip).limit(limit).all()
    return stores

@router.post("/stores/{store_id}/deactivate")
def deactivate_store(
    store_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    store.is_active = False
    db.commit()
    return {"message": f"Store {store_id} deactivated"}

@router.get("/analytics/sales")
def get_sales_analytics(
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    total_orders = db.query(func.count(models.Order.id)).scalar()
    total_revenue = db.query(func.sum(models.Order.total_amount)).scalar() or 0
    paid_orders = db.query(func.count(models.Order.id)).filter(
        models.Order.status == models.OrderStatus.PAID
    ).scalar()

    return {
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
        "paid_orders": paid_orders,
        "pending_orders": total_orders - paid_orders
    }

@router.get("/analytics/users")
def get_user_analytics(
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(models.User.id)).scalar()
    customers = db.query(func.count(models.User.id)).filter(
        models.User.role == models.UserRole.CUSTOMER
    ).scalar()
    sellers = db.query(func.count(models.User.id)).filter(
        models.User.role == models.UserRole.SELLER
    ).scalar()
    active_users = db.query(func.count(models.User.id)).filter(
        models.User.is_active == True
    ).scalar()

    return {
        "total_users": total_users,
        "customers": customers,
        "sellers": sellers,
        "active_users": active_users
    }

@router.get("/analytics/products")
def get_product_analytics(
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    total_products = db.query(func.count(models.Product.id)).scalar()
    active_products = db.query(func.count(models.Product.id)).filter(
        models.Product.is_active == True
    ).scalar()
    total_inventory = db.query(func.sum(models.Product.quantity_available)).scalar() or 0

    return {
        "total_products": total_products,
        "active_products": active_products,
        "total_inventory": int(total_inventory)
    }
