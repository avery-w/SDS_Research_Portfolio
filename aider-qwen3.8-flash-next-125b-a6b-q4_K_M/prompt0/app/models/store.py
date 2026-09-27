from datetime import datetime, timezone
from app import db

class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(500))
    banner_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    products = db.relationship("Product", backref="store", lazy=True)

    def __repr__(self):
        return f"<Store {self.name}>"
