from app.extensions import db
from datetime import datetime

class Store(db.Model):
    __tablename__ = "stores"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    logo_path = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller = db.relationship("User", backref=db.backref("stores", lazy="dynamic"))
