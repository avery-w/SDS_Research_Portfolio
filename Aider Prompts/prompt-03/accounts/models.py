from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CUSTOMER = "customer"
    ROLE_SELLER = "seller"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [
        (ROLE_CUSTOMER, "Customer"),
        (ROLE_SELLER, "Seller"),
        (ROLE_ADMIN, "Admin"),
    ]

    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    phone = models.CharField(max_length=32, blank=True)
    email_verified = models.BooleanField(default=False)
