"""
Declarative base configuration for SQLAlchemy models.

- Establishes metadata naming conventions to ensure stable Alembic diffs.
- Exposes a single Base class to be extended by all ORM models.
- Imports model modules to register them with Base.metadata for Alembic.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming conventions help Alembic consistently generate migration names and avoid diffs churn
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for ORM models with standardized metadata."""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Import models so their tables are registered with Base.metadata (important for Alembic)
# These imports have side-effects only; they are intentionally unused symbols.
# pylint: disable=unused-import, wrong-import-position
try:
    from src.models import user  # noqa: F401
    from src.models import employee  # noqa: F401
except Exception:
    # During certain tooling operations these imports may fail if paths aren't configured yet.
    # Alembic's env.py ensures proper sys.path so this generally loads in migration context.
    pass
