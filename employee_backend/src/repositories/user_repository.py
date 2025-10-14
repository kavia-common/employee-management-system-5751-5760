"""
User repository encapsulating database operations for User entities.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.user import User


class EmailAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an email that already exists."""


# PUBLIC_INTERFACE
def create_user(db: Session, email: str, password_hash: str, full_name: str | None = None) -> User:
    """Create a new user with uniqueness enforcement on email."""
    user = User(email=email, password_hash=password_hash, full_name=full_name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # The unique constraint on email was violated
        raise EmailAlreadyExistsError from exc
    db.refresh(user)
    return user


# PUBLIC_INTERFACE
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Fetch a user by email, or None if not found."""
    stmt = select(User).where(User.email == email)
    return db.scalar(stmt)


# PUBLIC_INTERFACE
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Fetch a user by primary key, or None if not found."""
    stmt = select(User).where(User.id == user_id)
    return db.scalar(stmt)
