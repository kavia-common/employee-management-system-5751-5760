"""
Pydantic models for the [STUB] backend.

Defines request/response schemas for:
- Auth: LoginRequest, SignupRequest
- Employees: EmployeeCreate, EmployeeUpdate, EmployeeOut
- Pagination wrapper: PaginatedEmployees
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class EmployeeStatus(str, Enum):
    """Enumerated employment status for stub responses."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# PUBLIC_INTERFACE
class LoginRequest(BaseModel):
    """Login request payload. [STUB]"""

    email: EmailStr = Field(..., description="Login email")
    password: str = Field(..., min_length=6, max_length=128, description="Login password (min 6 chars)")


# PUBLIC_INTERFACE
class SignupRequest(BaseModel):
    """Signup request payload. [STUB]"""

    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password (min 6 chars)")


# PUBLIC_INTERFACE
class EmployeeCreate(BaseModel):
    """Create employee payload. [STUB]"""

    first_name: str = Field(..., min_length=1, max_length=120, description="First name")
    last_name: str = Field(..., min_length=1, max_length=120, description="Last name")
    email: EmailStr = Field(..., description="Unique email")
    phone: Optional[str] = Field(None, max_length=32, description="Phone number")
    department: Optional[str] = Field(None, max_length=120, description="Department")
    title: Optional[str] = Field(None, max_length=120, description="Job title")
    manager_id: Optional[int] = Field(None, description="Manager employee ID")
    salary: Optional[float] = Field(None, ge=0, description="Salary (non-negative)")
    date_hired: Optional[date] = Field(None, description="Date hired")
    status: EmployeeStatus = Field(default=EmployeeStatus.ACTIVE, description="Employment status")


# PUBLIC_INTERFACE
class EmployeeUpdate(BaseModel):
    """Update employee payload (all fields optional). [STUB]"""

    first_name: Optional[str] = Field(None, min_length=1, max_length=120)
    last_name: Optional[str] = Field(None, min_length=1, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=32)
    department: Optional[str] = Field(None, max_length=120)
    title: Optional[str] = Field(None, max_length=120)
    manager_id: Optional[int] = None
    salary: Optional[float] = Field(None, ge=0)
    date_hired: Optional[date] = None
    status: Optional[EmployeeStatus] = None


# PUBLIC_INTERFACE
class EmployeeOut(BaseModel):
    """Employee response model returned to clients. [STUB]"""

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    manager_id: Optional[int] = None
    salary: Optional[float] = None
    date_hired: Optional[date] = None
    status: EmployeeStatus

    @property
    def name(self) -> str:
        """Computed name helper (not serialized). [STUB]"""
        return f"{self.first_name} {self.last_name}"


# PUBLIC_INTERFACE
class PaginationMeta(BaseModel):
    """Pagination metadata. [STUB]"""

    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Page size")
    pages: int = Field(..., ge=1, description="Total number of pages")


# PUBLIC_INTERFACE
class PaginatedEmployees(BaseModel):
    """Paginated employees response wrapper. [STUB]"""

    data: List[EmployeeOut]
    pagination: PaginationMeta
