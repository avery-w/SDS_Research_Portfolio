from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter.depends import RateLimiter
from fastapi.responses import ORJSONResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.rate_limit import init_rate_limiter
from app.utils.errors import install_error_handlers
from app.routers import auth, users, sellers, products, cart, checkout, orders, returns, messages, admin, analytics, chatbot

templates = Jinja2Templates(directory="app/templates")

def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, default_response_class=ORJSONResponse)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
    app.include_router(users.router, prefix=settings.API_V1_PREFIX)
    app.include_router(sellers.router, prefix=settings.API_V1_PREFIX, dependencies=[RateLimiter(times=60, seconds=60)])
    app.include_router(products.router, prefix=settings.API_V1_PREFIX)
    app.include_router(cart.router, prefix=settings.API_V1_PREFIX)
    app.include_router(checkout.router, prefix=settings.API_V1_PREFIX)
    app.include_router(orders.router, prefix=settings.API_V1_PREFIX)
    app.include_router(returns.router, prefix=settings.API_V1_PREFIX)
    app.include_router(messages.router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
    app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
    app.include_router(chatbot.router, prefix=settings.API_V1_PREFIX)
    return app

app = create_app()

@app.on_event("startup")
async def on_startup():
    await init_rate_limiter(app)

# Example page route
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
