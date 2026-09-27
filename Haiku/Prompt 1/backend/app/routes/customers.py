from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    User, Cart, CartItem, Product, Order, OrderItem, Address,
    Return, ReturnStatus, OrderStatus, Message
)
from app.schemas import (
    AddressCreate, AddressResponse, CartResponse, CartItemCreate,
    OrderCreate, OrderResponse, ReturnCreate, ReturnResponse, MessageCreate, MessageResponse
)
from app.auth import get_current_customer
from decimal import Decimal

router = APIRouter(prefix="/customers", tags=["customers"])

# Address Management
@router.post("/addresses", response_model=AddressResponse)
def create_address(
    address_data: AddressCreate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    address = Address(
        user_id=current_user.id,
        street=address_data.street,
        city=address_data.city,
        state=address_data.state,
        zip_code=address_data.zip_code,
        is_default=address_data.is_default
    )
    db.add(address)
    db.commit()
    db.refresh(address)
    return address

@router.get("/addresses", response_model=list[AddressResponse])
def list_addresses(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    addresses = db.query(Address).filter(Address.user_id == current_user.id).all()
    return addresses

# Cart Management
@router.get("/cart", response_model=CartResponse)
def get_cart(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart

@router.post("/cart/items", response_model=CartResponse)
def add_to_cart(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        db.commit()

    product = db.query(Product).filter(Product.id == item_data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == item_data.product_id
    ).first()

    if cart_item:
        cart_item.quantity += item_data.quantity
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity
        )
        db.add(cart_item)

    db.commit()
    db.refresh(cart)
    return cart

@router.delete("/cart/items/{item_id}")
def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(item)
    db.commit()
    return {"message": "Item removed from cart"}

# Checkout and Orders
@router.post("/checkout", response_model=OrderResponse)
def checkout(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total_amount = Decimal(0)
    for item in cart.items:
        total_amount += item.product.price * item.quantity

    shipping_cost = Decimal("5.00")
    total_amount += shipping_cost

    order = Order(
        customer_id=current_user.id,
        total_amount=total_amount,
        shipping_cost=shipping_cost,
        shipping_method=order_data.shipping_method,
        delivery_address_id=order_data.delivery_address_id,
        payment_method=order_data.payment_method,
        status=OrderStatus.PENDING,
        transaction_id="TXN-" + str(current_user.id) + "-" + str(int(__import__('time').time()))
    )
    db.add(order)
    db.flush()

    for cart_item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price_at_purchase=cart_item.product.price,
            seller_id=cart_item.product.store.owner_id
        )
        db.add(order_item)
        cart_item.product.stock -= cart_item.quantity

    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    db.refresh(order)
    return order

@router.get("/orders", response_model=list[OrderResponse])
def list_orders(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).filter(Order.customer_id == current_user.id).all()
    return orders

@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
        raise HTTPException(status_code=400, detail="Cannot cancel this order")

    order.status = OrderStatus.CANCELLED
    for item in order.items:
        item.product.stock += item.quantity

    db.commit()
    return {"message": "Order cancelled"}

# Returns
@router.post("/returns", response_model=ReturnResponse)
def request_return(
    return_data: ReturnCreate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    order_item = db.query(OrderItem).filter(
        OrderItem.product_id == return_data.product_id
    ).first()
    if not order_item:
        raise HTTPException(status_code=404, detail="Order item not found")

    return_request = Return(
        order_id=order_item.order_id,
        product_id=return_data.product_id,
        reason=return_data.reason,
        refund_amount=order_item.price_at_purchase,
        status=ReturnStatus.INITIATED
    )
    db.add(return_request)
    db.commit()
    db.refresh(return_request)
    return return_request

@router.get("/returns")
def list_returns(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    returns = db.query(Return).join(
        OrderItem, Return.product_id == OrderItem.product_id
    ).filter(
        OrderItem.product_id == Return.product_id
    ).all()
    return returns

# Messaging
@router.post("/messages", response_model=MessageResponse)
def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    message = Message(
        sender_id=current_user.id,
        recipient_id=message_data.recipient_id,
        product_id=message_data.product_id,
        content=message_data.content
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

@router.get("/messages")
def get_messages(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    messages = db.query(Message).filter(
        (Message.sender_id == current_user.id) |
        (Message.recipient_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()
    return messages
