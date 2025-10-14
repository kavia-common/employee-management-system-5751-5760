"""
User model definition.

Represents application users for authentication and authorization. Stores hashed
passwords (never plaintext), identity attributes, and lifecycle flags.

Security:
- Only store password hashes (e.g., bcrypt). Do NOT store plaintext passwords.
- Do not expose PII in logs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


# PUBLIC_INTERFACE
class User(Base):
    """Application user entity."""

    __tablename__ = "users"
    __table_args__ = (
        # Enforce email uniqueness at the database layer
        UniqueConstraint("email", name="uq_users_email"),
    )

    # Surrogate key primary identifier
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Business attributes
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover - repr primarily for debugging
        return f"User(id={self.id!r}, email={self.email!r}, is_active={self.is_active!r})"
