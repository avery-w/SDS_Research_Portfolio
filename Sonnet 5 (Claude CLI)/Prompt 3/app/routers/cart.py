from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_customer, verify_csrf
from app.models import CartItem, Product, User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/cart")
def view_cart(request: Request, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    items = user.cart.items if user.cart else []
    subtotal_cents = sum(i.quantity * i.product.price_cents for i in items)
    return templates.TemplateResponse(
        request, "cart.html", {"user": user, "items": items, "subtotal_cents": subtotal_cents}
    )


@router.post("/cart/add", dependencies=[Depends(verify_csrf)])
def add_to_cart(
    product_id: int = Form(...),
    quantity: int = Form(1),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        return RedirectResponse("/", status_code=303)
    quantity = max(1, min(quantity, 99))

    item = next((i for i in user.cart.items if i.product_id == product_id), None)
    if item:
        item.quantity = min(item.quantity + quantity, product.inventory_count or item.quantity)
    else:
        db.add(CartItem(cart_id=user.cart.id, product_id=product_id, quantity=min(quantity, max(product.inventory_count, 1))))
    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/update", dependencies=[Depends(verify_csrf)])
def update_cart_item(
    item_id: int = Form(...),
    quantity: int = Form(...),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    item = db.get(CartItem, item_id)
    if item and item.cart.user_id == user.id:
        if quantity <= 0:
            db.delete(item)
        else:
            item.quantity = min(quantity, 99)
        db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/remove", dependencies=[Depends(verify_csrf)])
def remove_cart_item(
    item_id: int = Form(...),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    item = db.get(CartItem, item_id)
    if item and item.cart.user_id == user.id:
        db.delete(item)
        db.commit()
    return RedirectResponse("/cart", status_code=303)
