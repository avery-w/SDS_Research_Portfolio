from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_active_user
from app.services.shipping import calculate_shipping_rate
from app.services.payment import process_payment
from datetime import datetime

router = APIRouter(prefix="/checkout", tags=["checkout"])

@router.post("/shipping-rate", response_model=schemas.ShippingRateResponse)
def get_shipping_rate(
    request: schemas.ShippingRateRequest,
    db: Session = Depends(get_db)
):
    rate = calculate_shipping_rate(request.destination_zip, request.weight_oz)
    return rate

@router.post("/create-order", response_model=schemas.Order)
def create_order(
    checkout: schemas.CheckoutRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    address = db.query(models.Address).filter(
        models.Address.id == checkout.shipping_address_id,
        models.Address.user_id == current_user.id
    ).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    group_by_store = {}
    total_weight = 0
    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product or not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} is unavailable")

        if product.quantity_available < item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough inventory for {product.name}")

        store_id = product.store_id
        if store_id not in group_by_store:
            group_by_store[store_id] = []
        group_by_store[store_id].append((product, item.quantity))
        total_weight += product.weight_oz * item.quantity

    shipping_rate = calculate_shipping_rate(address.zip_code, total_weight)
    shipping_cost = shipping_rate.get("rate", 0)

    orders = []
    for store_id, items in group_by_store.items():
        order_total = sum(product.price * qty for product, qty in items)
        order_total += shipping_cost

        order = models.Order(
            customer_id=current_user.id,
            store_id=store_id,
            status=models.OrderStatus.PENDING,
            total_amount=order_total,
            shipping_cost=shipping_cost,
            shipping_address_id=address.id,
            stripe_payment_id=None
        )
        db.add(order)
        db.flush()

        for product, qty in items:
            order_item = models.OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                price_at_purchase=product.price
            )
            db.add(order_item)
            product.quantity_available -= qty

        orders.append(order)

    db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete()
    db.commit()

    for order in orders:
        db.refresh(order)

    return orders[0] if len(orders) == 1 else orders

@router.post("/process-payment")
def process_checkout_payment(
    order_id: int,
    payment_method_id: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if order.status != models.OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order already processed")

    payment_result = process_payment(order.total_amount, payment_method_id)
    if not payment_result.get("success"):
        raise HTTPException(status_code=400, detail="Payment failed: " + payment_result.get("error", "Unknown error"))

    order.stripe_payment_id = payment_result.get("payment_id")
    order.status = models.OrderStatus.PAID
    db.commit()
    db.refresh(order)

    return {"message": "Payment successful", "order": order}
