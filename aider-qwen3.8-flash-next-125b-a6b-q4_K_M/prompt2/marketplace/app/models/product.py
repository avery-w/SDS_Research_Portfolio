from app.extensions import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    sku = db.Column(db.String(100), unique=True)
    category = db.Column(db.String(100), index=True)
    image_paths = db.Column(db.ARRAY(db.String(500)))
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    store = db.relationship("Store", backref=db.backref("products", lazy="dynamic"))
