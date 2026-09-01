from decimal import Decimal
from datetime import date, timedelta
from celery import shared_task
from django.db.models import Sum, Count, Avg
from orders.models import Order
from accounts.models import User
from .models import DailyMetrics

@shared_task
def compute_daily_metrics():
    d = date.today() - timedelta(days=1)
    qs = Order.objects.filter(created_at__date=d)
    total_orders = qs.count()
    gmv = qs.aggregate(s=Sum("grand_total"))["s"] or Decimal("0.00")
    aov = (gmv / total_orders) if total_orders else Decimal("0.00")
    new_customers = User.objects.filter(date_joined__date=d).count()
    DailyMetrics.objects.update_or_create(
        date=d,
        defaults={"total_orders": total_orders, "total_gmv": gmv, "avg_order_value": aov, "new_customers": new_customers},
    )
