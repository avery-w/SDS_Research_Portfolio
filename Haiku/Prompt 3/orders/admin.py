from django.contrib import admin
from .models import Order, OrderItem, ReturnRequest, CancellationRequest, ShippingRate

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'status', 'total_price', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'customer__email', 'tracking_number')
    readonly_fields = ('order_number', 'created_at')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'store', 'quantity', 'price_at_purchase')
    search_fields = ('order__order_number', 'product__name')

@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'reason', 'status', 'refund_amount', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('order__order_number',)

@admin.register(CancellationRequest)
class CancellationRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'refund_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number',)

@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ('carrier', 'service_type', 'base_rate', 'is_active')
    list_filter = ('is_active', 'carrier')
