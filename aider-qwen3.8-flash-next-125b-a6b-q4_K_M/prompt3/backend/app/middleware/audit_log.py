from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.database import async_session_factory
from app.models.analytics import AuditLog
import uuid


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            async with async_session_factory() as session:
                log = AuditLog(
                    actor_id=None,
                    action=f"{request.method} {request.url.path}",
                    resource_type=None,
                    resource_id=None,
                    metadata={"status_code": response.status_code},
                    ip_address=request.client.host if request.client else None,
                )
                session.add(log)
                await session.commit()
        return response
