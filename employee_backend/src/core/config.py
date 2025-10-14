"""
Application configuration management.

This module centralizes environment-driven configuration for the Employee
Management System backend. It ensures that secrets are never hardcoded and that
behavior can be tuned per environment.

Security:
- Never hardcode secrets; always source from environment (.env for dev).
- This module reads environment variables and provides typed, validated access.

Usage:
- Import `settings` singleton to access configuration values.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

# Load environment variables from .env for local development convenience.
# In production, environment variables should come from the hosting environment.
load_dotenv()


def _normalize_origin(origin: str) -> str:
    """
    Normalize an origin string for comparison/usage:
    - strip whitespace
    - remove trailing slash
    - lowercase scheme and host (safe for comparison; paths are not expected)
    """
    o = (origin or "").strip()
    if not o:
        return ""
    # remove trailing slash if present
    if o.endswith("/"):
        o = o[:-1]
    # lowercase the whole string (origins are case-insensitive for scheme/host)
    # Path portion is not used in same-origin checks here.
    return o.lower()


def _parse_origins_env(value: str) -> List[str]:
    """
    Parse CORS origins from environment.

    Supports:
    - JSON-style arrays: '["https://a", "http://b:3000"]'
    - Comma-separated lists: 'https://a,http://b:3000'
    - Single origin string: 'https://a'

    Returns a list of normalized, unique origins.
    """
    if not value:
        return []

    parsed: List[str] = []
    raw = value.strip()

    # Try JSON array parsing if it looks like JSON
    if raw.startswith("[") and raw.endswith("]"):
        try:
            arr = json.loads(raw)
            if isinstance(arr, list):
                parsed = [str(x) for x in arr if str(x).strip()]
        except Exception:
            # Fallback to CSV if invalid JSON
            pass

    if not parsed:
        # Fallback to CSV
        parts = [p for p in raw.split(",") if p.strip()]
        parsed = [p for p in parts]

    # Normalize and deduplicate while preserving order
    seen = set()
    result: List[str] = []
    for item in parsed:
        norm = _normalize_origin(item)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def _parse_csv_list(value: str) -> List[str]:
    """
    Parse a comma separated string into a list, trimming whitespace and ignoring empties.
    Note: kept for compatibility with other settings that may use CSV only.
    """
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Typed settings with defaults suitable for local development only."""

    # Environment metadata
    env: str = field(default=os.getenv("ENV", "development"))
    log_level: str = field(default=os.getenv("LOG_LEVEL", "INFO"))

    # CORS configuration - supports JSON-style or CSV list of origins
    # NOTE: CORS is currently hardcoded in src.api.main per user request to allow specific preview/local origins.
    # TODO: Re-enable env-driven CORS via this setting for production deployments.
    cors_origins: List[str] = field(
        default_factory=lambda: _parse_origins_env(os.getenv("CORS_ORIGINS", "")),
    )

    # Trusted hosts configuration (defense in depth)
    # Accept CSV or JSON array; in development default to wildcard for convenience.
    trusted_hosts: List[str] = field(
        default_factory=lambda: (
            _parse_origins_env(os.getenv("TRUSTED_HOSTS", "")) or (["*"] if os.getenv("ENV", "development") == "development" else [])
        ),
    )

    # Database URL (used by SQLAlchemy in session.py)
    database_url: str = field(default=os.getenv("DATABASE_URL", "sqlite:///./employees.db"))

    # Security configuration for JWT
    jwt_secret: str = field(default=os.getenv("JWT_SECRET", "CHANGE_ME_IN_ENV"))  # TODO: set in environment
    jwt_algorithm: str = field(default=os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(
        default=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    )


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return application settings loaded from environment."""
    return settings


# Singleton instance for convenience import
settings = Settings()
