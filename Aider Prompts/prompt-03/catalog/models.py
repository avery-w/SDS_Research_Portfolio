from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    store = models.ForeignKey("stores.Store", on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    weight_lb = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    length_in = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    width_in = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    height_in = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    url = models.URLField()
    alt = models.CharField(max_length=200, blank=True)
    position = models.PositiveIntegerField(default=0)

class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    allow_backorder = models.BooleanField(default=False)
