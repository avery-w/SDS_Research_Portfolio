from decimal import Decimal
from django.db import transaction
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
from .models import Order, OrderItem, Shipment

@transaction.atomic
def reserve_and_create_order(user, cart, shipping):
    subtotal = Decimal("0.00")
    for item in cart.items.select_for_update().select_related("product__inventory", "product__store"):
        inv = getattr(item.product, "inventory", None)
        if inv:
            if (inv.quantity - inv.reserved) < item.quantity and not inv.allow_backorder:
                raise ValidationError(f"Insufficient stock for product {item.product_id}")
            inv.reserved += item.quantity
            inv.save(update_fields=["reserved"])
        subtotal += (item.price_snapshot or item.product.price) * item.quantity

    number = get_random_string(12).upper()
    order = Order.objects.create(
        number=number,
        user=user,
        status=Order.PENDING,
        subtotal=subtotal,
        shipping_total=Decimal(str(shipping.get("cost", "0"))),
        tax_total=Decimal("0.00"),
        grand_total=subtotal + Decimal(str(shipping.get("cost", "0"))),
        ship_to_name=shipping.get("name", ""),
        ship_to_address1=shipping.get("address1", ""),
        ship_to_address2=shipping.get("address2", ""),
        ship_to_city=shipping.get("city", ""),
        ship_to_state=shipping.get("state", ""),
        ship_to_postal=shipping.get("postal", ""),
        ship_to_country=shipping.get("country", "US"),
    )

    for item in cart.items.select_related("product__store"):
        OrderItem.objects.create(
            order=order,
            store=item.product.store,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.price_snapshot or item.product.price,
            total_price=(item.price_snapshot or item.product.price) * item.quantity,
        )

    Shipment.objects.create(
        order=order,
        carrier=shipping.get("carrier", "UPS"),
        service=shipping.get("service", ""),
        cost=Decimal(str(shipping.get("cost", "0"))),
        status="pending",
    )

    cart.items.all().delete()
    return order

def cancel_order(user, order: Order):
    if order.status not in [Order.PENDING, Order.PAID, Order.FULFILLING]:
        raise ValidationError("Cannot cancel at this stage.")
    order.status = Order.CANCELLED
    order.save(update_fields=["status"])
    # release inventory
    for oi in order.items.select_related("product__inventory"):
        inv = getattr(oi.product, "inventory", None)
        if inv:
            inv.reserved = max(0, inv.reserved - oi.quantity)
            inv.save(update_fields=["reserved"])
    return order

def request_return(user, order_item, reason: str):
    from .models import ReturnRequest
    if order_item.order.user_id != user.id:
        raise ValidationError("Not your order item")
    return ReturnRequest.objects.create(order=order_item.order, item=order_item, user=user, reason=reason)
