"""
Authentication service encapsulating user signup, login, and token-based current user retrieval.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.security import create_access_token, hash_password, verify_password
from src.db.session import get_db
from src.repositories.user_repository import EmailAlreadyExistsError, create_user, get_user_by_email, get_user_by_id

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


# PUBLIC_INTERFACE
def signup_user(db: Session, email: str, password: str, full_name: Optional[str] = None):
    """Create a new user ensuring uniqueness."""
    # Hashing may fail if bcrypt backend is unavailable or misconfigured.
    try:
        password_hash = hash_password(password)
    except Exception:
        # Log without sensitive details and return standardized server error.
        logger.exception("Password hashing failed during signup")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    try:
        user = create_user(db, email=email, password_hash=password_hash, full_name=full_name)
        return user
    except EmailAlreadyExistsError:
        # Do not log email (PII). Return 409 Conflict per acceptance criteria.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")


# PUBLIC_INTERFACE
def login_user(db: Session, email: str, password: str) -> str:
    """Validate credentials and return a JWT access token."""
    user = get_user_by_email(db, email=email)
    if not user or not verify_password(password, user.password_hash):
        # Avoid user enumeration; return generic error
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(subject=str(user.id))
    return token


# PUBLIC_INTERFACE
def get_current_user(
    db: Session = Depends(get_db), credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    """
    FastAPI dependency to retrieve the current user from a Bearer token.

    Validates JWT, extracts subject (user id), and fetches user from DB.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    from src.core.security import decode_access_token, InvalidTokenError  # lazy import to avoid cycles

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidTokenError("Missing subject")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return user
