from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

def install_error_handlers(app: FastAPI):
    @app.exception_handler(422)
    async def validation_handler(request: Request, exc):
        return JSONResponse(status_code=422, content={"detail": "Invalid input", "errors": getattr(exc, "errors", lambda: [])()})
    # NOTE: 401 and 403 are raised via dependencies; 404 is default.
