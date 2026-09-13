import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine, SessionLocal
from .models import User, Role
from .security import hash_password
from .routers import auth, products, sellers, cart, orders, messaging, chat, admin

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

app = FastAPI(title="Marketplace API")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Normalizes pydantic's 422 body into a flat, readable "detail" message.
    errors = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": "; ".join(errors) or "Invalid input"})


app.include_router(auth.router)
app.include_router(products.router)
app.include_router(sellers.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(messaging.router)
app.include_router(chat.router)
app.include_router(admin.router)

os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _seed_admin()


def _seed_admin():
    """Creates a default admin from env vars on first run, if none exists."""
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return
    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == Role.admin).first() is None:
            db.add(User(
                email=admin_email, password_hash=hash_password(admin_password),
                name="Admin", role=Role.admin,
            ))
            db.commit()
    finally:
        db.close()
