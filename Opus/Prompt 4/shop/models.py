import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(self, *args, **kwargs):
        kwargs.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(*args, **kwargs)


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer"
        SELLER = "seller"
        ADMIN = "admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    objects = UserManager()

    def save(self, *args, **kwargs):
        # Role is the single source of truth for Django admin access.
        self.is_staff = self.is_superuser = self.role == self.Role.ADMIN
        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    """Singleton (pk=1) for platform settings editable in the admin."""

    site_name = models.CharField(max_length=100, default="Marketplace")
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"))
    allow_seller_signup = models.BooleanField(default=True)
    chatbot_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return "Site settings"


class Store(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="store")
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, max_length=5000)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(is_active=True, store__is_active=True, store__owner__is_active=True)


class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True, max_length=10000)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    stock = models.PositiveIntegerField(default=0)
    weight_lb = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    length_in = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0.1"))])
    width_in = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0.1"))])
    height_in = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0.1"))])
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0), name="product_price_positive")]

    def __str__(self):
        return self.name


def image_path(instance, filename):
    # Never trust the client filename.
    return f"products/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def validate_image_size(f):
    if f.size > settings.MAX_IMAGE_BYTES:
        raise ValidationError("Image must be 5 MB or smaller.")


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to=image_path,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_image_size],
    )
    created = models.DateTimeField(auto_now_add=True)


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_cart_line")]


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed"
        SHIPPED = "shipped"
        DELIVERED = "delivered"
        CANCELLED = "cancelled"
        RETURN_REQUESTED = "return_requested"
        RETURNED = "returned"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED, db_index=True)
    ship_name = models.CharField(max_length=120)
    ship_line1 = models.CharField(max_length=200)
    ship_city = models.CharField(max_length=100)
    ship_state = models.CharField(max_length=2)
    ship_zip = models.CharField(max_length=10)
    shipping_service = models.CharField(max_length=40)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    tracking_number = models.CharField(max_length=40, blank=True)
    return_reason = models.TextField(blank=True, max_length=2000)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=200)  # snapshot at purchase time
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    body = models.TextField(max_length=2000)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created"]
