from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user, require_role
from ..models import User, CartItem, Order, OrderItem, Product, OrderStatus, UserRole, Message
from ..schemas import (
    ShippingRequest,
    CheckoutRequest,
    ChatRequest,
    ChatResponse,
    MessageCreate,
    MessageOut,
    OrderOut,
)
from ..shipping import calculate_shipping
from ..chatbot import get_chat_response

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/shipping/rates")
def shipping_rates(req: ShippingRequest):
    """Public endpoint – calculates approximate UPS-style rates from Austin origin."""
    return calculate_shipping(
        weight_lb=req.weight_lb,
        length_in=req.length_in,
        width_in=req.width_in,
        height_in=req.height_in,
        dest_zip=req.dest_zip,
    )


@router.post("/checkout", response_model=OrderOut)
def checkout(
    body: CheckoutRequest,
    current_user: User = Depends(require_role(UserRole.customer)),
    db: Session = Depends(get_db),
):
    cart = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user.id)
        .all()
    )
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    subtotal = 0.0
    total_weight = 0.0
    max_l = max_w = max_h = 0.0
    items_data = []

    for item in cart:
        product = item.product
        if not product or not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} is unavailable")
        if product.inventory < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient inventory for '{product.name}' (only {product.inventory} left)",
            )
        subtotal += product.price * item.quantity
        total_weight += product.weight_lb * item.quantity
        max_l = max(max_l, product.length_in)
        max_w = max(max_w, product.width_in)
        max_h = max(max_h, product.height_in)
        items_data.append((product, item.quantity))

    ship_info = calculate_shipping(
        weight_lb=total_weight,
        length_in=max_l or 10.0,
        width_in=max_w or 8.0,
        height_in=max_h or 4.0,
        dest_zip=body.shipping_zip,
    )
    shipping_cost = ship_info["shipping_cost"]
    total = round(subtotal + shipping_cost, 2)

    order = Order(
        customer_id=current_user.id,
        status=OrderStatus.paid,  # demo: assume payment succeeded
        subtotal=round(subtotal, 2),
        shipping_cost=shipping_cost,
        total=total,
        shipping_address=body.shipping_address,
        shipping_zip=body.shipping_zip,
    )
    db.add(order)
    db.flush()

    for product, qty in items_data:
        oi = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=qty,
            unit_price=product.price,
            seller_id=product.store.owner_id,
        )
        db.add(oi)
        product.inventory -= qty

    for item in cart:
        db.delete(item)

    db.commit()
    db.refresh(order)
    return order


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    reply = await get_chat_response(req.message)
    return {"reply": reply}


@router.post("/messages", response_model=MessageOut, status_code=201)
def send_message(
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    receiver = db.query(User).filter(User.id == body.receiver_id, User.is_active == True).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    msg = Message(
        sender_id=current_user.id,
        receiver_id=body.receiver_id,
        product_id=body.product_id,
        order_id=body.order_id,
        content=body.content.strip(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/messages", response_model=list[MessageOut])
def list_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msgs = (
        db.query(Message)
        .filter(
            (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
        )
        .order_by(Message.created_at.desc())
        .limit(100)
        .all()
    )
    return msgs
