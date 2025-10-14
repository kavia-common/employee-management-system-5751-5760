"""
FastAPI stub application entry point.

This is a [STUB] backend that preserves the public REST API structure while
removing external dependencies (no database, no real authentication).
It uses an in-memory mock store for the lifetime of the process.

- Target: Python 3.10+, FastAPI ^0.110, Uvicorn for dev
- CORS: enabled for http://localhost:3000
- Health: GET /health
- Authentication [STUB]: /auth/login, /auth/signup, /auth/logout
- Employees [STUB]: CRUD endpoints under /employees

Run locally:
  uvicorn app.main:app --host 0.0.0.0 --port 3001
"""
from __future__ import annotations

import logging
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    version="0.1.0-stub",
    openapi_tags=openapi_tags,
)

# CORS for stub local preview
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev port
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


@app.get(
    "/health",
    summary="Health Check [STUB]",
    description="Return a simple status payload to indicate service health. [STUB]",
    tags=["Health"],
)
# PUBLIC_INTERFACE
def health() -> Dict[str, str]:
    """Return a basic health status response. [STUB]"""
    return {"status": "ok", "mode": "stub"}


# Register routers
app.include_router(auth_router.router)
app.include_router(employees_router.router)
