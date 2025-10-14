"""
Security utilities for authentication and authorization.

Includes:
- Password hashing and verification using bcrypt via Passlib.
- JWT token creation and validation using python-jose.

Security considerations:
- Do not log sensitive data (passwords, tokens, user emails).
- Token expiration is enforced to reduce risk from leaked tokens.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from passlib.context import CryptContext

from src.core.config import settings

# Configure Passlib crypt context for bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(plain_password: str) -> str:
    """Return a salted bcrypt hash for the supplied plaintext password."""
    if not isinstance(plain_password, str) or not plain_password:
        raise ValueError("Invalid password input")
    return pwd_context.hash(plain_password)


# PUBLIC_INTERFACE
def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    if not plain_password or not password_hash:
        return False
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception:
        # Avoid throwing details; treat as verification failure
        return False


# PUBLIC_INTERFACE
def create_access_token(subject: str, expires_minutes: Optional[int] = None, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a signed JWT access token.

    Parameters
    ----------
    subject : str
        The subject (typically a user ID) for whom the token is issued.
    expires_minutes : int | None
        How many minutes until the token expires. Uses settings default if None.
    extra_claims : dict | None
        Additional claims to include in the token payload (avoid PII).

    Returns
    -------
    str
        The encoded JWT string.
    """
    if not subject:
        raise ValueError("Token subject is required")

    to_encode: Dict[str, Any] = {"sub": subject}
    if extra_claims:
        # Merge but avoid overwriting reserved keys
        for k, v in extra_claims.items():
            if k not in {"exp", "sub", "iat"}:
                to_encode[k] = v

    expire_minutes = expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(minutes=int(expire_minutes))
    to_encode.update({"iat": int(now.timestamp()), "exp": int(expire.timestamp())})

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


# PUBLIC_INTERFACE
def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Returns the payload dictionary if valid, raises JWTError otherwise.
    """
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return payload


class InvalidTokenError(Exception):
    """Domain exception indicating an invalid or expired token."""

    pass
