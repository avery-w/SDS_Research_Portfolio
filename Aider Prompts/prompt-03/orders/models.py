from django.db import models
from django.conf import settings

class Order(models.Model):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    FULFILLING = "fulfilling"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PAID, "Paid"),
        (CANCELLED, "Cancelled"),
        (FULFILLING, "Fulfilling"),
        (SHIPPED, "Shipped"),
        (COMPLETED, "Completed"),
        (REFUNDED, "Refunded"),
    ]
    number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ship_to_name = models.CharField(max_length=120)
    ship_to_address1 = models.CharField(max_length=200)
    ship_to_address2 = models.CharField(max_length=200, blank=True)
    ship_to_city = models.CharField(max_length=100)
    ship_to_state = models.CharField(max_length=50)
    ship_to_postal = models.CharField(max_length=20)
    ship_to_country = models.CharField(max_length=2, default="US")
    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    store = models.ForeignKey("stores.Store", on_delete=models.PROTECT, related_name="order_items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

class Shipment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipments")
    carrier = models.CharField(max_length=40, default="UPS")
    service = models.CharField(max_length=40)
    tracking_number = models.CharField(max_length=50, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    label_url = models.URLField(blank=True)
    status = models.CharField(max_length=30, default="pending")

class ReturnRequest(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="returns")
    item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="returns")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField()
    status = models.CharField(max_length=20, default="requested")
    created_at = models.DateTimeField(auto_now_add=True)
