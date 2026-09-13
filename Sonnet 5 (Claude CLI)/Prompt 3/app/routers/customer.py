from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_customer, verify_csrf
from app.models import Order, OrderItem, OrderStatus, ReturnRequest, SellerMessage, Store, User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/account")
def account(request: Request, user: User = Depends(require_customer)):
    return templates.TemplateResponse(request, "account.html", {"user": user})


@router.get("/orders")
def order_history(request: Request, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    orders = db.scalars(
        select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc())
    ).all()
    return templates.TemplateResponse(request, "orders.html", {"user": user, "orders": orders})


@router.get("/orders/{order_id}")
def order_detail(order_id: int, request: Request, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order or order.customer_id != user.id:
        return templates.TemplateResponse(request, "not_found.html", {"user": user}, status_code=404)
    return templates.TemplateResponse(request, "order_detail.html", {"user": user, "order": order})


@router.post("/orders/{order_id}/cancel", dependencies=[Depends(verify_csrf)])
def cancel_order(order_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order and order.customer_id == user.id and order.status in (OrderStatus.pending_payment, OrderStatus.paid):
        order.status = OrderStatus.cancelled
        for item in order.items:
            item.product.inventory_count += item.quantity
        db.commit()
    return RedirectResponse(f"/orders/{order_id}", status_code=303)


@router.post("/order-items/{item_id}/return", dependencies=[Depends(verify_csrf)])
def request_return(
    item_id: int,
    reason: str = Form(...),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    item = db.get(OrderItem, item_id)
    if item and item.order.customer_id == user.id and not item.return_request:
        db.add(ReturnRequest(order_item_id=item.id, reason=reason.strip()[:2000]))
        db.commit()
    return RedirectResponse(f"/orders/{item.order_id}", status_code=303)


@router.get("/messages/{store_id}")
def message_thread(store_id: int, request: Request, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    store = db.get(Store, store_id)
    if not store:
        return templates.TemplateResponse(request, "not_found.html", {"user": user}, status_code=404)
    messages = db.scalars(
        select(SellerMessage)
        .where(SellerMessage.store_id == store_id, SellerMessage.customer_id == user.id)
        .order_by(SellerMessage.created_at)
    ).all()
    return templates.TemplateResponse(
        request, "messages.html", {"user": user, "store": store, "messages": messages}
    )


@router.post("/messages/{store_id}", dependencies=[Depends(verify_csrf)])
def send_message(
    store_id: int,
    content: str = Form(...),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    content = content.strip()[:4000]
    if content:
        db.add(SellerMessage(store_id=store_id, customer_id=user.id, sender_role="customer", content=content))
        db.commit()
    return RedirectResponse(f"/messages/{store_id}", status_code=303)
