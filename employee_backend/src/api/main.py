"""
FastAPI application entry point.

- Configures CORS from environment variables with explicit allowed origins
- Installs correlation ID middleware and structured JSON logging
- Registers API routers with OpenAPI tags
- Provides health endpoint and consistent exception handling returning:
  { "error": { "code": <int>, "message": <str>, "correlationId": <str|null> } }
"""

from __future__ import annotations

import logging
from typing import Dict, List

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

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

# Middleware ordering:
# - ProxyHeadersMiddleware: respect X-Forwarded-* when behind a proxy/load balancer
# - TrustedHostMiddleware: restrict allowed Host headers (defense in depth)
# - CORSMiddleware: must be added before routers to handle preflight
# - CorrelationIdMiddleware: tracing and logging
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")  # starlette uses this to parse forwarded headers

# Trusted hosts from settings; default is permissive in dev
trusted_hosts = settings.trusted_hosts or ["*"]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

# CORS configuration (hardcoded per user request)
# NOTE: This intentionally bypasses env-based configuration to ensure the preview
# frontend and localhost are always allowed during this phase.
# TODO: Revert to env-driven configuration (settings.cors_origins) for production readiness.
HARD_CODED_CORS_ORIGINS: List[str] = [
    "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000",
    "http://localhost:3000",
]
CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
CORS_ALLOW_HEADERS: List[str] = ["Authorization", "Content-Type", "X-Correlation-ID"]
CORS_EXPOSE_HEADERS: List[str] = ["X-Correlation-ID"]

# Middleware ordering must remain:
# ProxyHeaders -> TrustedHost -> CORS -> Correlation -> Routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=HARD_CODED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    expose_headers=CORS_EXPOSE_HEADERS,
)

# Log configured CORS origins at startup (no PII)
@app.on_event("startup")
async def _log_cors_config() -> None:
    auth_signup_route_present = any(
        getattr(r, "path", "") == "/auth/signup" and "POST" in getattr(r, "methods", set())
        for r in app.routes
    )
    logger.info(
        "Hardcoded CORS configured",
        extra={
            "origins": HARD_CODED_CORS_ORIGINS,
            "methods": CORS_ALLOW_METHODS,
            "headers": CORS_ALLOW_HEADERS,
            "expose_headers": CORS_EXPOSE_HEADERS,
            "allow_credentials": True,
            "trusted_hosts": trusted_hosts,
            "auth_signup_path": "/auth/signup",
            "auth_signup_route_present": auth_signup_route_present,
        },
    )

# Install correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)

# Include routers
app.include_router(auth_router.router)
app.include_router(employees_router.router)
app.include_router(dashboard_router.router)

# PUBLIC_INTERFACE
@app.options(
    "/{path:path}",
    include_in_schema=False,
)
def cors_preflight_fallback(path: str, request: Request) -> Response:
    """
    Fallback handler for CORS preflight requests.

    Important:
    - CORSMiddleware should normally intercept and respond to preflight OPTIONS
      requests before they reach the router.
    - This route acts as a safety net to ensure preflight succeeds by returning
      the correct CORS headers when the origin is allowed. It uses the same
      allowlist configured for CORSMiddleware.
    """
    origin = request.headers.get("origin")
    acr_headers = request.headers.get("access-control-request-headers", "")

    # 204 No Content is the typical preflight response code
    resp = Response(status_code=204)

    # Normalize and validate the origin against the configured allowlist
    allowed_norm = [o.lower().rstrip("/") for o in HARD_CODED_CORS_ORIGINS]
    origin_norm = origin.lower().rstrip("/") if origin else None

    # Only return CORS headers if the origin is explicitly allowed
    if origin_norm and origin_norm in allowed_norm:
        resp.headers["Access-Control-Allow-Origin"] = origin
        # Emit Vary: Origin for correct caching semantics
        resp.headers["Vary"] = "Origin"

        # Methods: return configured allowed methods
        resp.headers["Access-Control-Allow-Methods"] = ", ".join(CORS_ALLOW_METHODS)

        # Headers: return the intersection of requested and configured, or our allowlist if none match
        requested = [h.strip() for h in acr_headers.split(",") if h.strip()]
        allowed_lower = [h.lower() for h in CORS_ALLOW_HEADERS]
        if requested:
            intersection = [h for h in requested if h.lower() in allowed_lower]
            allow_headers_value = ", ".join(intersection) if intersection else ", ".join(CORS_ALLOW_HEADERS)
        else:
            allow_headers_value = ", ".join(CORS_ALLOW_HEADERS)
        resp.headers["Access-Control-Allow-Headers"] = allow_headers_value

        # Credentials policy must align with CORSMiddleware
        resp.headers["Access-Control-Allow-Credentials"] = "true"

        # Cache preflight response briefly
        resp.headers["Access-Control-Max-Age"] = "600"

    # If origin is not allowed, return 204 without CORS headers (preflight should then fail)
    return resp


def _error_response(status_code: int, message: str) -> JSONResponse:
    """Build standardized error response payload including correlationId."""
    correlation_id = correlation_id_var.get()
    payload = {"error": {"code": status_code, "message": message, "correlationId": correlation_id}}
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions consistently without leaking internal details."""
    # Don't include path or PII in logs; log code for ops
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
# PUBLIC_INTERFACE
def health_check() -> Dict[str, str]:
    """Return a basic health status response."""
    return {"message": "Healthy"}


@app.get(
    "/_websocket-usage",
    summary="WebSocket Usage",
    description="This API does not expose WebSocket endpoints currently.",
    tags=["Health"],
)
# PUBLIC_INTERFACE
def websocket_help() -> Dict[str, str]:
    """Explicitly document WebSocket usage (none for this project)."""
    return {"message": "No WebSocket endpoints available."}
