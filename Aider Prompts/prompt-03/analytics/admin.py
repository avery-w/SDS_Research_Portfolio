from django.contrib import admin
from .models import DailyMetrics, AuditLog

@admin.register(DailyMetrics)
class DailyMetricsAdmin(admin.ModelAdmin):
    list_display = ("date", "total_orders", "total_gmv", "avg_order_value", "new_customers")

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "target", "ts")
