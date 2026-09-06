"""Custom user model with marketplace roles: customer, seller, admin."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A user of the marketplace.

    Roles:
        CUSTOMER - browses products, manages cart/orders, contacts sellers.
        SELLER   - owns a store and manages its products, inventory and orders.
        ADMIN    - manages users, stores, products, orders and platform settings.
    """

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        SELLER = "SELLER", "Seller"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
    )
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    class Meta:
        ordering = ["-date_joined"]

    @property
    def is_customer(self) -> bool:
        return self.role == self.Role.CUSTOMER

    @property
    def is_seller(self) -> bool:
        return self.role == self.Role.SELLER

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"
