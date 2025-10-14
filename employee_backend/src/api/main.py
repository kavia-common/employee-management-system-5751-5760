"""
FastAPI application entry point.

- Definitive CORS configuration requested:
  allow_origins includes:
    - https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000
    - http://localhost:3000
  allow_credentials: True
  allow_methods: ['GET','POST','PUT','DELETE','PATCH','OPTIONS']
  allow_headers: ['Authorization','Content-Type','X-Correlation-ID','X-Requested-With']
  expose_headers: ['X-Correlation-ID']

- Middleware ordering MUST be:
  ProxyHeadersMiddleware -> TrustedHostMiddleware -> CORSMiddleware -> CorrelationIdMiddleware -> Routers

- Includes a minimal fallback OPTIONS '/{path:path}' route that returns the above headers.

- Provides OpenAPI docs tags and simple health endpoints.

Security:
- No secrets are hardcoded; only CORS origins are fixed as per task requirements.
- For production, prefer environment-driven origins.

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

# ---------------------------------------------------------------------------
# Middleware ordering: ProxyHeaders -> TrustedHost -> CORS -> Correlation
# ---------------------------------------------------------------------------

# Proxy headers (safe defaults; no parameters required)
app.add_middleware(ProxyHeadersMiddleware)

# TrustedHostMiddleware: in dev and to avoid startup issues, accept any host.
# If stricter host checks are required, configure via environment later.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"], www_redirect=False)

# Definitive CORS settings per request
CORS_ALLOW_ORIGINS: List[str] = [
    "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000",
    "http://localhost:3000",
]
CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
CORS_ALLOW_HEADERS: List[str] = ["Authorization", "Content-Type", "X-Correlation-ID", "X-Requested-With"]
CORS_EXPOSE_HEADERS: List[str] = ["X-Correlation-ID"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    expose_headers=CORS_EXPOSE_HEADERS,
)

# Correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)

# Routers
app.include_router(auth_router.router)
app.include_router(employees_router.router)
app.include_router(dashboard_router.router)


# ---------------------------------------------------------------------------
# Utilities and common handlers
# ---------------------------------------------------------------------------

def _normalize_origin(origin: str) -> str:
    """Normalize origin by trimming, removing trailing slash, and lowering."""
    o = (origin or "").strip()
    if not o:
        return ""
    if o.endswith("/"):
        o = o[:-1]
    return o.lower()


# PUBLIC_INTERFACE
@app.middleware("http")
async def add_vary_origin_header(request: Request, call_next):
    """
    Ensure Vary: Origin header is present on all responses.

    This helps caches differentiate responses by Origin to comply with CORS.
    """
    response = await call_next(request)
    try:
        vary_val = response.headers.get("Vary")
        if vary_val:
            if "Origin" not in [v.strip() for v in vary_val.split(",")]:
                response.headers["Vary"] = vary_val + ", Origin"
        else:
            response.headers["Vary"] = "Origin"
    except Exception:
        # Do not fail response for header adjustments
        pass
    return response


# PUBLIC_INTERFACE
@app.options(
    "/{path:path}",
    include_in_schema=False,
)
def cors_preflight_fallback(path: str, request: Request) -> Response:
    """
    Minimal fallback handler for CORS preflight requests.

    CORSMiddleware should handle OPTIONS before routing. This route ensures that,
    if OPTIONS reaches routing, the response still includes expected headers
    for allowed origins.

    Returns 200 with:
      - Access-Control-Allow-Origin (echoed origin if allowed)
      - Access-Control-Allow-Methods (configured list)
      - Access-Control-Allow-Headers (intersection or configured list)
      - Access-Control-Allow-Credentials: true
      - Access-Control-Max-Age
      - Vary: Origin
    """
    origin = request.headers.get("origin")
    acr_headers = request.headers.get("access-control-request-headers", "")
    resp = Response(status_code=200)

    # Normalize for comparison
    allowed = [_normalize_origin(o) for o in CORS_ALLOW_ORIGINS]
    origin_norm = _normalize_origin(origin) if origin else None

    if origin_norm and origin_norm in allowed:
        # Mirror origin if allowed
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Methods"] = ", ".join(CORS_ALLOW_METHODS)

        requested = [h.strip() for h in acr_headers.split(",") if h.strip()]
        allowed_lower = [h.lower() for h in CORS_ALLOW_HEADERS]
        if requested:
            # Case-insensitive intersection; if none, return configured list
            intersection: list[str] = []
            for h in requested:
                if h.lower() in allowed_lower and h not in intersection:
                    intersection.append(h)
            allow_headers_value = ", ".join(intersection) if intersection else ", ".join(CORS_ALLOW_HEADERS)
        else:
            allow_headers_value = ", ".join(CORS_ALLOW_HEADERS)
        resp.headers["Access-Control-Allow-Headers"] = allow_headers_value
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Max-Age"] = "600"

    return resp


def _error_response(status_code: int, message: str) -> JSONResponse:
    """Build standardized error response payload including correlationId."""
    correlation_id = correlation_id_var.get()
    payload = {"error": {"code": status_code, "message": message, "correlationId": correlation_id}}
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions consistently without leaking internal details."""
    logger.warning("HTTP exception", extra={"status_code": exc.status_code})
    # Use exc.detail string for message
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
