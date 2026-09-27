import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.order import Order, OrderItem, OrderStatus
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.store import Store


async def create_order_from_cart(db: AsyncSession, user_id: uuid.UUID, shipping_address: dict, shipping_method: str | None) -> Order:
    cart_result = await db.execute(select(Cart).where(Cart.user_id == user_id))
    cart = cart_result.scalar_one_or_none()
    if not cart:
        raise ValueError("Cart is empty")

    items_result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    cart_items = items_result.scalars().all()
    if not cart_items:
        raise ValueError("Cart is empty")

    subtotal = Decimal("0")
    order_items = []
    store_id = None
    for ci in cart_items:
        prod_result = await db.execute(select(Product).where(Product.id == ci.product_id))
        product = prod_result.scalar_one_or_none()
        if not product:
            continue
        store_id = product.store_id
        line_total = product.price * ci.quantity
        subtotal += line_total
        order_items.append(OrderItem(
            product_id=product.id,
            variant_id=ci.variant_id,
            quantity=ci.quantity,
            unit_price=product.price,
            subtotal=line_total,
        ))

    if not store_id:
        raise ValueError("No valid products in cart")

    tax = subtotal * Decimal("0.08")
    total = subtotal + tax

    order = Order(
        customer_id=user_id,
        store_id=store_id,
        status=OrderStatus.pending,
        shipping_address=shipping_address,
        shipping_method=shipping_method,
        shipping_cost=Decimal("0"),
        subtotal=subtotal,
        tax=tax,
        total=total,
    )
    db.add(order)
    await db.flush()

    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)

    # Clear cart
    for ci in cart_items:
        await db.delete(ci)
    await db.delete(cart)

    await db.flush()
    return order
