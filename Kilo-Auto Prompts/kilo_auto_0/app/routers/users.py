from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_current_active_user, require_role
from app.database import get_session
from app.models import User, UserRole
from app.schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
async def list_users(current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    return session.exec(select(User)).all()


@router.put("/{user_id}/deactivate")
async def deactivate_user(user_id: int, current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    session.add(user)
    session.commit()
    return {"message": "User deactivated"}


@router.put("/{user_id}/activate")
async def activate_user(user_id: int, current_user: User = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    session.add(user)
    session.commit()
    return {"message": "User activated"}
