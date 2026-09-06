"""Admin configuration for the accounts app."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin panel for marketplace users."""

    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Marketplace", {"fields": ("role", "phone", "avatar")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Marketplace", {"fields": ("role",)}),
    )
