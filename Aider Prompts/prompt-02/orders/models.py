from django.db import models
from django.conf import settings
from catalog.models import Product
import uuid

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    store = models.ForeignKey('stores.Store', on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, default='pending')  # pending, paid, fulfilled, cancelled, returned
    subtotal_cents = models.PositiveIntegerField(default=0)
    shipping_cents = models.PositiveIntegerField(default=0)
    tax_cents = models.PositiveIntegerField(default=0)
    total_cents = models.PositiveIntegerField(default=0)
    shipping_address = models.JSONField()
    billing_address = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    title_snapshot = models.CharField(max_length=220)
    price_cents = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()

class CancellationRequest(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='cancellations')
    reason = models.TextField()
    status = models.CharField(max_length=20, default='requested')  # requested, approved, rejected
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

class ReturnRequest(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    reason = models.TextField()
    status = models.CharField(max_length=20, default='requested')  # requested, authorized, rejected, received, refunded
    created_at = models.DateTimeField(auto_now_add=True)
    rma_number = models.CharField(max_length=40, blank=True)
