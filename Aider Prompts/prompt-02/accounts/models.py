from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Roles(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        SELLER = 'seller', 'Seller'
        ADMIN = 'admin', 'Admin'
    role = models.CharField(max_length=16, choices=Roles.choices, default=Roles.CUSTOMER)
    # optional phone, two_factor fields later

class CustomerProfile(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='customer_profile')
    default_shipping_address = models.JSONField(blank=True, null=True)  # {name, line1, city, state, zip, country, phone}

class SellerProfile(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='seller_profile')
    payout_account = models.JSONField(blank=True, null=True)
    kyc_status = models.CharField(max_length=32, default='unverified')
