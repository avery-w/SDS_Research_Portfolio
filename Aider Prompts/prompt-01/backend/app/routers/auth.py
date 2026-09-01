from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from app.db.session import get_session
from app.models.user import User, Role
from app.utils.hashing import hash_password, verify_password
from app.core.security import create_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenPair, responses={422: {"description": "Invalid input"}})
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_session)):
    exists = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=body.email, hashed_password=hash_password(body.password), role=Role(body.role))
    db.add(user); await db.commit(); await db.refresh(user)
    access = create_token(str(user.id), timedelta(minutes=30), "access")
    refresh = create_token(str(user.id), timedelta(days=7), "refresh")
    return TokenPair(access_token=access, refresh_token=refresh)

@router.post("/login", response_model=TokenPair, responses={401: {"description": "Bad credentials"}, 422: {"description": "Invalid input"}})
async def login(body: LoginRequest, db: AsyncSession = Depends(get_session)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    from datetime import timedelta
    return {
        "access_token": create_token(str(user.id), timedelta(minutes=30), "access"),
        "refresh_token": create_token(str(user.id), timedelta(days=7), "refresh"),
        "token_type": "bearer"
    }
