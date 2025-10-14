"""
Auth router providing signup, login, and current user endpoints.
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
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user.

    Parameters
    ----------
    payload : UserCreate
        The user details including email, password, and optional full name.

    Returns
    -------
    UserRead
        The created user record (without sensitive fields).
    """
    print("---->1 user", payload)
    user = signup_user(db, email=payload.email, password=payload.password, full_name=payload.full_name)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate with email and password to obtain a JWT bearer token.",
)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return an access token.
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
def me(current_user=Depends(get_current_user)):
    """
    Retrieve details about the current user.
    """
    return UserRead.model_validate(current_user)
