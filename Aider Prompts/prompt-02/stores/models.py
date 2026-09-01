from django.db import models
from django.conf import settings
import uuid

class Store(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store')
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='store_logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    return_policy = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
