"""
Auth router providing signup, login, and current user endpoints.

This module exposes:
- POST /auth/signup: Create new user with unique email
- POST /auth/login: Authenticate and return JWT bearer token
- GET /auth/me: Return current authenticated user using Bearer token

All public interfaces are documented and include structured responses. Errors are centrally
handled in src.api.main to provide standardized JSON payloads and CORS headers.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.user import Token, UserCreate, UserLogin, UserRead
from src.services.auth_service import get_current_user, login_user, signup_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up a new user",
    description="Create a new user account with unique email.",
)
# PUBLIC_INTERFACE
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user.

    Parameters
    ----------
    payload : UserCreate
        The user details including email, password, and optional full name.
    db : Session
        Database session dependency.

    Returns
    -------
    UserRead
        The created user record (without sensitive fields).
    """
    user = signup_user(db, email=payload.email, password=payload.password, full_name=payload.full_name)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate with email and password to obtain a JWT bearer token.",
)
# PUBLIC_INTERFACE
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return an access token.

    Parameters
    ----------
    payload : UserLogin
        Email and password credentials.
    db : Session
        Database session dependency.

    Returns
    -------
    Token
        JWT bearer token (access_token) and token_type.
    """
    token = login_user(db, email=payload.email, password=payload.password)
    return Token(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Retrieve the current authenticated user's profile using the provided JWT.",
)
# PUBLIC_INTERFACE
def me(current_user=Depends(get_current_user)):
    """
    Retrieve details about the current user.

    Parameters
    ----------
    current_user : User (injected via dependency)
        The authenticated user resolved from the JWT.

    Returns
    -------
    UserRead
        Public-safe representation of the current user.
    """
    return UserRead.model_validate(current_user)
