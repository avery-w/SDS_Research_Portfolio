from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, Integer
from app.db.base import Base

class DailySales(Base):
    __tablename__ = "daily_sales"
    day: Mapped["Date"] = mapped_column(Date, primary_key=True)
    orders_count: Mapped[int] = mapped_column(Integer, default=0)
    gross_cents: Mapped[int] = mapped_column(Integer, default=0)
    units_sold: Mapped[int] = mapped_column(Integer, default=0)
