from fastapi import Cookie, Depends, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, User
from app.security import read_session_token


def get_current_user(
    session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not session:
        return None
    user_id = read_session_token(session)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


def require_role(*roles: Role):
    def dependency(user: User = Depends(require_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        return user

    return dependency


require_customer = require_role(Role.customer, Role.admin)
require_seller = require_role(Role.seller, Role.admin)
require_admin = require_role(Role.admin)


def verify_csrf(
    csrf_token: str = Form(...),
    csrf_cookie: str | None = Cookie(default=None, alias="csrf_token"),
) -> None:
    if not csrf_cookie or csrf_token != csrf_cookie:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
