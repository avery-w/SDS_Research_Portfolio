"""HTML page routes (server-rendered with Jinja2 + HTMX)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Order, Product, Store, User, UserRole, PlatformSetting
from app.security import get_current_user, get_current_user_optional

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def _context(request: Request, user: Optional[User] = None, **kwargs) -> dict:
    ctx: dict = {"request": request, "user": user, **kwargs}
    return ctx


# ── Auth pages ──────────────────────────
@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        "auth/login.html", _context(request, flash=None)
    )


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(
        "auth/register.html", _context(request)
    )


# ── Customer pages ──────────────────────
@router.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_db), user=Depends(get_current_user_optional)):
    products = await db.execute(
        select(Product)
        .where(Product.is_active == True)
        .options(selectinload(Product.images))
        .limit(8)
    )
    return templates.TemplateResponse(
        "customer/home.html",
        _context(request, user=user, products=products.scalars().all()),
    )


@router.get("/products")
async def products_page(
    request: Request,
    q: Optional[str] = None,
    page: int = 1,
    user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    return templates.TemplateResponse(
        "customer/products.html",
        _context(request, user=user, q=q, page=page),
    )


@router.get("/products/{product_id}")
async def product_detail_page(
    request: Request,
    product_id: int,
    user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    return templates.TemplateResponse(
        "customer/product_detail.html",
        _context(request, user=user, product_id=product_id),
    )


@router.get("/cart")
async def cart_page(request: Request, user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(
        "customer/cart.html", _context(request, user=user)
    )


@router.get("/checkout")
async def checkout_page(request: Request, user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(
        "customer/checkout.html", _context(request, user=user)
    )


@router.get("/orders")
async def orders_page(
    request: Request,
    user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    orders = []
    if user and user.role == UserRole.CUSTOMER:
        result = await db.execute(
            select(Order)
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
    return templates.TemplateResponse(
        "customer/orders.html",
        _context(request, user=user, orders=orders),
    )


@router.get("/orders/{order_id}")
async def order_detail_page(
    request: Request,
    order_id: int,
    user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    order = None
    if user:
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
    status_bg = {
        "pending": "yellow", "confirmed": "blue", "processing": "blue",
        "shipped": "indigo", "delivered": "green", "cancelled": "red",
        "returned": "gray", "refunded": "gray",
    }
    bg = status_bg.get(order.status.value, "gray") if order else "gray"
    return templates.TemplateResponse(
        "customer/order_detail.html",
        _context(request, user=user, order=order, status_bg=bg),
    )


@router.get("/returns")
async def returns_page(request: Request, user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(
        "customer/returns.html", _context(request, user=user)
    )


@router.get("/account")
async def account_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "customer/account.html", _context(request, user=user)
    )


@router.get("/messages")
async def messages_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "customer/messages.html", _context(request, user=user)
    )


@router.get("/stores")
async def stores_page(request: Request, user=Depends(get_current_user_optional), db: AsyncSession = Depends(get_db)):
    stores = []
    result = await db.execute(select(Store).where(Store.is_active == True))
    stores = result.scalars().all()
    return templates.TemplateResponse(
        "customer/home.html",
        _context(request, user=user, stores=stores),
    )


# ── Seller pages ────────────────────────
@router.get("/seller")
async def seller_dashboard_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return templates.TemplateResponse(
        "seller/dashboard.html", _context(request, user=user)
    )


@router.get("/seller/products")
async def seller_products_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    products = []
    if user.store:
        result = await db.execute(
            select(Product).where(Product.store_id == user.store.id)
        )
        products = result.scalars().all()
    return templates.TemplateResponse(
        "seller/products.html", _context(request, user=user, products=products)
    )


@router.get("/seller/orders")
async def seller_orders_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orders = []
    if user.store:
        result = await db.execute(
            select(Order).where(Order.store_id == user.store.id)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
    return templates.TemplateResponse(
        "seller/orders.html", _context(request, user=user, orders=orders)
    )


@router.get("/seller/store")
async def seller_store_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return templates.TemplateResponse(
        "seller/manage_store.html", _context(request, user=user)
    )


# ── Admin pages ─────────────────────────
@router.get("/admin")
async def admin_dashboard_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return templates.TemplateResponse(
        "admin/dashboard.html", _context(request, user=user)
    )


@router.get("/admin/users")
async def admin_users_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    users = []
    result = await db.execute(select(User))
    users = result.scalars().all()
    return templates.TemplateResponse(
        "admin/users.html", _context(request, user=user, users=users)
    )


@router.get("/admin/orders")
async def admin_orders_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orders = []
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    orders = result.scalars().all()
    return templates.TemplateResponse(
        "admin/orders.html", _context(request, user=user, orders=orders)
    )


@router.get("/admin/products")
async def admin_products_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    products = []
    result = await db.execute(select(Product))
    products = result.scalars().all()
    return templates.TemplateResponse(
        "admin/products.html", _context(request, user=user, products=products)
    )


@router.get("/admin/stores")
async def admin_stores_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stores = []
    result = await db.execute(select(Store))
    stores = result.scalars().all()
    return templates.TemplateResponse(
        "admin/stores.html", _context(request, user=user, stores=stores)
    )


@router.get("/admin/settings")
async def admin_settings_page(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = {}
    result = await db.execute(select(PlatformSetting))
    for s in result.scalars().all():
        settings[s.key] = {"value": s.value, "type": s.type, "description": s.description}
    return templates.TemplateResponse(
        "admin/settings.html", _context(request, user=user, settings=settings)
    )


# ── Chatbot & misc ──────────────────────
@router.get("/chatbot")
async def chatbot_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "customer/chatbot.html", _context(request, user=user)
    )


@router.get("/{path:path}")
async def catch_all(request: Request, path: str, user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(
        "index.html", _context(request, user=user)
    )
