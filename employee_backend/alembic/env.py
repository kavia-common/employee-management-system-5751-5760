"""
Alembic environment configuration.

- Loads DATABASE_URL from environment variables (via python-dotenv for dev).
- Registers SQLAlchemy ORM models' metadata for autogeneration.
- Supports both offline (script) and online (DB) migration modes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure 'src' package is importable when running alembic from container root
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Load env vars (local dev) and obtain URL
load_dotenv(PROJECT_ROOT / ".env")

# Import ORM base after sys.path is configured
from src.db.base import Base  # noqa: E402


# For 'autogenerate' support, set target_metadata to your model's MetaData object.
target_metadata = Base.metadata


def _get_database_url() -> str:
    """Resolve the database URL from environment with a safe default for dev."""
    return os.getenv("DATABASE_URL", "sqlite:///./employees.db")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode. Emits SQL statements to the script output."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # detect column type changes
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode. Connects to the database and runs migrations."""
    configuration = context.config.get_section(context.config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Alembic uses its own connection; no long-lived pool needed
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
