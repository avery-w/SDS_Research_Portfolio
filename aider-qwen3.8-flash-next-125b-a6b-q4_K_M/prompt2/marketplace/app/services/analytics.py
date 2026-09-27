from app.extensions import db
from app.models.order import Order
from sqlalchemy import func
from datetime import datetime

def generate_sales_report(start: str, end: str) -> dict:
    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None
    query = Order.query
    if start_dt:
        query = query.filter(Order.created_at >= start_dt)
    if end_dt:
        query = query.filter(Order.created_at <= end_dt)
    orders = query.all()
    total_revenue = sum(float(o.total_amount) for o in orders)
    total_orders = len(orders)
    by_status = {}
    for o in orders:
        by_status[o.status] = by_status.get(o.status, 0) + 1
    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "orders_by_status": by_status,
        "period": {"start": start, "end": end}
    }
