from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from app import db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole

class AnalyticsService:

    @staticmethod
    def platform_overview():
        total_users = User.query.count()
        total_sellers = User.query.filter_by(role=UserRole.SELLER).count()
        total_customers = User.query.filter_by(role=UserRole.CUSTOMER).count()
        total_products = Product.query.count()
        total_orders = Order.query.count()
        total_revenue = db.session.query(func.sum(Order.total)).scalar() or 0
        return {
            "total_users": total_users,
            "total_sellers": total_sellers,
            "total_customers": total_customers,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
        }

    @staticmethod
    def sales_by_period(days=30):
        since = datetime.now(timezone.utc) - timedelta(days=days)
        orders = Order.query.filter(Order.created_at >= since).all()
        daily = {}
        for o in orders:
            key = o.created_at.strftime("%Y-%m-%d")
            daily[key] = daily.get(key, 0) + float(o.total)
        return daily

    @staticmethod
    def top_selling_products(limit=10):
        results = (
            db.session.query(
                Product.name,
                func.sum(OrderItem.quantity).label("total_qty"),
                func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_rev"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .group_by(Product.id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
            .all()
        )
        return [
            {"name": r.name, "quantity": int(r.total_qty), "revenue": float(r.total_rev)}
            for r in results
        ]

    @staticmethod
    def order_status_breakdown():
        results = (
            db.session.query(Order.status, func.count(Order.id))
            .group_by(Order.status)
            .all()
        )
        return {status: int(count) for status, count in results}
