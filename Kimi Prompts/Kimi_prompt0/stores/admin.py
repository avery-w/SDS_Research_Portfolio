"""Admin configuration for the stores app."""
from django.contrib import admin

from .models import Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_active", "is_verified", "created_at")
    list_filter = ("is_active", "is_verified")
    search_fields = ("name", "owner__username")
    prepopulated_fields = {"slug": ("name",)}
