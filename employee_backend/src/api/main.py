"""
FastAPI application entry point.

- Configures CORS with robust origin derivation:
  1) Use settings.cors_origins (CSV or JSON from CORS_ORIGINS)
  2) If empty, use FRONTEND_ORIGIN env var (single or CSV/JSON)
  3) If still empty, try deriving from a :3001 backend to :3000 frontend on the same host
  4) As a last resort, include preview/local defaults to avoid empty allow_origins
- Installs correlation ID middleware and structured JSON logging
- Registers API routers with OpenAPI tags
- Provides health endpoint and consistent exception handling returning:
  { "error": { "code": <int>, "message": <str>, "correlationId": <str|null> } }

Security:
- Do not hardcode secrets. Preview/local origins are included as safe defaults to ensure CORS headers are always emitted.
- TODO: For production, set CORS_ORIGINS or FRONTEND_ORIGIN in the environment explicitly.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

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
app.add_middleware(ProxyHeadersMiddleware)  # starlette uses this to parse forwarded headers

# Trusted hosts from settings; default is permissive in dev
def _compute_trusted_hosts_patterns(sources: List[str]) -> List[str]:
    """
    Convert environment-provided trusted hosts (which may be full origins) into
    host patterns consumable by Starlette's TrustedHostMiddleware.
    Examples:
      - "https://example.com:3000" -> "example.com"
      - "http://localhost:3000" -> "localhost"
      - "*" -> "*"
    """
    if not sources:
        return ["*"]
    patterns: List[str] = []
    for raw in sources:
        if not raw:
            continue
        s = raw.strip()
        if s == "*":
            # Wildcard shortcut
            patterns = ["*"]
            break
        # Remove scheme if provided
        if "://" in s:
            s = s.split("://", 1)[1]
        # Remove path or trailing slash
        s = s.split("/", 1)[0].rstrip("/")
        # Drop port if included
        if ":" in s:
            s = s.split(":", 1)[0]
        if s:
            patterns.append(s)
    return patterns or ["*"]

trusted_hosts_patterns = _compute_trusted_hosts_patterns(settings.trusted_hosts)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts_patterns)


def _normalize_origin(origin: str) -> str:
    """
    Normalize an origin string for comparison/usage:
    - strip whitespace
    - remove trailing slash
    - lowercase (scheme/host are case-insensitive)
    """
    o = (origin or "").strip()
    if not o:
        return ""
    if o.endswith("/"):
        o = o[:-1]
    return o.lower()


def _parse_env_origins(value: str) -> List[str]:
    """
    Parse env-provided origins. Accepts:
    - JSON array: '["https://a", "http://b:3000"]'
    - CSV: 'https://a,http://b:3000'
    - Single string: 'https://a'
    Returns unique, normalized origins preserving input order.
    """
    if not value:
        return []
    value = value.strip()
    parsed: List[str] = []
    # Try JSON-style array first
    if value.startswith("[") and value.endswith("]"):
        try:
            import json

            arr = json.loads(value)
            if isinstance(arr, list):
                parsed = [str(x) for x in arr if str(x).strip()]
        except Exception:
            # Fall back to CSV
            pass
    if not parsed:
        parts = [p.strip() for p in value.split(",") if p.strip()]
        parsed = parts

    result: List[str] = []
    seen = set()
    for item in parsed:
        norm = _normalize_origin(item)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def _try_derive_frontend_from_backend_env() -> List[str]:
    """
    Attempt to derive a paired frontend origin from environment hints about backend's own origin.

    If a backend origin indicates port 3001 on host H, assume frontend is on the same host at port 3000.
    Checks several common env var names without assuming their presence.
    """
    candidates = [
        os.getenv("BACKEND_ORIGIN", ""),
        os.getenv("API_BASE_URL", ""),
        os.getenv("BACKEND_BASE_URL", ""),
        os.getenv("EXTERNAL_URL", ""),
    ]
    for raw in candidates:
        if not raw:
            continue
        o = _normalize_origin(raw)
        if not o:
            continue
        # Expect "scheme://host[:port]"
        # Cheap parse: find ':3001' at the end of netloc
        # Examples:
        #  - https://example.com:3001 -> https://example.com:3000
        #  - http://localhost:3001 -> http://localhost:3000
        # If there is no explicit :3001, skip (cannot reliably derive).
        if ":3001" in o:
            scheme_host = o.split("://", 1)
            if len(scheme_host) == 2:
                scheme, host_port = scheme_host
                derived = f"{scheme}://{host_port.replace(':3001', ':3000')}"
                return [_normalize_origin(derived)]
    return []


def _compute_cors_allow_origins() -> List[str]:
    """
    Compute a non-empty list of allowed origins for CORS.

    Priority:
    1) settings.cors_origins
    2) FRONTEND_ORIGIN env var (supports JSON/CSV/single)
    3) Derive from backend origin envs with :3001 -> :3000 mapping
    4) Final fallback to preview/local defaults to ensure CORS is never disabled
    """
    origins: List[str] = []

    # 1) From settings (CORS_ORIGINS), already normalized by config
    for o in settings.cors_origins:
        norm = _normalize_origin(o)
        if norm and norm not in origins:
            origins.append(norm)

    # 2) FRONTEND_ORIGIN env (single or CSV/JSON)
    fe_env_raw = os.getenv("FRONTEND_ORIGIN", "")
    for o in _parse_env_origins(fe_env_raw):
        if o not in origins:
            origins.append(o)

    # 3) Derive from backend :3001 -> :3000 mapping if still empty
    if not origins:
        derived = _try_derive_frontend_from_backend_env()
        for o in derived:
            if o not in origins:
                origins.append(o)

    # 4) Final fallback to ensure non-empty list in preview/local
    # Include preview environment URL and localhost. This prevents CORS omission causing signup failures.
    if not origins:
        preview_defaults = [
            "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000",
            "http://localhost:3000",
        ]
        for o in preview_defaults:
            norm = _normalize_origin(o)
            if norm not in origins:
                origins.append(norm)

    return origins


# Effective CORS settings
CORS_ALLOW_ORIGINS: List[str] = _compute_cors_allow_origins()
CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
CORS_ALLOW_HEADERS: List[str] = ["Authorization", "Content-Type", "X-Correlation-ID", "X-Requested-With"]
CORS_EXPOSE_HEADERS: List[str] = ["X-Correlation-ID"]

# Middleware ordering must remain:
# ProxyHeaders -> TrustedHost -> CORS -> Correlation -> Routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
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
        "CORS configured",
        extra={
            "origins": CORS_ALLOW_ORIGINS,
            "methods": CORS_ALLOW_METHODS,
            "headers": CORS_ALLOW_HEADERS,
            "expose_headers": CORS_EXPOSE_HEADERS,
            "allow_credentials": True,
            "trusted_hosts": trusted_hosts_patterns,
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


def _derive_frontend_origin_from_request(request: Request) -> Optional[str]:
    """
    Try to derive an origin for a paired frontend on the same host when backend runs on :3001.
    Uses forwarded headers when available. This is a best-effort fallback primarily for preview.
    """
    # Prefer forwarded headers when behind a proxy
    fwd_host = request.headers.get("x-forwarded-host")
    fwd_proto = request.headers.get("x-forwarded-proto")
    host = fwd_host or request.headers.get("host") or request.url.netloc
    proto = fwd_proto or request.url.scheme or "https"

    if not host:
        return None

    # Extract hostname and port
    hostname = host
    port: Optional[str] = None
    if ":" in host:
        hostname, port = host.rsplit(":", 1)

    # Only derive if explicit 3001 is detected
    if port == "3001":
        scheme = "https" if (proto or "").lower() == "https" else "http"
        return _normalize_origin(f"{scheme}://{hostname}:3000")
    return None


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
      allowlist configured for CORSMiddleware, plus a best-effort derived origin
      for :3001 -> :3000 paired host setups.
    """
    origin = request.headers.get("origin")
    acr_headers = request.headers.get("access-control-request-headers", "")

    # 200 OK for preflight to align with common CORS behavior and acceptance criteria
    resp = Response(status_code=200)

    # Normalize and prepare allowed origins for this request
    allowed_norm = [o.lower().rstrip("/") for o in CORS_ALLOW_ORIGINS]
    derived = _derive_frontend_origin_from_request(request)
    if derived:
        dnorm = derived.lower().rstrip("/")
        if dnorm not in allowed_norm:
            allowed_norm.append(dnorm)

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

    # If origin is not allowed, return 200 without CORS headers (preflight should then fail)
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
