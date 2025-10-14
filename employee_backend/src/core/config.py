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

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

# Load environment variables from .env for local development convenience.
# In production, environment variables should come from the hosting environment.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Typed settings with defaults suitable for local development only."""

    # Environment metadata
    env: str = field(default=os.getenv("ENV", "development"))
    log_level: str = field(default=os.getenv("LOG_LEVEL", "INFO"))

    # CORS configuration - comma separated list of origins
    cors_origins: List[str] = field(
        default_factory=lambda: _parse_csv_list(os.getenv("CORS_ORIGINS", "")),
    )

    # Database URL (used by SQLAlchemy in session.py)
    database_url: str = field(default=os.getenv("DATABASE_URL", "sqlite:///./employees.db"))

    # Security configuration for JWT
    jwt_secret: str = field(default=os.getenv("JWT_SECRET", "CHANGE_ME_IN_ENV"))  # TODO: set in environment
    jwt_algorithm: str = field(default=os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(
        default=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    )


def _parse_csv_list(value: str) -> List[str]:
    """
    Parse a comma separated string into a list, trimming whitespace and ignoring empties.
    """
    return [item.strip() for item in value.split(",") if item.strip()]


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return application settings loaded from environment."""
    return settings


# Singleton instance for convenience import
settings = Settings()
