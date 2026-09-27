from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole


class AnalyticsService:
    async def get_sales_summary(self, db: AsyncSession, start: datetime | None, end: datetime | None) -> dict:
        query = select(
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total).label("total_revenue"),
            func.avg(Order.total).label("avg_order_value"),
        )
        if start:
            query = query.where(Order.created_at >= start)
        if end:
            query = query.where(Order.created_at <= end)
        result = await db.execute(query)
        row = result.one()
        return {
            "total_orders": row.total_orders or 0,
            "total_revenue": float(row.total_revenue or 0),
            "avg_order_value": float(row.avg_order_value or 0),
        }

    async def get_top_products(self, db: AsyncSession, limit: int = 10) -> list[dict]:
        from app.models.order import OrderItem
        query = (
            select(
                Product.name,
                Product.id,
                func.sum(OrderItem.quantity).label("total_sold"),
                func.sum(OrderItem.total_price).label("total_revenue"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .group_by(Product.id, Product.name)
            .order_by(func.sum(OrderItem.total_price).desc())
            .limit(limit)
        )
        result = await db.execute(query)
        return [
            {"product_id": r.id, "name": r.name, "total_sold": r.total_sold, "total_revenue": float(r.total_revenue or 0)}
            for r in result.all()
        ]

    async def get_user_stats(self, db: AsyncSession) -> dict:
        total_users = await db.execute(select(func.count(User.id)))
        total_sellers = await db.execute(select(func.count(User.id)).where(User.role == UserRole.SELLER))
        total_customers = await db.execute(select(func.count(User.id)).where(User.role == UserRole.CUSTOMER))
        return {
            "total_users": total_users.scalar() or 0,
            "total_sellers": total_sellers.scalar() or 0,
            "total_customers": total_customers.scalar() or 0,
        }
