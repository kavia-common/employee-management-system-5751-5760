"""
Pydantic models for Employee entities and query parameters.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, conint, field_validator

from src.models.employee import EmployeeStatus


class EmployeeBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=120, description="Employee first name")
    last_name: str = Field(..., min_length=1, max_length=120, description="Employee last name")
    email: EmailStr = Field(..., description="Employee unique email")
    phone: Optional[str] = Field(None, max_length=32, description="Contact phone number")
    department: Optional[str] = Field(None, max_length=120, description="Department name")
    title: Optional[str] = Field(None, max_length=120, description="Job title")
    manager_id: Optional[int] = Field(None, description="Manager employee ID")
    salary: Optional[float] = Field(None, ge=0, description="Salary amount (non-negative)")
    date_hired: Optional[date] = Field(None, description="Date when hired")
    status: EmployeeStatus = Field(default=EmployeeStatus.ACTIVE, description="Employment status")


class EmployeeCreate(EmployeeBase):
    """Payload for creating an employee."""
    pass


class EmployeeUpdate(BaseModel):
    """Payload for updating employee fields; all optional."""
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


class EmployeeRead(BaseModel):
    """Employee data returned to clients."""
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str]
    department: Optional[str]
    title: Optional[str]
    manager_id: Optional[int]
    salary: Optional[float]
    date_hired: Optional[date]
    status: EmployeeStatus

    class Config:
        from_attributes = True


class Pagination(BaseModel):
    """Pagination metadata for list responses."""
    total: int
    page: int
    size: int
    pages: int


class EmployeeListResponse(BaseModel):
    """Response model for employee list endpoints with pagination."""
    data: List[EmployeeRead]
    pagination: Pagination


class EmployeeQueryParams(BaseModel):
    """Query params for listing employees with pagination and filtering."""
    page: conint(ge=1) = Field(1, description="Page number starting from 1")
    size: conint(ge=1, le=100) = Field(10, description="Page size (1-100)")
    search: Optional[str] = Field(None, description="Search term for name or email")
    department: Optional[str] = Field(None, description="Filter by department")
    status: Optional[EmployeeStatus] = Field(None, description="Filter by employee status")

    @field_validator("search")
    @classmethod
    def validate_search(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            return None
        return v
