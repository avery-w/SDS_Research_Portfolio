from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.deps.auth import require_roles
from app.db.session import get_session
from app.models.user import Role, User
from app.models.seller import SellerProfile, Store

router = APIRouter(prefix="/sellers", tags=["sellers"])

@router.post("/stores", responses={401: {"description": "Missing auth"}, 403: {"description": "Not a seller"}, 422: {"description": "Invalid"}})
async def create_store(name: str, description: str | None = None, db: AsyncSession = Depends(get_session), user: User = Depends(require_roles(Role.seller))):
    profile = (await db.execute(select(SellerProfile).where(SellerProfile.user_id == user.id))).scalar_one_or_none()
    if not profile:
        profile = SellerProfile(user_id=user.id, display_name=user.email.split("@")[0])
        db.add(profile); await db.flush()
    store = Store(seller_id=profile.id, name=name, description=description)
    db.add(store); await db.commit(); await db.refresh(store)
    return {"id": store.id, "name": store.name, "description": store.description}
