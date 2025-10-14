"""
FastAPI application entry point.

- Configures CORS from environment variables
- Installs correlation ID middleware and structured JSON logging
- Registers API routers with OpenAPI tags
- Provides health endpoint and consistent exception handling returning:
  { "error": { "code": <int>, "message": <str>, "correlationId": <str|null> } }
"""

from __future__ import annotations

import logging
from typing import Dict, List

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.config import settings
from src.core.logging_config import setup_logging
from src.middlewares.correlation import CorrelationIdMiddleware, correlation_id_var
from src.routers import auth as auth_router
from src.routers import dashboard as dashboard_router
from src.routers import employees as employees_router

# Configure logging at import time
setup_logging()
logger = logging.getLogger(__name__)

openapi_tags = [
    {"name": "Authentication", "description": "User authentication endpoints"},
    {"name": "Employees", "description": "Employee management endpoints"},
    {"name": "Dashboard", "description": "Dashboard statistics endpoints"},
]

app = FastAPI(
    title="Employee Management System API",
    description="REST API for managing employees with authentication and dashboards.",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS configuration from environment
allow_origins: List[str] = settings.cors_origins if settings.cors_origins else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins if allow_origins else ["*"] if settings.env == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Install correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)

# Include routers
app.include_router(auth_router.router)
app.include_router(employees_router.router)
app.include_router(dashboard_router.router)


def _error_response(status_code: int, message: str) -> JSONResponse:
    """Build standardized error response payload including correlationId."""
    correlation_id = correlation_id_var.get()
    payload = {"error": {"code": status_code, "message": message, "correlationId": correlation_id}}
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions consistently without leaking internal details."""
    # Don't include path or PII in logs; log code and route for ops
    logger.warning("HTTP exception", extra={"status_code": exc.status_code})
    return _error_response(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors consistently."""
    logger.debug("Validation error on request", extra={"errors": "redacted"})
    return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors with a generic message to avoid exposing internals."""
    logger.exception("Unhandled server error")
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")


@app.get(
    "/",
    summary="Health Check",
    description="Simple health check endpoint.",
    tags=["Health"],
)
def health_check() -> Dict[str, str]:
    """Return a basic health status response."""
    return {"message": "Healthy"}


@app.get(
    "/_websocket-usage",
    summary="WebSocket Usage",
    description="This API does not expose WebSocket endpoints currently.",
    tags=["Health"],
)
def websocket_help() -> Dict[str, str]:
    """Explicitly document WebSocket usage (none for this project)."""
    return {"message": "No WebSocket endpoints available."}
