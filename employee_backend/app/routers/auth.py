"""
Auth router [STUB].

This module preserves the authentication API surface while providing
a deterministic in-memory implementation using a mock store. There is
NO real password hashing or JWT validation in this stub.

Endpoints:
- POST /auth/signup: Create a user if it doesn't exist; return user data
- POST /auth/login: Validate minimal input and return a fake bearer token
- POST /auth/logout: No-op, returns a simple payload
"""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Body, HTTPException, status


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
def login(payload: LoginRequest = Body(...)) -> Dict[str, str]:
    """Return a fake token if credentials match a known in-memory user. [STUB]"""
    user = store.get_user_by_email(payload.email)
    if not user or user["password"] != payload.password:
        # 401 for invalid credentials
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = f"fake-jwt-{user['id']}"
    return {"access_token": token, "token_type": "bearer", "user": {"id": user["id"], "email": user["email"]}}


@router.post(
    "/logout",
    summary="[STUB] User logout",
    description="No-op logout endpoint for client flows. [STUB]",
)
# PUBLIC_INTERFACE
def logout() -> Dict[str, str]:
    """Return a simple message indicating logout. [STUB]"""
    return {"message": "logged out"}
