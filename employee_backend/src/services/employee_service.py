"""
Employee service implementing business logic for CRUD and listing with filters.
"""

from __future__ import annotations

from math import ceil
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.employee import Employee, EmployeeStatus
from src.repositories.employee_repository import (
    EmployeeEmailAlreadyExistsError,
    InvalidSortError,
    create_employee,
    delete_employee,
    get_employee,
    list_employees,
    update_employee,
)


# PUBLIC_INTERFACE
def list_employee_records(
    db: Session,
    page: int,
    size: int,
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[EmployeeStatus] = None,
    sort: Optional[str] = None,
) -> Tuple[list[Employee], int, int, int]:
    """Return employees and pagination meta (total, page, pages)."""
    try:
        rows, total = list_employees(
            db,
            page=page,
            size=size,
            search=search,
            department=department,
            status=status,
            sort=sort,
        )
    except InvalidSortError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    total_pages = ceil(total / size) if size else 1
    return rows, total, page, total_pages


# PUBLIC_INTERFACE
def get_employee_record(db: Session, employee_id: int) -> Employee:
    """Get a single employee or raise 404."""
    employee = get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


# PUBLIC_INTERFACE
def create_employee_record(db: Session, data: dict) -> Employee:
    """Create an employee with unique email handling."""
    try:
        return create_employee(db, data)
    except EmployeeEmailAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee email already exists")


# PUBLIC_INTERFACE
def update_employee_record(db: Session, employee_id: int, data: dict) -> Employee:
    """Update an employee with unique email handling."""
    employee = get_employee_record(db, employee_id)
    try:
        return update_employee(db, employee, data)
    except EmployeeEmailAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee email already exists")


# PUBLIC_INTERFACE
def delete_employee_record(db: Session, employee_id: int) -> None:
    """Delete an employee by id."""
    employee = get_employee_record(db, employee_id)
    delete_employee(db, employee)
