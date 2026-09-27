import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import get_settings

settings = get_settings()
_request_counts: dict[str, list[float]] = defaultdict(list)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60.0
        _request_counts[client_ip] = [t for t in _request_counts[client_ip] if now - t < window]
        if len(_request_counts[client_ip]) >= settings.RATE_LIMIT_PER_MIN:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        _request_counts[client_ip].append(now)
        return await call_next(request)
