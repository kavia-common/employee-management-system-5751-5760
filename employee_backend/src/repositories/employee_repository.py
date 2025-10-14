"""
Employee repository encapsulating SQLAlchemy queries with pagination and filters.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.employee import Employee, EmployeeStatus


class EmployeeEmailAlreadyExistsError(Exception):
    """Raised when an employee email uniqueness constraint is violated."""


def _apply_filters(
    stmt: Select,
    search: Optional[str],
    department: Optional[str],
    status: Optional[EmployeeStatus],
) -> Select:
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Employee.first_name).like(like),
                func.lower(Employee.last_name).like(like),
                func.lower(Employee.email).like(like),
            )
        )
    if department:
        stmt = stmt.where(Employee.department == department)
    if status:
        stmt = stmt.where(Employee.status == status)
    return stmt


# PUBLIC_INTERFACE
def list_employees(
    db: Session,
    page: int,
    size: int,
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[EmployeeStatus] = None,
) -> Tuple[List[Employee], int]:
    """Return a page of employees with total count."""
    stmt = select(Employee)
    stmt = _apply_filters(stmt, search, department, status)

    # Count query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Pagination
    offset = (page - 1) * size
    stmt = stmt.offset(offset).limit(size)

    rows = db.execute(stmt).scalars().all()
    return rows, int(total)


# PUBLIC_INTERFACE
def get_employee(db: Session, employee_id: int) -> Optional[Employee]:
    """Get a single employee by id."""
    stmt = select(Employee).where(Employee.id == employee_id)
    return db.scalar(stmt)


# PUBLIC_INTERFACE
def create_employee(db: Session, data: dict) -> Employee:
    """Create an employee record."""
    employee = Employee(**data)
    db.add(employee)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Unique email violated
        raise EmployeeEmailAlreadyExistsError from exc
    db.refresh(employee)
    return employee


# PUBLIC_INTERFACE
def update_employee(db: Session, employee: Employee, data: dict) -> Employee:
    """Update mutable fields of an employee."""
    for key, value in data.items():
        setattr(employee, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EmployeeEmailAlreadyExistsError from exc
    db.refresh(employee)
    return employee


# PUBLIC_INTERFACE
def delete_employee(db: Session, employee: Employee) -> None:
    """Delete an employee record."""
    db.delete(employee)
    db.commit()
