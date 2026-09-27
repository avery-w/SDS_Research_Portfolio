from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth_service import register_user, login_user, logout_token
from app.utils.security import decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=dict, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": str(user.id), "email": user.email, "role": user.role.value}


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await login_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout", status_code=204)
async def logout(token: str):
    payload = decode_token(token)
    await logout_token(payload["jti"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh(token: str):
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    from app.utils.security import create_access_token, create_refresh_token
    token_data = {"sub": payload["sub"], "role": payload.get("role", "customer")}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )
