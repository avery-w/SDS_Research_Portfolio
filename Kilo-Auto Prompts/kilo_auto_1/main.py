"""Entry point: uvicorn invocation."""
from __future__ import annotations

import uvicorn

from app import settings, app as app_module

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.debug and "0.0.0.0" or "0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.debug and "debug" or "info",
    )
