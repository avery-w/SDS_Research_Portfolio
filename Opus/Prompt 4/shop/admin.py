from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin

from .models import Message, Order, OrderItem, Product, ProductImage, SiteSettings, Store, User
from .views import RESTOCK, transition

admin.site.site_header = "Marketplace administration"


@admin.action(description="Deactivate selected")
def deactivate(modeladmin, request, queryset):
    queryset.update(is_active=False)


@admin.action(description="Activate selected")
def activate(modeladmin, request, queryset):
    queryset.update(is_active=True)


@admin.register(User)
class MarketUserAdmin(UserAdmin):
    list_display = ["username", "email", "role", "is_active", "date_joined"]
    list_filter = ["role", "is_active"]
    fieldsets = UserAdmin.fieldsets + (("Marketplace", {"fields": ["role"]}),)
    actions = [deactivate, activate]


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "is_active", "created"]
    list_filter = ["is_active"]
    search_fields = ["name", "owner__username", "owner__email"]
    raw_id_fields = ["owner"]
    actions = [deactivate, activate]


class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "store", "price", "stock", "is_active", "updated"]
    list_filter = ["is_active", "store"]
    search_fields = ["name", "store__name"]
    inlines = [ImageInline]
    actions = [deactivate, activate]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "product_name", "unit_price", "quantity"]
    can_delete = False


def force(to):
    @admin.action(description=f"Force status: {to.label}" + (" (restock)" if to in RESTOCK else ""))
    def action(modeladmin, request, queryset):
        done = sum(transition(Order.objects, o.pk, [s for s in Order.Status if s not in RESTOCK], to) for o in queryset)
        messages.info(request, f"Updated {done} order(s).")
    action.__name__ = f"force_{to}"
    return action


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "store", "status", "total", "created"]
    list_filter = ["status", "store"]
    search_fields = ["id", "customer__username", "customer__email", "tracking_number"]
    readonly_fields = ["status", "customer", "store", "subtotal", "shipping_cost", "total", "created", "updated"]
    inlines = [OrderItemInline]
    actions = [force(s) for s in Order.Status]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["sender", "recipient", "created", "read"]
    search_fields = ["sender__username", "recipient__username", "body"]
    raw_id_fields = ["sender", "recipient", "product", "order"]


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
