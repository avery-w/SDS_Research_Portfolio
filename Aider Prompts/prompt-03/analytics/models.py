from django.db import models
from django.conf import settings

class DailyMetrics(models.Model):
    date = models.DateField(unique=True)
    total_orders = models.IntegerField()
    total_gmv = models.DecimalField(max_digits=14, decimal_places=2)
    avg_order_value = models.DecimalField(max_digits=14, decimal_places=2)
    new_customers = models.IntegerField()

class AuditLog(models.Model):
    action = models.CharField(max_length=100)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    target = models.CharField(max_length=200, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ts = models.DateTimeField(auto_now_add=True)
