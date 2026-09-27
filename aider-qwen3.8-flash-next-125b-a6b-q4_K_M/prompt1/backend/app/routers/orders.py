import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.schemas.order import CheckoutRequest, OrderResponse
from app.utils.security import get_current_user, require_role
from app.services.shipping_service import ShippingService

router = APIRouter(prefix="/api/orders", tags=["orders"])
shipping_service = ShippingService()


@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not request.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    product_ids = [item.product_id for item in request.items]
    result = await db.execute(select(Product).where(Product.id.in_(product_ids), Product.is_active == True))
    products = {p.id: p for p in result.scalars().all()}

    for item in request.items:
        if item.product_id not in products:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        if products[item.product_id].stock_quantity < item.quantity:
            raise HTTPException(status_code=409, detail="Insufficient stock")

    subtotal = sum(products[item.product_id].price * item.quantity for item in request.items)
    total_weight = sum(products[item.product_id].weight_oz or 16 for item in request.items)

    try:
        shipping = await shipping_service.calculate_shipping(
            destination_zip=request.shipping_address.zip,
            weight_oz=total_weight,
        )
        shipping_cost = shipping["cost"]
    except Exception:
        shipping_cost = shipping_service.calculate_fallback_rate(total_weight, request.shipping_address.zip)

    tax = round(subtotal * 0.0825, 2)
    total = round(subtotal + shipping_cost + tax, 2)

    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:12].upper()}",
        status=OrderStatus.CONFIRMED,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=tax,
        total=total,
        shipping_address=request.shipping_address.model_dump(),
        billing_address=request.billing_address.model_dump() if request.billing_address else None,
        customer_id=current_user.id,
    )
    db.add(order)
    await db.flush()

    for item in request.items:
        product = products[item.product_id]
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=product.price,
            total_price=round(product.price * item.quantity, 2),
        )
        db.add(order_item)
        product.stock_quantity -= item.quantity

    await db.flush()
    await db.refresh(order)
    return order


@router.get("/my", response_model=list[OrderResponse])
async def my_orders(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Order).where(Order.customer_id == current_user.id).offset(offset).limit(per_page)
    )
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    return order


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    if order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
        raise HTTPException(status_code=400, detail="Order cannot be cancelled at this stage")
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = reason
    await db.flush()
    return {"message": "Order cancelled", "order_id": order.id}


@router.post("/{order_id}/return")
async def request_return(
    order_id: int,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Only delivered orders can be returned")
    order.status = OrderStatus.RETURN_REQUESTED
    order.return_reason = reason
    await db.flush()
    return {"message": "Return requested", "order_id": order.id}


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    current_user: User = Depends(require_role(UserRole.SELLER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = new_status
    await db.flush()
    return {"message": "Status updated", "order_id": order.id, "status": new_status}
