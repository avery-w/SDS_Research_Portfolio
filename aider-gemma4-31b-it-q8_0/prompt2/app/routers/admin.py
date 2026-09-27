from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import get_db
from . import models, schemas, auth

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/analytics", response_model=schemas.AnalyticsOut)
def get_analytics(
    db: Session = Depends(get_db), 
    user: models.User = Depends(auth.RoleChecker([models.UserRole.admin]))
):
    total_revenue = db.query(func.sum(models.Order.total_price)).scalar() or 0.0
    total_orders = db.query(func.count(models.Order.id)).scalar() or 0
    
    return {"total_revenue": total_revenue, "total_orders": total_orders}

@router.patch("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    user: models.User = Depends(auth.RoleChecker([models.UserRole.admin]))
):
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    target_user.is_active = False
    db.commit()
    return {"message": f"User {user_id} deactivated"}
