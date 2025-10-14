"""
Session and engine management for the Employee Management System backend.

This module centralizes SQLAlchemy engine and session configuration, ensuring:
- Single, pooled engine instance per process
- Environment-driven configuration (no hardcoded credentials)
- Safe session lifecycle via dependency generator for FastAPI routes
- SQLite compatibility for local development

Security considerations:
- No credentials are hardcoded; all configurations are read from environment variables.
- Connection pooling is enabled for non-SQLite databases.
"""

from __future__ import annotations

import os
from typing import Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

# Load environment variables from .env if present (dev convenience)
load_dotenv()


def _get_env_int(name: str, default: int) -> int:
    """
    Internal helper to safely parse integer environment variables.

    Returns default if the environment variable is missing or invalid.
    """
    try:
        value = int(os.getenv(name, str(default)))
        return value
    except (TypeError, ValueError):
        return default


def _build_engine() -> Engine:
    """
    Create SQLAlchemy engine based on environment variables.

    - DATABASE_URL: required for DB address; defaults to local sqlite file
    - DB_POOL_SIZE, DB_MAX_OVERFLOW: used for non-SQLite pooling configuration
    """
    database_url = os.getenv("DATABASE_URL", "sqlite:///./employees.db")

    # Default options for all engines
    engine_kwargs: dict = {
        "pool_pre_ping": True,  # proactively validate connections from pool
        # echo can be enabled for debugging by setting SQLALCHEMY_ECHO=1
        "echo": bool(int(os.getenv("SQLALCHEMY_ECHO", "0"))),
    }

    if database_url.startswith("sqlite"):
        # SQLite specific configuration
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        # Pooling settings are not applicable for SQLite memory/file DBs in most cases
    else:
        # Apply pooling config only for non-SQLite databases
        engine_kwargs["pool_size"] = _get_env_int("DB_POOL_SIZE", 5)
        engine_kwargs["max_overflow"] = _get_env_int("DB_MAX_OVERFLOW", 10)

    try:
        engine = create_engine(database_url, **engine_kwargs)
    except SQLAlchemyError as exc:
        # Fail fast with a meaningful error to aid diagnostics without leaking secrets
        raise RuntimeError("Failed to create SQLAlchemy engine. Check DATABASE_URL and connectivity.") from exc

    return engine


# Create a module-level engine and session factory
engine: Engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session for request-scoped operations.

    Yields
    ------
    sqlalchemy.orm.Session
        An active session bound to the configured engine. The session is closed
        after use to avoid connection leaks.

    Usage
    -----
    - In FastAPI, use as a dependency: `Depends(get_db)`
    - In scripts, use as a context manager pattern:
        ```
        db = next(get_db())
        try:
            ...
        finally:
            db.close()
        ```

    Notes
    -----
    - Do not long-hold sessions; keep transactions short to reduce contention.
    """
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        yield db
    finally:
        # Ensure the session is closed even if an exception occurs in the caller
        if db is not None:
            try:
                db.close()
            except SQLAlchemyError:
                # Avoid raising during cleanup; log here if a central logger exists
                pass
