"""
FastAPI application entry point.

- Definitive CORS configuration requested (dev preview + localhost):
  allow_origins includes:
    - https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000
    - https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3002
    - http://localhost:3000
    - http://localhost:3002

- Developer note: prefer running uvicorn on port 3002 for local/dev consistency with docs.
  allow_credentials: True
  allow_methods: ['GET','POST','PUT','DELETE','PATCH','OPTIONS']
  allow_headers: ['Authorization','Content-Type','X-Correlation-ID','X-Requested-With']
  expose_headers: ['X-Correlation-ID']

- Middleware ordering simplified to avoid startup/import/runtime conflicts:
  CORSMiddleware -> CorrelationIdMiddleware -> Routers
  (TrustedHostMiddleware and ProxyHeadersMiddleware temporarily removed)

- Includes a minimal fallback OPTIONS '/{path:path}' route that returns the above headers.

- Provides OpenAPI docs tags and simple health endpoints.

Security:
- No secrets are hardcoded; only CORS origins are fixed as per task requirements.
- For production, prefer environment-driven origins and consider re-adding host/proxy middleware.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.logging_config import setup_logging
from src.db.session import engine
from src.middlewares.correlation import CorrelationIdMiddleware, correlation_id_var
from src.routers import auth as auth_router
from src.routers import dashboard as dashboard_router
from src.routers import employees as employees_router
from src.services import seed_sample_employees_if_needed

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
# Middleware ordering: CORS -> Correlation
# (TrustedHost and ProxyHeaders temporarily removed to stabilize startup)
# ---------------------------------------------------------------------------

# Definitive CORS settings per request
CORS_ALLOW_ORIGINS: List[str] = [
    "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000",
    "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3002",
    "http://localhost:3000",
    "http://localhost:3002",
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
# Startup database check & auto-migration
# ---------------------------------------------------------------------------


def _ensure_alembic_upgrade_head() -> None:
    """
    Internal helper to run 'alembic upgrade head' programmatically.

    Avoids blowing up the app on failure; logs errors and allows request-time
    handlers to respond gracefully if DB remains unavailable.
    """
    try:
        project_root = Path(__file__).resolve().parents[2]  # employee_backend/
        alembic_ini = project_root / "alembic.ini"
        migrations_dir = project_root / "alembic"
        cfg = Config(str(alembic_ini))
        # Explicitly set script location and DB URL for safety in various run contexts
        cfg.set_main_option("script_location", str(migrations_dir))
        cfg.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", "sqlite:///./employees.db"))
        command.upgrade(cfg, "head")
        logger.info("Alembic migrations applied (upgrade head).")
    except Exception:
        logger.exception("Failed to run Alembic migrations at startup.")


def _core_tables_present() -> bool:
    """Return True if essential tables exist (users, employees)."""
    try:
        with engine.connect() as conn:
            insp = inspect(conn)
            return insp.has_table("users") and insp.has_table("employees")
    except Exception:
        # Connection failure or engine issues; treat as not present
        logger.warning("Unable to inspect database for core tables.", exc_info=True)
        return False


def _self_test_password_hashing() -> None:
    """
    Perform a lightweight self-test of password hashing/verification to ensure
    passlib[bcrypt] is available at runtime. Logs errors but does not prevent startup.
    """
    try:
        # Lazy import to avoid any potential circular imports at import time
        from src.core.security import hash_password, verify_password  # type: ignore

        test_pw = "self-test-password"
        hashed = hash_password(test_pw)
        if not verify_password(test_pw, hashed):
            raise RuntimeError("Password verification failed during self-test.")
        logger.info("Password hashing self-test passed (bcrypt available).")
    except Exception:
        logger.exception(
            "Password hashing self-test failed; ensure 'passlib[bcrypt]' is installed and functional."
        )


# PUBLIC_INTERFACE
@app.on_event("startup")
async def ensure_database_ready_on_startup() -> None:
    """
    Apply Alembic migrations at startup if core tables are missing.

    This prevents 500 errors on auth endpoints due to missing tables when
    the service is started without first running migrations.

    Additionally, in development environments, optionally seed sample
    employees when the table is empty to improve DX and allow the
    frontend to render lists immediately after login.
    """
    if _core_tables_present():
        # Still perform security self-test to catch missing bcrypt early
        _self_test_password_hashing()
    else:
        logger.warning("Core tables missing at startup. Attempting to apply migrations...")
        _ensure_alembic_upgrade_head()
        # Recheck and log outcome
        if not _core_tables_present():
            logger.error("Database still missing core tables after migration attempt.")
        # Always perform security self-test
        _self_test_password_hashing()

    # Dev-only optional seed
    try:
        env = os.getenv("ENV", "development").lower()
        seed_flag = os.getenv("SEED_ON_STARTUP")
        # Default: seed in development unless explicitly disabled
        should_seed = (seed_flag.lower() == "true") if seed_flag else (env == "development")
        if should_seed:
            logger.info("Seeding check: attempting to seed sample employees if needed (dev-only).")
            # Use a short-lived session to avoid interfering with request sessions
            from src.db.session import SessionLocal

            with SessionLocal() as db_sess:
                created = seed_sample_employees_if_needed(db_sess)
                if created > 0:
                    logger.info("Seeded %d sample employees.", created)
    except Exception:
        # Never block startup due to seeding; log and continue
        logger.exception("Employee seeding failed; continuing without seed.")

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


def _is_origin_allowed(origin: str | None) -> bool:
    """Check if the provided origin is in the allowlist (case-insensitive, no trailing slash)."""
    if not origin:
        return False
    allowed = [_normalize_origin(o) for o in CORS_ALLOW_ORIGINS]
    return _normalize_origin(origin) in allowed


def _apply_cors_headers(resp: Response, request: Request) -> None:
    """
    Apply CORS headers to the response if the Origin is allowed.

    This is used as a safety net for error responses produced by exception handlers
    so that browsers still receive the necessary headers to surface details to client code.
    """
    try:
        origin = request.headers.get("origin")
        if _is_origin_allowed(origin):
            # Mirror the origin and include standard headers
            resp.headers["Access-Control-Allow-Origin"] = origin  # exact echo
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            # Expose correlation id header for tracing across client
            if CORS_EXPOSE_HEADERS:
                resp.headers["Access-Control-Expose-Headers"] = ", ".join(CORS_EXPOSE_HEADERS)
        # Always ensure Vary: Origin is present
        vary_val = resp.headers.get("Vary")
        if vary_val:
            if "Origin" not in [v.strip() for v in vary_val.split(",")]:
                resp.headers["Vary"] = vary_val + ", Origin"
        else:
            resp.headers["Vary"] = "Origin"
    except Exception:
        # Never let CORS header application break the response path
        pass


def _apply_common_headers(resp: Response, request: Request) -> None:
    """
    Apply CORS headers and ensure X-Correlation-ID is set on responses,
    including error responses produced by exception handlers.
    """
    _apply_cors_headers(resp, request)
    try:
        correlation_id = correlation_id_var.get()
        if not correlation_id:
            # Fallback to the value stored on request.state by the CorrelationIdMiddleware.
            # The middleware resets the contextvar on exception paths, so this preserves
            # the correlation ID for error responses.
            correlation_id = getattr(request.state, "correlation_id", None)
        if correlation_id:
            resp.headers["X-Correlation-ID"] = correlation_id
    except Exception:
        # Do not fail response for header adjustments
        pass


# PUBLIC_INTERFACE
@app.middleware("http")
async def add_vary_origin_header(request: Request, call_next):
    """
    Ensure Vary: Origin header is present on all responses and apply common headers.

    This helps caches differentiate responses by Origin to comply with CORS and
    ensures Access-Control-Expose-Headers, Access-Control-Allow-Origin (when allowed),
    and X-Correlation-ID are applied to all responses.
    """
    response = await call_next(request)
    try:
        # Always ensure Vary: Origin
        vary_val = response.headers.get("Vary")
        if vary_val:
            if "Origin" not in [v.strip() for v in vary_val.split(",")]:
                response.headers["Vary"] = vary_val + ", Origin"
        else:
            response.headers["Vary"] = "Origin"

        # Apply common headers (CORS + correlation) post-handler as safety net
        _apply_common_headers(response, request)
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

    # Always ensure Vary: Origin is set for caches
    vary_val = resp.headers.get("Vary")
    resp.headers["Vary"] = (vary_val + ", Origin") if vary_val and "Origin" not in vary_val else "Origin"

    # Normalize for comparison
    if _is_origin_allowed(origin):
        # Mirror origin if allowed
        resp.headers["Access-Control-Allow-Origin"] = origin
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


def _error_response(status_code: int, message: str, request: Optional[Request] = None) -> JSONResponse:
    """Build standardized error response payload including correlationId."""
    correlation_id = correlation_id_var.get()
    if not correlation_id and request is not None:
        try:
            correlation_id = getattr(request.state, "correlation_id", None)
        except Exception:
            correlation_id = None
    payload = {"error": {"code": status_code, "message": message, "correlationId": correlation_id}}
    return JSONResponse(status_code=status.HTTP_200_OK if status_code == 200 else status_code, content=payload)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions consistently without leaking internal details."""
    logger.warning("HTTP exception", extra={"status_code": exc.status_code})
    # Use exc.detail string for message
    resp = _error_response(exc.status_code, str(exc.detail), request)
    _apply_common_headers(resp, request)
    return resp


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors consistently."""
    logger.debug("Validation error on request", extra={"errors": "redacted"})
    resp = _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error", request)
    _apply_common_headers(resp, request)
    return resp


@app.exception_handler(OperationalError)
async def db_operational_error_handler(request: Request, exc: OperationalError):
    """Handle database operational errors (e.g., missing tables/migrations) gracefully."""
    logger.error("Database operational error encountered")
    # Provide a safe message guiding the operator to run migrations
    message = "Database is not ready. Please apply migrations (e.g., 'alembic upgrade head')."
    resp = _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, message, request)
    _apply_common_headers(resp, request)
    return resp


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors with a generic message to avoid exposing internals."""
    logger.exception("Unhandled server error")
    resp = _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error", request)
    _apply_common_headers(resp, request)
    return resp


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
    "/healthz",
    summary="Health Check (compat)",
    description=(
        "Kubernetes-style liveness probe endpoint. Alias of '/' (GET only). "
        "Returns 200 with {'message': 'Healthy'}."
    ),
    tags=["Health"],
    operation_id="health_check_healthz_get",
)
# PUBLIC_INTERFACE
def health_check_healthz_app() -> Dict[str, str]:
    """Compatibility health endpoint that mirrors '/' to ensure GET /healthz returns 200."""
    return {"message": "Healthy"}


@app.head(
    "/",
    summary="Health Check (HEAD)",
    description="HEAD variant of the health check for load balancers and probes.",
    tags=["Health"],
)
# PUBLIC_INTERFACE
def health_check_head() -> Response:
    """Return empty body with 200 OK for HEAD health checks."""
    return Response(status_code=200)


@app.head(
    "/healthz",
    summary="Health Check (compat, HEAD)",
    description="HEAD variant of /healthz for load balancers and probes.",
    tags=["Health"],
    operation_id="health_check_healthz_head",
)
# PUBLIC_INTERFACE
def health_check_healthz_head() -> Response:
    """Return empty body with 200 OK for HEAD /healthz checks."""
    return Response(status_code=200)


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
