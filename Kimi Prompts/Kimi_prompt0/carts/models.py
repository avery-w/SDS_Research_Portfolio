"""Shopping cart models."""
from decimal import Decimal

from django.conf import settings
from django.db import models

from catalog.models import Product


class Cart(models.Model):
    """A user's shopping cart."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Cart for {self.user.username}"

    @property
    def subtotal(self):
        return sum(
            (item.product.price * item.quantity for item in self.items.all()),
            Decimal("0"),
        )

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """A single line item in a cart."""

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product")
        ordering = ["added_at"]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product.name}"

    @property
    def line_total(self):
        return self.product.price * self.quantity
