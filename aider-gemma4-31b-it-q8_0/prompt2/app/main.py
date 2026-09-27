from fastapi import FastAPI
from .database import engine, Base
from .routers import users, stores, orders, admin, chat

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Marketplace API")

app.include_router(users.router)
app.include_router(stores.router)
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {"message": "Welcome to the Marketplace API"}
