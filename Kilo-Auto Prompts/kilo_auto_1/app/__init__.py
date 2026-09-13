from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app import routers
from app.config import settings
from app.database import AsyncSessionLocal, create_all, engine, get_db
from app.security import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    get_current_refresh_user,
    revoke_refresh_token,
    set_auth_cookies,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    await create_all()
    logging.info("Database tables initialized")
    yield
    logging.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Full-stack e-commerce marketplace with three roles, "
        "UPS shipping calculator, AI chatbot, and admin analytics.",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uploads = settings.uploads_path
    if uploads.exists():
        app.mount("/static/uploads", StaticFiles(directory=uploads), name="uploads")

    app.include_router(routers.auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(routers.users.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(
        routers.products.router, prefix="/api/v1/products", tags=["Products"]
    )
    app.include_router(routers.stores.router, prefix="/api/v1/stores", tags=["Stores"])
    app.include_router(
        routers.categories.router, prefix="/api/v1/categories", tags=["Categories"]
    )
    app.include_router(routers.cart.router, prefix="/api/v1/cart", tags=["Cart"])
    app.include_router(routers.orders.router, prefix="/api/v1/orders", tags=["Orders"])
    app.include_router(routers.returns.router, prefix="/api/v1/returns", tags=["Returns"])
    app.include_router(routers.reviews.router, prefix="/api/v1/reviews", tags=["Reviews"])
    app.include_router(
        routers.seller.router, prefix="/api/v1/seller", tags=["Seller"]
    )
    app.include_router(routers.admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(
        routers.messages.router, prefix="/api/v1/messages", tags=["Messages"]
    )
    app.include_router(
        routers.chatbot.router, prefix="/api/v1/chatbot", tags=["Chatbot"]
    )
    app.include_router(
        routers.shipping.router, prefix="/api/v1/shipping", tags=["Shipping"]
    )
    app.include_router(routers.pages.router, tags=["Pages"])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/v1/auth/token/refresh")
    async def refresh_token_endpoint(
        request: Request,
        response: Response,
        db: AsyncSessionLocal = Depends(get_db),
    ):
        try:
            user = await get_current_refresh_user(request.cookies.get(REFRESH_COOKIE))
        except Exception as exc:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": str(exc)},
            )
        new_access = create_access_token(user)
        new_refresh = create_refresh_token(user)
        resp = JSONResponse({"access_token": new_access, "token_type": "bearer"})
        set_auth_cookies(resp, new_access, new_refresh)
        return resp

    @app.post("/api/v1/auth/logout")
    async def logout(
        request: Request,
        response: Response,
        db: AsyncSessionLocal = Depends(get_db),
    ):
        try:
            await get_current_refresh_user(request.cookies.get(REFRESH_COOKIE))
            token = request.cookies.get(REFRESH_COOKIE)
            if token and db:
                await revoke_refresh_token(token, db)
        except Exception:
            pass
        resp = JSONResponse({"message": "Logged out"})
        clear_auth_cookies(resp)
        return resp

    return app


app = create_app()
