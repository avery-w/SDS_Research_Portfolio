import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.order import Order, OrderStatus
from app.models.analytics import SalesSnapshot


async def generate_sales_snapshot(db: AsyncSession, store_id: uuid.UUID, start: datetime, end: datetime) -> SalesSnapshot:
    result = await db.execute(
        select(
            func.sum(Order.total).label("revenue"),
            func.count(Order.id).label("count"),
        ).where(
            Order.store_id == store_id,
            Order.status == OrderStatus.delivered,
            Order.created_at >= start,
            Order.created_at <= end,
        )
    )
    row = result.one()
    snapshot = SalesSnapshot(
        store_id=store_id,
        period_start=start,
        period_end=end,
        total_revenue=float(row.revenue or 0),
        total_orders=int(row.count or 0),
        top_products=None,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot
