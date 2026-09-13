"""Role-based access control (RBAC) dependencies and helpers."""
from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status

from app.models import User, UserRole
from app.security import get_current_user


def role_required(*roles: UserRole) -> Callable:
    """Return a dependency that requires the current user to have one of *roles*."""
    allowed = set(roles)

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions: this action requires the "
                f"{' / '.join(r.value for r in allowed)} role.",
            )
        return current_user

    return _checker


class Permissions:
    """Convenience dependency shortcuts."""

    @staticmethod
    def admin(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )
        return current_user

    @staticmethod
    def seller(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in (UserRole.SELLER, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller access required.",
            )
        return current_user

    @staticmethod
    def customer(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in (UserRole.CUSTOMER, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Customer access required.",
            )
        return current_user


# Aliases for use as Depends(...)
AdminUser = Depends(Permissions.admin)
SellerUser = Depends(Permissions.seller)
CustomerUser = Depends(Permissions.customer)
CurrentUser = Depends(get_current_user)


def role_names(user: User) -> str:
    """Return a human-readable list of roles (for display)."""
    return user.role.value.capitalize()
