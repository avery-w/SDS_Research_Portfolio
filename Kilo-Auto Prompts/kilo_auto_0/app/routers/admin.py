from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import require_role
from app.database import get_session
from app.models import Analytics, Order, PlatformSetting, Product, ReturnRequest, Store, User, UserRole
from app.schemas import AnalyticsCreate, AnalyticsRead, PlatformSettingCreate, PlatformSettingRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[dict])
def admin_list_users(current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.put("/users/{user_id}/deactivate")
def admin_deactivate_user(user_id: int, current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    session.add(user)
    session.commit()
    return {"message": "User deactivated"}


@router.put("/users/{user_id}/activate")
def admin_activate_user(user_id: int, current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    session.add(user)
    session.commit()
    return {"message": "User activated"}


@router.get("/orders", response_model=list[dict])
def admin_list_orders(current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    orders = session.exec(select(Order)).all()
    return [
        {
            "id": o.id,
            "user_id": o.user_id,
            "store_id": o.store_id,
            "total": o.total,
            "status": o.status,
            "created_at": o.created_at,
            "updated_at": o.updated_at,
        }
        for o in orders
    ]


@router.put("/orders/{order_id}/override")
def admin_override_order(order_id: int, status: str, current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status
    order.updated_at = order.updated_at
    session.add(order)
    session.commit()
    return {"message": "Order status updated"}


@router.post("/analytics", response_model=AnalyticsRead, status_code=status.HTTP_201_CREATED)
def admin_record_analytics(analytics: AnalyticsCreate, current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    db_analytics = Analytics(**analytics.dict())
    session.add(db_analytics)
    session.commit()
    session.refresh(db_analytics)
    return db_analytics


@router.get("/analytics", response_model=list[AnalyticsRead])
def admin_get_analytics(metric_name: str | None = None, current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    stmt = select(Analytics)
    if metric_name:
        stmt = stmt.where(Analytics.metric_name == metric_name)
    return session.exec(stmt.order_by(Analytics.recorded_at.desc())).all()


@router.post("/platform-settings", response_model=PlatformSettingRead, status_code=status.HTTP_201_CREATED)
def admin_create_setting(setting: PlatformSettingCreate, current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    existing = session.exec(select(PlatformSetting).where(PlatformSetting.key == setting.key)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Setting already exists")
    db_setting = PlatformSetting(**setting.dict())
    session.add(db_setting)
    session.commit()
    session.refresh(db_setting)
    return db_setting


@router.get("/platform-settings", response_model=list[PlatformSettingRead])
def admin_list_settings(current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    return session.exec(select(PlatformSetting)).all()
