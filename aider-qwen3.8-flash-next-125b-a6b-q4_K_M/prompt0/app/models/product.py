from datetime import datetime, timezone
from app import db

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    children = db.relationship("Category", backref=db.backref("parent", remote_side=[id]))

    def __repr__(self):
        return f"<Category {self.name}>"

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    sku = db.Column(db.String(100), unique=True)
    weight_oz = db.Column(db.Float, default=0)
    length_in = db.Column(db.Float, default=0)
    width_in = db.Column(db.Float, default=0)
    height_in = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    images = db.relationship("ProductImage", backref="product", lazy=True, cascade="all, delete-orphan")
    order_items = db.relationship("OrderItem", backref="product", lazy=True)

    def __repr__(self):
        return f"<Product {self.name}>"

class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
