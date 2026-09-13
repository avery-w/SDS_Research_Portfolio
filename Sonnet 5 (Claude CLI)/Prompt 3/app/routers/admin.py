from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin, verify_csrf
from app.models import (
    Order,
    OrderItem,
    OrderStatus,
    PlatformSetting,
    Product,
    ReturnRequest,
    ReturnStatus,
    Store,
    User,
)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    total_sales_cents = db.scalar(
        select(func.coalesce(func.sum(Order.total_cents), 0)).where(Order.status != OrderStatus.cancelled)
    )
    order_count = db.scalar(select(func.count(Order.id)))
    user_count = db.scalar(select(func.count(User.id)))
    store_count = db.scalar(select(func.count(Store.id)))
    top_products = db.execute(
        select(Product.name, func.sum(OrderItem.quantity).label("sold"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
    ).all()
    pending_returns = db.scalar(
        select(func.count(ReturnRequest.id)).where(ReturnRequest.status == ReturnStatus.requested)
    )
    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "user": user,
            "total_sales_cents": total_sales_cents,
            "order_count": order_count,
            "user_count": user_count,
            "store_count": store_count,
            "top_products": top_products,
            "pending_returns": pending_returns,
        },
    )


@router.get("/users")
def list_users(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return templates.TemplateResponse(request, "admin_users.html", {"user": user, "users": users})


@router.post("/users/{target_id}/toggle-active", dependencies=[Depends(verify_csrf)])
def toggle_user_active(target_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, target_id)
    if target and target.id != user.id:
        target.is_active = not target.is_active
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/stores")
def list_stores(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    stores = db.scalars(select(Store).order_by(Store.created_at.desc())).all()
    return templates.TemplateResponse(request, "admin_stores.html", {"user": user, "stores": stores})


@router.post("/stores/{store_id}/toggle-active", dependencies=[Depends(verify_csrf)])
def toggle_store_active(store_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    store = db.get(Store, store_id)
    if store:
        store.is_active = not store.is_active
        db.commit()
    return RedirectResponse("/admin/stores", status_code=303)


@router.get("/products")
def list_all_products(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    products = db.scalars(select(Product).order_by(Product.created_at.desc())).all()
    return templates.TemplateResponse(request, "admin_products.html", {"user": user, "products": products})


@router.post("/products/{product_id}/toggle-active", dependencies=[Depends(verify_csrf)])
def toggle_product_active(product_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product:
        product.is_active = not product.is_active
        db.commit()
    return RedirectResponse("/admin/products", status_code=303)


@router.get("/orders")
def list_all_orders(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    orders = db.scalars(select(Order).order_by(Order.created_at.desc()).limit(200)).all()
    return templates.TemplateResponse(request, "admin_orders.html", {"user": user, "orders": orders})


@router.post("/orders/{order_id}/override-status", dependencies=[Depends(verify_csrf)])
def override_order_status(
    order_id: int,
    status: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order and status in OrderStatus.__members__:
        order.status = OrderStatus[status]
        db.commit()
    return RedirectResponse("/admin/orders", status_code=303)


@router.get("/returns")
def list_returns(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    returns = db.scalars(select(ReturnRequest).order_by(ReturnRequest.created_at.desc())).all()
    return templates.TemplateResponse(request, "admin_returns.html", {"user": user, "returns": returns})


@router.post("/returns/{return_id}/decide", dependencies=[Depends(verify_csrf)])
def decide_return(
    return_id: int,
    decision: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ret = db.get(ReturnRequest, return_id)
    if ret and decision in ("approved", "rejected", "refunded"):
        ret.status = ReturnStatus(decision)
        db.commit()
    return RedirectResponse("/admin/returns", status_code=303)


@router.get("/settings")
def settings_page(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    settings_rows = db.scalars(select(PlatformSetting)).all()
    return templates.TemplateResponse(request, "admin_settings.html", {"user": user, "settings_rows": settings_rows})


@router.post("/settings", dependencies=[Depends(verify_csrf)])
def update_setting(
    key: str = Form(...),
    value: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    key = key.strip()[:100]
    row = db.get(PlatformSetting, key)
    if row:
        row.value = value
    else:
        db.add(PlatformSetting(key=key, value=value))
    db.commit()
    return RedirectResponse("/admin/settings", status_code=303)
