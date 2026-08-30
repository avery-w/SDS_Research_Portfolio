from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import UPLOAD_DIR
from app.database import create_db_and_tables
from app.routers import admin, auth, cart, chatbot, messages, orders, products, returns, seller, stores, upload, users

app = FastAPI(title="Marketplace API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(stores.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(returns.router)
app.include_router(messages.router)
app.include_router(chatbot.router)
app.include_router(seller.router)
app.include_router(admin.router)
app.include_router(upload.router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def root():
    return {"message": "Marketplace API running"}
