"""Store model owned by sellers."""
from django.conf import settings
from django.db import models


class Store(models.Model):
    """A seller-owned store on the marketplace."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="store_logos/", blank=True, null=True)
    banner = models.ImageField(upload_to="store_banners/", blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=40, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=40, default="US")
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name
