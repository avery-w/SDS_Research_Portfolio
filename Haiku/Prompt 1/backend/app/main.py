from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import engine
from app.models import Base
from app.routes import auth, products, customers, sellers, admins, integrations

app = FastAPI(
    title="E-Commerce Marketplace API",
    description="Multi-role e-commerce platform with customers, sellers, and admins",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(sellers.router)
app.include_router(admins.router)
app.include_router(integrations.router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {
        "message": "E-Commerce Marketplace API",
        "version": "1.0.0",
        "docs": "/docs"
    }
