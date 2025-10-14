"""
FastAPI stub application entry point.

This is a [STUB] backend that preserves the public REST API structure while
removing external dependencies (no database, no real authentication).
It uses an in-memory mock store for the lifetime of the process.

- Target: Python 3.10+, FastAPI ^0.110, Uvicorn for dev
- CORS: enabled for all origins in stub mode (allow_origins=["*"])
- Health: GET /health returns {"status": "ok"}
- Authentication [STUB]: /auth/login, /auth/signup, /auth/logout, /auth/me
- Employees [STUB]: CRUD endpoints under /employees
- OpenAPI docs: /docs

Run locally:
  uvicorn app.main:app --host 0.0.0.0 --port 3001
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import auth as auth_router
from app.routers import employees as employees_router
from app.utils.logger import configure_json_logging

# Configure structured JSON logging for consistent observability.
configure_json_logging()
logger = logging.getLogger(__name__)

openapi_tags = [
    {"name": "Authentication", "description": "[STUB] User authentication endpoints (no real auth)"},
    {"name": "Employees", "description": "[STUB] Employee management endpoints using in-memory store"},
    {"name": "Health", "description": "Health endpoints"},
]

app = FastAPI(
    title="Employee Management System API [STUB]",
    description="REST API [STUB] for managing employees. This stub replaces DB/auth with in-memory mocks.",
    version="0.2.0-stub",
    openapi_tags=openapi_tags,
)

# CORS for stub local preview:
# - allow all origins for flexibility in preview environments (localhost and preview URLs)
# - Expose X-Correlation-ID to clients for troubleshooting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev port and preview domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """
    Attach a correlation ID to every response for easier tracing across client/server logs.
    """
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        # Ensure we still return a well-formed JSON payload on unexpected errors
        logger.exception("Unhandled application error")
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": 500,
                    "message": "Internal server error",
                    "correlationId": correlation_id,
                }
            },
        )
    # Always include correlation id on responses
    response.headers["X-Correlation-ID"] = correlation_id
    # Hint caches/proxies that responses may vary by Origin (important for CORS)
    vary_header = response.headers.get("Vary", "")
    if "Origin" not in vary_header:
        response.headers["Vary"] = (vary_header + ", Origin").strip(", ").strip()
    return response


# PUBLIC_INTERFACE
@app.exception_handler(HTTPException)
async def http_exception_to_envelope(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Convert HTTP exceptions into a consistent JSON error envelope and preserve the status code.

    Returns:
        JSONResponse with {"error": {"code": <int>, "message": <str>, "correlationId": <uuid>}}
    """
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    # Delegate to default handler to ensure details like headers are handled, then override body.
    response = await http_exception_handler(request, exc)
    message: str = exc.detail if isinstance(exc.detail, str) else "Request failed"
    payload: Dict[str, Any] = {"error": {"code": exc.status_code, "message": message, "correlationId": correlation_id}}
    new = JSONResponse(status_code=exc.status_code, content=payload, headers=dict(response.headers))
    new.headers["X-Correlation-ID"] = correlation_id
    vary_header = new.headers.get("Vary", "")
    if "Origin" not in (vary_header or ""):
        new.headers["Vary"] = (vary_header + ", Origin").strip(", ").strip()
    return new


# PUBLIC_INTERFACE
@app.exception_handler(RequestValidationError)
async def validation_exception_to_envelope(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Convert validation errors into a standardized JSON envelope with 422 status code.

    Returns:
        JSONResponse with {"error": {"code": 422, "message": "Validation error", "correlationId": <uuid>}}
    """
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    payload = {
        "error": {
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Validation error",
            "correlationId": correlation_id,
            "details": exc.errors(),
        }
    }
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=payload,
        headers={"X-Correlation-ID": correlation_id},
    )


@app.get(
    "/health",
    summary="Health Check [STUB]",
    description="Return a simple status payload to indicate service health. [STUB]",
    tags=["Health"],
)
# PUBLIC_INTERFACE
def health() -> Dict[str, str]:
    """
    Return a basic health status response. [STUB]

    Returns:
        {"status": "ok"}
    """
    return {"status": "ok"}


# Register routers
app.include_router(auth_router.router)
app.include_router(employees_router.router)


if __name__ == "__main__":
    # Provide sensible defaults for local/dev runs. Runtime may override via env.
    # TODO: If deploying behind a platform runner, prefer CLI: uvicorn app.main:app --host 0.0.0.0 --port 3001
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3001"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
