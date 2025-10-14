"""
Employees router [STUB].

This module preserves the employees API surface while providing in-memory
CRUD operations with deterministic seed data. It supports:
- List with pagination (page, page_size) and simple filter by 'q'
- Create (unique email)
- Read by ID
- Update
- Delete
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Path, Query, status

from app.models.schemas import (
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
    PaginatedEmployees,
)
from app.services.mock_store import store

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get(
    "",
    summary="[STUB] List employees",
    description="List employees with pagination and optional 'q' search across name/email. [STUB]",
    response_model=PaginatedEmployees,
)
# PUBLIC_INTERFACE
def list_employees(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    q: Optional[str] = Query(None, description="Search term (name or email contains)"),
) -> PaginatedEmployees:
    """Return a paginated list of employees using in-memory data. [STUB]"""
    results = store.search_employees(query=q or "")
    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = results[start:end]
    pages = (total + page_size - 1) // page_size if page_size else 1
    return PaginatedEmployees(
        data=[EmployeeOut(**e) for e in page_items],
        pagination={"total": total, "page": page, "page_size": page_size, "pages": pages or 1},
    )


@router.post(
    "",
    summary="[STUB] Create employee",
    description="Create a new employee record with unique email. [STUB]",
    status_code=status.HTTP_201_CREATED,
    response_model=EmployeeOut,
)
# PUBLIC_INTERFACE
def create_employee(payload: EmployeeCreate = Body(...)) -> EmployeeOut:
    """Create an employee in the in-memory store. [STUB]"""
    if store.get_employee_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee with this email already exists")
    emp = store.create_employee(payload.model_dump())
    return EmployeeOut(**emp)


@router.get(
    "/{employee_id}",
    summary="[STUB] Get employee by ID",
    description="Retrieve an employee by ID. [STUB]",
    response_model=EmployeeOut,
)
# PUBLIC_INTERFACE
def get_employee(
    employee_id: int = Path(..., ge=1, description="Employee ID"),
) -> EmployeeOut:
    """Get an employee by ID. [STUB]"""
    emp = store.get_employee(employee_id)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return EmployeeOut(**emp)


@router.put(
    "/{employee_id}",
    summary="[STUB] Update employee",
    description="Update an existing employee record. [STUB]",
    response_model=EmployeeOut,
)
# PUBLIC_INTERFACE
def update_employee(
    employee_id: int = Path(..., ge=1, description="Employee ID"),
    payload: EmployeeUpdate = Body(...),
) -> EmployeeOut:
    """Update employee fields. [STUB]"""
    emp = store.get_employee(employee_id)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    updated = store.update_employee(employee_id, payload.model_dump(exclude_unset=True))
    return EmployeeOut(**updated)


@router.delete(
    "/{employee_id}",
    summary="[STUB] Delete employee",
    description="Delete an employee by ID. [STUB]",
    status_code=status.HTTP_204_NO_CONTENT,
)
# PUBLIC_INTERFACE
def delete_employee(
    employee_id: int = Path(..., ge=1, description="Employee ID"),
) -> None:
    """Delete an employee by ID. Returns 204 on success. [STUB]"""
    emp = store.get_employee(employee_id)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    store.delete_employee(employee_id)
    return None
