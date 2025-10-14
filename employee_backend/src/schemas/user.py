"""
Pydantic models for User entities and auth flows.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user fields used across schemas."""
    email: EmailStr = Field(..., description="Unique email address of the user")
    full_name: str | None = Field(None, max_length=255, description="Full name of the user")


class UserCreate(UserBase):
    """User creation payload with password."""
    password: str = Field(..., min_length=8, max_length=128, description="User password (min 8 chars)")


class UserLogin(BaseModel):
    """User login payload with credentials."""
    email: EmailStr = Field(..., description="Email used for login")
    password: str = Field(..., min_length=8, max_length=128, description="Password used for login")


class UserRead(UserBase):
    """Public user data returned to clients (no sensitive fields)."""
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    """OAuth2-like token response."""
    access_token: str = Field(..., description="JWT bearer token")
    token_type: str = Field(default="bearer", description="Token type, always 'bearer'")
