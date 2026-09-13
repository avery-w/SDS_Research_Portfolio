from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Product, Store, User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
def home(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    stmt = select(Product).join(Store).where(Product.is_active.is_(True), Store.is_active.is_(True))
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))
    products = db.scalars(stmt.order_by(Product.created_at.desc()).limit(60)).all()
    return templates.TemplateResponse(
        request, "home.html", {"products": products, "q": q, "user": user}
    )


@router.get("/products/{product_id}")
def product_detail(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        return templates.TemplateResponse(
            request, "not_found.html", {"user": user}, status_code=404
        )
    return templates.TemplateResponse(
        request, "product_detail.html", {"product": product, "user": user}
    )
