"""Admin configuration for the catalog app."""
from django.contrib import admin

from .models import Category, Inventory, InventoryLog, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "store",
        "category",
        "price",
        "stock_quantity",
        "is_active",
        "is_featured",
    )
    list_filter = ("is_active", "is_featured", "store", "category")
    search_fields = ("name", "sku", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, InventoryInline]


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = (
        "inventory",
        "quantity_change",
        "reason",
        "created_by",
        "created_at",
    )
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
