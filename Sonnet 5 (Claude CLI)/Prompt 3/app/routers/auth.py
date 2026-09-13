from fastapi import APIRouter, Cookie, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.limiter import limiter
from app.models import Cart, Role, User
from app.security import create_session_token, hash_password, verify_password

router = APIRouter()
templates = Jinja2Templates(directory="templates")
settings = get_settings()


@router.get("/register")
def register_form(request: Request, user: User | None = Depends(get_current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register")
@limiter.limit("5/minute")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("customer"),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    if role not in ("customer", "seller"):
        role = "customer"
    if len(password) < 8:
        return templates.TemplateResponse(
            request, "register.html", {"error": "Password must be at least 8 characters."}
        )
    if len(password.encode("utf-8")) > 72:
        return templates.TemplateResponse(
            request, "register.html", {"error": "Password must be under 72 characters."}
        )
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return templates.TemplateResponse(
            request, "register.html", {"error": "An account with that email already exists."}
        )

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role=Role(role),
    )
    db.add(user)
    db.flush()
    db.add(Cart(user_id=user.id))
    db.commit()

    resp = RedirectResponse("/", status_code=303)
    _set_session_cookie(resp, user.id)
    return resp


@router.get("/login")
def login_form(request: Request, user: User | None = Depends(get_current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
@limiter.limit("10/minute")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash) or not user.is_active:
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid email or password."}, status_code=401
        )

    resp = RedirectResponse("/", status_code=303)
    _set_session_cookie(resp, user.id)
    return resp


@router.post("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("session")
    return resp


def _set_session_cookie(resp: RedirectResponse, user_id: int) -> None:
    resp.set_cookie(
        "session",
        create_session_token(user_id),
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=60 * 60 * 24 * 7,
    )
