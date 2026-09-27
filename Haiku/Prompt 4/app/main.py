from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import Base, engine
from app.routes import auth, products, cart, stores, orders, checkout, chat, admin, users

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="E-Commerce Marketplace API",
    description="Production-ready e-commerce platform with customer, seller, and admin roles",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(stores.router)
app.include_router(orders.router)
app.include_router(checkout.router)
app.include_router(chat.router)
app.include_router(admin.router)

@app.get("/", tags=["root"])
def read_root():
    return {
        "message": "E-Commerce Marketplace API",
        "docs": "/docs",
        "openapi_schema": "/openapi.json"
    }

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy"}
