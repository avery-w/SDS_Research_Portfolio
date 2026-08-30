from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_current_active_user, require_role
from app.database import get_session
from app.models import Product, Store, User, UserRole
from app.schemas import ProductRead

router = APIRouter(prefix="/seller", tags=["seller"])


@router.get("/stores", response_model=list[dict])
def seller_stores(current_user: User = Depends(require_role(UserRole.SELLER, UserRole.ADMIN)), session: Session = Depends(get_session)):
    stores = session.exec(select(Store).where(Store.owner_id == current_user.id)).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "is_active": s.is_active,
            "created_at": s.created_at,
        }
        for s in stores
    ]


@router.get("/products", response_model=list[ProductRead])
def seller_products(current_user: User = Depends(require_role(UserRole.SELLER, UserRole.ADMIN)), session: Session = Depends(get_session)):
    stores = session.exec(select(Store).where(Store.owner_id == current_user.id)).all()
    store_ids = [s.id for s in stores]
    if not store_ids:
        return []
    return session.exec(select(Product).where(Product.store_id.in_(store_ids))).all()
