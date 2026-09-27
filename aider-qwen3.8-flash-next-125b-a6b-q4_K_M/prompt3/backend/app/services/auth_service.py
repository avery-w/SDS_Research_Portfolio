import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserRole
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
import redis.asyncio as aioredis
from app.config import get_settings

settings = get_settings()
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise ValueError("Email already registered")
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole(data.role),
    )
    db.add(user)
    await db.flush()
    return user


async def login_user(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise ValueError("Invalid credentials")
    if not user.is_active:
        raise ValueError("Account deactivated")
    token_data = {"sub": str(user.id), "role": user.role.value}
    access = create_access_token(token_data)
    refresh = create_refresh_token(token_data)
    return TokenResponse(access_token=access, refresh_token=refresh)


async def logout_token(jti: str) -> None:
    await redis_client.setex(f"blacklist:{jti}", 86400, "1")
