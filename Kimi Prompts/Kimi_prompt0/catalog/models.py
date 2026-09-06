"""Catalog models: categories, products, images and inventory."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    """Product category, optionally nested under a parent category."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """A sellable product belonging to a store."""

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=64, blank=True)
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    compare_at_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default="USD")
    # Weight in ounces and dimensions in inches are used by the shipping
    # rate calculator (UPS guidelines).
    weight_oz = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    length_in = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    width_in = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    height_in = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "is_active"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def main_image(self):
        image = self.images.filter(is_primary=True).first()
        if image:
            return image.image.url
        return ""


class ProductImage(models.Model):
    """An image attached to a product."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"Image for {self.product.name}"


class Inventory(models.Model):
    """Inventory tracking for a single product."""

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="inventory"
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def available(self) -> int:
        return max(self.quantity - self.reserved, 0)

    def __str__(self) -> str:
        return f"Inventory for {self.product.name}"


class InventoryLog(models.Model):
    """An audit trail of inventory changes."""

    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE, related_name="logs"
    )
    quantity_change = models.IntegerField()
    reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.quantity_change:+d} @ {self.created_at:%Y-%m-%d %H:%M}"
