"""Create tables and seed one admin account. Run once: python init_db.py"""
import os

from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    db.create_all()
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    if not User.query.filter_by(email=admin_email).first():
        admin = User(name="Admin", email=admin_email, role="admin")
        admin.set_password(os.environ.get("ADMIN_PASSWORD", "changeme123"))
        db.session.add(admin)
        db.session.commit()
        print(f"Seeded admin: {admin_email} / (see ADMIN_PASSWORD env or 'changeme123')")
    else:
        print("Admin already exists, skipping seed.")
