from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.limiter import limiter
from app.routers import admin, auth, cart, chatbot, checkout, customer, products, seller
from app.security import CSRF_COOKIE_NAME, new_csrf_token

settings = get_settings()

app = FastAPI(title="Marketplace")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")


class CSRFCookieMiddleware(BaseHTTPMiddleware):
    """Ensures every visitor has a CSRF cookie, and exposes it to templates via
    request.state.csrf_token for embedding as a hidden form field."""

    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get(CSRF_COOKIE_NAME)
        is_new = token is None
        if is_new:
            token = new_csrf_token()
        request.state.csrf_token = token

        response = await call_next(request)

        if is_new:
            response.set_cookie(
                CSRF_COOKIE_NAME,
                token,
                httponly=True,  # only the server needs to read it back; forms embed the value directly
                samesite="lax",
                secure=settings.session_cookie_secure,
                max_age=60 * 60 * 24 * 7,
            )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


app.add_middleware(CSRFCookieMiddleware)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(checkout.router)
app.include_router(customer.router)
app.include_router(seller.router)
app.include_router(admin.router)
app.include_router(chatbot.router)
