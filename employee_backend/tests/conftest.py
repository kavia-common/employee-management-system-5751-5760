"""
Pytest configuration to ensure 'src' package is importable during test collection,
and to set minimal environment variables required for security configuration.

This adjusts sys.path so that 'from src.api.main import app' works regardless of
how pytest sets the working directory, and sets JWT-related env vars to avoid
startup failures during imports in test context.
"""
from __future__ import annotations

import os
import sys

# Ensure minimal security env is present for tests before importing application modules.
# Do NOT use sensitive values here; tests run with ephemeral, non-production secrets.
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("DATABASE_URL", "sqlite:///./employees.db")

# Compute the backend project root (the directory containing 'src' and 'tests')
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Prepend backend root to sys.path if not already present
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)
