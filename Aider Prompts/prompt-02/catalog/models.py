from django.db import models
from django.conf import settings
from stores.models import Store
from uuid import uuid4

def product_image_upload_to(instance, filename):
    return f'products/{instance.product_id}/{uuid4().hex}.jpg'

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    price_cents = models.PositiveIntegerField()
    weight_oz = models.PositiveIntegerField(default=0)  # for shipping
    length_in = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    width_in = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    height_in = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=product_image_upload_to)
    alt_text = models.CharField(max_length=200, blank=True)

class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory')
    sku = models.CharField(max_length=64, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=2)
