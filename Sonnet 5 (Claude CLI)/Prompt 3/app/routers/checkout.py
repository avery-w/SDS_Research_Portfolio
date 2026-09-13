from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_customer, verify_csrf
from app.models import Order, OrderItem, OrderStatus, User
from app.services.shipping import get_shipping_rates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _cart_shipping_totals(user: User):
    items = user.cart.items if user.cart else []
    total_weight_lb = sum((float(i.product.weight_oz) / 16.0) * i.quantity for i in items)
    # ponytail: uses the largest single item's box dimensions as a stand-in for a
    # combined package. Upgrade path: real box-packing/dim-weight calc if orders
    # regularly mix many large items.
    biggest = max(items, key=lambda i: float(i.product.length_in) * float(i.product.width_in) * float(i.product.height_in), default=None)
    dims = (
        (float(biggest.product.length_in), float(biggest.product.width_in), float(biggest.product.height_in))
        if biggest
        else (10.0, 6.0, 4.0)
    )
    return items, total_weight_lb, dims


@router.get("/checkout")
def checkout_form(request: Request, user: User = Depends(require_customer)):
    items = user.cart.items if user.cart else []
    if not items:
        return RedirectResponse("/cart", status_code=303)
    subtotal_cents = sum(i.quantity * i.product.price_cents for i in items)
    return templates.TemplateResponse(
        request, "checkout.html", {"user": user, "items": items, "subtotal_cents": subtotal_cents, "rates": None}
    )


@router.post("/checkout/rates", dependencies=[Depends(verify_csrf)])
def checkout_rates(
    request: Request,
    shipping_name: str = Form(...),
    shipping_address1: str = Form(...),
    shipping_city: str = Form(...),
    shipping_state: str = Form(...),
    shipping_zip: str = Form(...),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    items, weight_lb, (length, width, height) = _cart_shipping_totals(user)
    if not items:
        return RedirectResponse("/cart", status_code=303)
    subtotal_cents = sum(i.quantity * i.product.price_cents for i in items)

    rates = get_shipping_rates(
        to_name=shipping_name,
        to_address1=shipping_address1,
        to_city=shipping_city,
        to_state=shipping_state.upper(),
        to_zip=shipping_zip,
        weight_lb=weight_lb,
        length_in=length,
        width_in=width,
        height_in=height,
    )
    address = {
        "shipping_name": shipping_name,
        "shipping_address1": shipping_address1,
        "shipping_city": shipping_city,
        "shipping_state": shipping_state.upper(),
        "shipping_zip": shipping_zip,
    }
    return templates.TemplateResponse(
        request,
        "checkout.html",
        {"user": user, "items": items, "subtotal_cents": subtotal_cents, "rates": rates, "address": address},
    )


@router.post("/checkout/place", dependencies=[Depends(verify_csrf)])
def place_order(
    request: Request,
    shipping_name: str = Form(...),
    shipping_address1: str = Form(...),
    shipping_city: str = Form(...),
    shipping_state: str = Form(...),
    shipping_zip: str = Form(...),
    ups_service_code: str = Form(...),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    items, weight_lb, (length, width, height) = _cart_shipping_totals(user)
    if not items:
        return RedirectResponse("/cart", status_code=303)

    # Recompute price and shipping server-side; never trust client-submitted amounts.
    for item in items:
        if item.quantity > item.product.inventory_count:
            return templates.TemplateResponse(
                request,
                "checkout.html",
                {
                    "user": user,
                    "items": items,
                    "subtotal_cents": sum(i.quantity * i.product.price_cents for i in items),
                    "rates": None,
                    "error": f'"{item.product.name}" no longer has enough stock.',
                },
                status_code=409,
            )

    subtotal_cents = sum(i.quantity * i.product.price_cents for i in items)
    rates = get_shipping_rates(
        to_name=shipping_name,
        to_address1=shipping_address1,
        to_city=shipping_city,
        to_state=shipping_state.upper(),
        to_zip=shipping_zip,
        weight_lb=weight_lb,
        length_in=length,
        width_in=width,
        height_in=height,
    )
    chosen = next((r for r in rates if r["code"] == ups_service_code), rates[0])

    order = Order(
        customer_id=user.id,
        status=OrderStatus.paid,  # ponytail: payment processor integration is out of scope; treated as prepaid.
        shipping_name=shipping_name,
        shipping_address1=shipping_address1,
        shipping_city=shipping_city,
        shipping_state=shipping_state.upper(),
        shipping_zip=shipping_zip,
        subtotal_cents=subtotal_cents,
        shipping_cents=chosen["cost_cents"],
        total_cents=subtotal_cents + chosen["cost_cents"],
        ups_service_code=chosen["code"],
    )
    db.add(order)
    db.flush()

    for item in items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                store_id=item.product.store_id,
                quantity=item.quantity,
                unit_price_cents=item.product.price_cents,
            )
        )
        item.product.inventory_count -= item.quantity
        db.delete(item)

    db.commit()
    return RedirectResponse(f"/orders/{order.id}", status_code=303)
