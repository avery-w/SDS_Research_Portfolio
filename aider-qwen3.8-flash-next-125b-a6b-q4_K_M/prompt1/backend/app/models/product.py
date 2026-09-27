from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    slug = Column(String(500), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    compare_at_price = Column(Float, nullable=True)
    sku = Column(String(100), unique=True, nullable=True)
    barcode = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    images = Column(JSON, default=list)
    stock_quantity = Column(Integer, default=0)
    weight_oz = Column(Float, nullable=True)
    dimensions = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    store = relationship("Store", back_populates="products")
