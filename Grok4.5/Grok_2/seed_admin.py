"""Create admin user. Run: python seed_admin.py"""
from app.database import SessionLocal, engine, Base
from app.models import User, UserRole
from app.auth import get_password_hash

Base.metadata.create_all(bind=engine)
db = SessionLocal()
email = "admin@marketplace.local"
existing = db.query(User).filter(User.email == email).first()
if existing:
    existing.role = UserRole.admin
    existing.is_active = True
    db.commit()
    print(f"Updated {email} → admin")
else:
    db.add(User(
        email=email,
        hashed_password=get_password_hash("admin123"),
        full_name="Platform Admin",
        role=UserRole.admin,
        is_active=True,
    ))
    db.commit()
    print(f"Created admin → {email} / admin123")
db.close()
