"""
Auth router [STUB].

This module preserves the authentication API surface while providing
a deterministic in-memory implementation using a mock store. There is
NO real password hashing or JWT validation in this stub.

Endpoints:
- POST /auth/signup: Create a user if it doesn't exist; return user data
- POST /auth/login: Validate minimal input and return a fake bearer token
- POST /auth/logout: No-op, returns a simple payload
- GET /auth/me: Return current user details parsed from fake token
"""
from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException, status

from app.models.schemas import LoginRequest, SignupRequest
from app.services.mock_store import store

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    summary="[STUB] Sign up a new user",
    description="Create a new user account with unique email. [STUB: in-memory, no hashing]",
    status_code=status.HTTP_201_CREATED,
)
# PUBLIC_INTERFACE
def signup(payload: SignupRequest = Body(...)) -> Dict:
    """Create a user in the in-memory store. [STUB]"""
    # Minimal validation is enforced by Pydantic model.
    exists = store.get_user_by_email(payload.email)
    if exists:
        # 409 to indicate conflict (email already exists)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )
    user = store.create_user(email=payload.email, password=payload.password)
    # Response mirrors a typical public user payload (no sensitive fields)
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user.get("full_name"),
        "is_active": True,
    }


@router.post(
    "/login",
    summary="[STUB] User login",
    description=(
        "Authenticate using email and password to obtain a bearer token. "
        "[STUB: deterministic fake token; no password hashing or JWT]"
    ),
)
# PUBLIC_INTERFACE
def login(payload: LoginRequest = Body(...)) -> Dict[str, object]:
    """Return a fake token if credentials match a known in-memory user. [STUB]"""
    user = store.get_user_by_email(payload.email)
    if not user or user["password"] != payload.password:
        # 401 for invalid credentials; standardized envelope handled by global exception handler
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = f"fake-jwt-{user['id']}"
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"]},
    }


def _parse_user_id_from_token(authorization: Optional[str]) -> Optional[int]:
    """
    Utility: parse fake token in the form 'Bearer fake-jwt-<id>' and return the user id.
    """
    if not authorization:
        return None
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        if not token.startswith("fake-jwt-"):
            return None
        user_id = int(token.replace("fake-jwt-", "", 1))
        return user_id
    except Exception:
        return None


@router.get(
    "/me",
    summary="[STUB] Get current user",
    description="Return current user information using a fake bearer token. [STUB]",
)
# PUBLIC_INTERFACE
def me(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> Dict:
    """
    Return current user data by parsing the fake JWT from the Authorization header.

    Raises:
        HTTPException 401 when the token is missing/invalid or user cannot be found.
    """
    user_id = _parse_user_id_from_token(authorization)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = None
    # The mock store only supports lookup by email; emulate by scanning
    # This is acceptable for stub environments but not for production.
    for candidate in store._users.values():  # noqa: SLF001 - acceptable for stub
        if candidate.get("id") == user_id:
            user = candidate
            break
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user.get("full_name"),
        "is_active": user.get("is_active", True),
    }


@router.post(
    "/logout",
    summary="[STUB] User logout",
    description="No-op logout endpoint for client flows. [STUB]",
)
# PUBLIC_INTERFACE
def logout() -> Dict[str, str]:
    """Return a simple message indicating logout. [STUB]"""
    return {"message": "logged out"}
