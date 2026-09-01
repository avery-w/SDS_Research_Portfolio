from django.db import transaction
from .models import Order, OrderItem
from catalog.models import Inventory

@transaction.atomic
def create_order_from_cart(cart, store, shipping_address, shipping_cents, tax_cents):
    items = list(cart.items.select_related('product'))
    subtotal = sum(i.product.price_cents * i.quantity for i in items)
    order = Order.objects.create(
        customer=cart.user, store=store, subtotal_cents=subtotal,
        shipping_cents=shipping_cents, tax_cents=tax_cents,
        total_cents=subtotal + shipping_cents + tax_cents,
        shipping_address=shipping_address
    )
    for i in items:
        OrderItem.objects.create(order=order, product=i.product, title_snapshot=i.product.title, price_cents=i.product.price_cents, quantity=i.quantity)
        inv = Inventory.objects.select_for_update().get(product=i.product)
        if inv.quantity < i.quantity: raise ValueError('Insufficient stock')
        inv.quantity -= i.quantity; inv.save()
    cart.items.all().delete()
    return order
