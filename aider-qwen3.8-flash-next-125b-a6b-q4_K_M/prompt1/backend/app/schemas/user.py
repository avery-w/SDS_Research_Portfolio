from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    role: UserRole = UserRole.CUSTOMER


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
