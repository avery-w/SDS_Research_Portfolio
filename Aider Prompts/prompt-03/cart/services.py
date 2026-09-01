from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from catalog.models import Product

def get_or_create_cart(user=None, session_id=""):
    cart = None
    if user and getattr(user, "is_authenticated", False):
        cart, _ = Cart.objects.get_or_create(user=user)
    elif session_id:
        cart, _ = Cart.objects.get_or_create(session_id=session_id)
    else:
        cart = Cart.objects.create()
    return cart

@transaction.atomic
def add_item(cart: Cart, product: Product, quantity: int):
    quantity = max(1, min(int(quantity or 1), 50))
    inv = getattr(product, "inventory", None)
    if inv and not inv.allow_backorder and (inv.quantity - inv.reserved) < quantity:
        raise ValueError("Insufficient stock")
    item, created = CartItem.objects.select_for_update().get_or_create(
        cart=cart, product=product, defaults={"quantity": quantity, "price_snapshot": product.price}
    )
    if not created:
        new_qty = item.quantity + quantity
        if inv and not inv.allow_backorder and (inv.quantity - inv.reserved) < new_qty:
            raise ValueError("Insufficient stock")
        item.quantity = new_qty
        item.price_snapshot = product.price
        item.save(update_fields=["quantity", "price_snapshot"])
    return item

@transaction.atomic
def update_item(cart: Cart, item_id: int, quantity: int):
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    quantity = max(1, min(int(quantity or 1), 50))
    inv = getattr(item.product, "inventory", None)
    if inv and not inv.allow_backorder and (inv.quantity - inv.reserved) < quantity:
        raise ValueError("Insufficient stock")
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item

@transaction.atomic
def remove_item(cart: Cart, item_id: int):
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item.delete()
