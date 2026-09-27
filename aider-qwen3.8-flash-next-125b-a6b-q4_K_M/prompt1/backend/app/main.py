from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, NoResultFound
from app.config import settings
from app.routers import auth, users, products, stores, cart, orders, shipping, chatbot, admin
from app.middleware.error_handler import (
    validation_exception_handler,
    integrity_error_handler,
    not_found_handler,
    generic_exception_handler,
)
from app.middleware.auth_middleware import RateLimitMiddleware

app = FastAPI(title="Marketplace API", version="1.0.0")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(NoResultFound, not_found_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(stores.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(shipping.router)
app.include_router(chatbot.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "healthy"}
