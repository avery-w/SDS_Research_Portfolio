from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_customer
from ..models import CartItem, Order, OrderItem, Product, User, OrderStatus, ItemStatus, ReturnRequest, ReturnStatus
from ..schemas import (
    ShippingQuoteRequest, ShippingOption, CheckoutRequest, OrderOut, OrderItemOut,
    ReturnRequestCreate, ReturnRequestOut,
)
from ..shipping import quote_all_services, quote_service, InvalidShippingInput

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _cart_or_400(db: Session, user: User) -> list[CartItem]:
    items = db.query(CartItem).options(joinedload(CartItem.product)).filter(CartItem.user_id == user.id).all()
    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your cart is empty")
    return items


def _to_order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id, status=order.status, ship_name=order.ship_name, ship_street=order.ship_street,
        ship_city=order.ship_city, ship_state=order.ship_state, ship_zip=order.ship_zip,
        shipping_service=order.shipping_service, shipping_cost_cents=order.shipping_cost_cents,
        subtotal_cents=order.subtotal_cents, total_cents=order.total_cents, created_at=order.created_at,
        items=[
            OrderItemOut(
                id=i.id, product_id=i.product_id, product_name=i.product.name, store_id=i.store_id,
                quantity=i.quantity, unit_price_cents=i.unit_price_cents, status=i.status,
            )
            for i in order.items
        ],
    )


@router.post("/shipping-quote", response_model=list[ShippingOption])
def shipping_quote(payload: ShippingQuoteRequest, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    items = _cart_or_400(db, user)
    total_weight_oz = sum(i.product.weight_oz * i.quantity for i in items)
    box = max(items, key=lambda i: i.product.length_in * i.product.width_in * i.product.height_in).product
    try:
        return quote_all_services(payload.dest_zip, total_weight_oz, box.length_in, box.width_in, box.height_in)
    except InvalidShippingInput as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/checkout", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def checkout(payload: CheckoutRequest, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    items = _cart_or_400(db, user)

    for i in items:
        if not i.product.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{i.product.name}' is no longer available")
        if i.product.stock_qty < i.quantity:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Only {i.product.stock_qty} left of '{i.product.name}'")

    total_weight_oz = sum(i.product.weight_oz * i.quantity for i in items)
    box = max(items, key=lambda i: i.product.length_in * i.product.width_in * i.product.height_in).product
    try:
        shipping = quote_service(payload.ship_zip, payload.shipping_service, total_weight_oz, box.length_in, box.width_in, box.height_in)
    except InvalidShippingInput as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    subtotal_cents = sum(i.product.price_cents * i.quantity for i in items)
    order = Order(
        customer_id=user.id, status=OrderStatus.paid,
        ship_name=payload.ship_name, ship_street=payload.ship_street, ship_city=payload.ship_city,
        ship_state=payload.ship_state.upper(), ship_zip=payload.ship_zip,
        shipping_service=shipping.service, shipping_cost_cents=shipping.cost_cents,
        subtotal_cents=subtotal_cents, total_cents=subtotal_cents + shipping.cost_cents,
    )
    db.add(order)
    db.flush()

    for i in items:
        db.add(OrderItem(
            order_id=order.id, product_id=i.product_id, store_id=i.product.store_id,
            quantity=i.quantity, unit_price_cents=i.product.price_cents,
        ))
        i.product.stock_qty -= i.quantity
        db.delete(i)

    db.commit()
    db.refresh(order)
    return _to_order_out(order)


@router.get("", response_model=list[OrderOut])
def order_history(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.customer_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_to_order_out(o) for o in orders]


def _get_own_order(db: Session, user: User, order_id: int) -> Order:
    order = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.id == order_id)
        .first()
    )
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    if order.customer_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This order does not belong to you")
    return order


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    return _to_order_out(_get_own_order(db, user, order_id))


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    order = _get_own_order(db, user, order_id)
    if any(i.status != ItemStatus.pending for i in order.items):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order can no longer be cancelled, one or more items are already being fulfilled")

    for i in order.items:
        i.status = ItemStatus.cancelled
        i.product.stock_qty += i.quantity
    order.status = OrderStatus.cancelled
    db.commit()
    db.refresh(order)
    return _to_order_out(order)


@router.post("/returns", response_model=ReturnRequestOut, status_code=status.HTTP_201_CREATED)
def request_return(payload: ReturnRequestCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    item = (
        db.query(OrderItem)
        .join(Order)
        .filter(OrderItem.id == payload.order_item_id, Order.customer_id == user.id)
        .first()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order item not found")
    if item.status not in (ItemStatus.fulfilled, ItemStatus.shipped, ItemStatus.delivered):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This item isn't eligible for a return yet")
    if item.return_request is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A return request already exists for this item")

    ret = ReturnRequest(order_item_id=item.id, reason=payload.reason)
    item.status = ItemStatus.return_requested
    db.add(ret)
    db.commit()
    db.refresh(ret)
    return ret


@router.get("/returns/mine", response_model=list[ReturnRequestOut])
def my_returns(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    return (
        db.query(ReturnRequest)
        .join(OrderItem)
        .join(Order)
        .filter(Order.customer_id == user.id)
        .all()
    )
