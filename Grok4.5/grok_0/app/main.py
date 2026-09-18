import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .database import engine, Base
from .config import get_settings
from .routers import auth, customer, seller, admin, api

settings = get_settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Modern Marketplace",
    description="Multi-role e-commerce marketplace (Customer / Seller / Admin)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & uploads
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

templates = Jinja2Templates(directory="app/templates")

# Routers
app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(seller.router)
app.include_router(admin.router)
app.include_router(api.router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "ok"}
