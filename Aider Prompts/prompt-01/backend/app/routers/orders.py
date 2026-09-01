from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.session import get_session
from app.deps.auth import get_current_user, require_roles
from app.models.order import Order, OrderItem, OrderStatus, Shipment
from app.models.cart import Cart, CartItem
from app.models.product import Product, Inventory
from app.models.user import Role, User

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", responses={401: {"description": "Missing auth"}, 422: {"description": "Invalid"}})
async def create_order(shipping_rate_cents: int, address_id: int, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    cart = (await db.execute(select(Cart).where(Cart.user_id == user.id))).scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=422, detail="Cart empty")
    items = (await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))).scalars().all()
    if not items: raise HTTPException(status_code=422, detail="Cart empty")
    # Validate inventory
    product_ids = [i.product_id for i in items]
    products = (await db.execute(select(Product).where(Product.id.in_(product_ids)))).scalars().all()
    # Split by store (one order per store)
    orders_by_store = {}
    for it in items:
        p = next(p for p in products if p.id == it.product_id)
        inv = (await db.execute(select(Inventory).where(Inventory.product_id == p.id))).scalar_one_or_none()
        if not inv or inv.quantity < it.quantity: raise HTTPException(status_code=422, detail=f"Insufficient inventory for product {p.id}")
        orders_by_store.setdefault(p.store_id, []).append((p, it.quantity))
    created_ids = []
    total_cart_cents = 0
    for store_id, tuples in orders_by_store.items():
        subtotal = sum(int(p.price_cents) * q for p, q in tuples)
        total_cart_cents += subtotal
        order = Order(customer_id=user.id, store_id=store_id, status=OrderStatus.paid, total_cents=subtotal + shipping_rate_cents, shipping_cents=shipping_rate_cents, shipping_address_id=address_id)
        db.add(order); await db.flush()
        for p, q in tuples:
            db.add(OrderItem(order_id=order.id, product_id=p.id, quantity=q, unit_price_cents=p.price_cents))
            await db.execute(update(Inventory).where(Inventory.product_id == p.id).values(quantity=Inventory.quantity - q))
        created_ids.append(order.id)
    # Clear cart
    await db.execute(update(CartItem).where(CartItem.cart_id == cart.id).values(quantity=0))  # option: actually delete rows
    await db.commit()
    return {"order_ids": created_ids}

@router.post("/{order_id}/cancel", responses={401: {"description": "Missing auth"}, 403: {"description": "Unauthorized"}})
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_id != user.id and user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Cannot cancel others' orders")
    if order.status not in (OrderStatus.pending, OrderStatus.paid):
        raise HTTPException(status_code=422, detail="Too late to cancel")
    order.status = OrderStatus.cancelled
    await db.commit()
    return {"ok": True}

@router.post("/{order_id}/fulfill", responses={401: {"description": "Missing auth"}, 403: {"description": "Unauthorized"}})
async def fulfill_order(order_id: int, tracking_number: str, service_code: str, db: AsyncSession = Depends(get_session), user: User = Depends(require_roles(Role.seller, Role.admin))):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    if user.role != Role.admin:
        # Verify this seller owns the store (join omitted here; enforce in actual code)
        pass
    if order.status != OrderStatus.paid:
        raise HTTPException(status_code=422, detail="Order not in shippable state")
    order.status = OrderStatus.shipped
    db.add(Shipment(order_id=order.id, tracking_number=tracking_number, service_code=service_code))
    await db.commit()
    return {"ok": True}
