from django.contrib import admin
from .models import Category, Product, ProductImage, Inventory

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0

class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 0

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "store", "price", "is_active", "created_at")
    inlines = [ProductImageInline, InventoryInline]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
