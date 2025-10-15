"""
Employee repository encapsulating SQLAlchemy queries with pagination and filters.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.employee import Employee, EmployeeStatus


class EmployeeEmailAlreadyExistsError(Exception):
    """Raised when an employee email uniqueness constraint is violated."""


class InvalidSortError(Exception):
    """Raised when a sort parameter is invalid (unsupported field or direction)."""


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


def _apply_sort(stmt: Select, sort: Optional[str]) -> Select:
    """
    Apply ordering to the query based on a sort string.

    Supported formats:
    - "field" (ascending)
    - "field:asc" or "field:desc"
    - "-field" (descending shorthand)

    Supported fields: id, first_name, last_name, email, department, title,
    salary, date_hired, status, created_at, updated_at

    Default: order by id desc (newest first).
    """
    # Default sort
    if not sort or not sort.strip():
        return stmt.order_by(desc(Employee.id))

    raw = sort.strip()

    # Initialize defaults
    direction = "asc"
    field = raw

    # Shorthand for descending: "-field"
    if raw.startswith("-") and len(raw) > 1:
        field = raw[1:]
        direction = "desc"

    # Explicit "field:asc|desc"
    if ":" in field:
        base, dir_part = field.split(":", 1)
        field = base
        if dir_part.lower() in {"asc", "desc"}:
            direction = dir_part.lower()
        else:
            raise InvalidSortError("Invalid sort direction; use 'asc' or 'desc'.")

    field = field.strip().lower()

    sortable = {
        "id": Employee.id,
        "first_name": Employee.first_name,
        "last_name": Employee.last_name,
        "email": Employee.email,
        "department": Employee.department,
        "title": Employee.title,
        "salary": Employee.salary,
        "date_hired": Employee.date_hired,
        "status": Employee.status,
        "created_at": Employee.created_at,
        "updated_at": Employee.updated_at,
    }

    col = sortable.get(field)
    if col is None:
        raise InvalidSortError("Invalid sort field.")

    return stmt.order_by(asc(col) if direction == "asc" else desc(col))


# PUBLIC_INTERFACE
def list_employees(
    db: Session,
    page: int,
    size: int,
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[EmployeeStatus] = None,
    sort: Optional[str] = None,
) -> Tuple[List[Employee], int]:
    """Return a page of employees with total count."""
    base_stmt = select(Employee)
    filtered_stmt = _apply_filters(base_stmt, search, department, status)

    # Count query must not include limit/offset but should include filters
    count_stmt = select(func.count()).select_from(filtered_stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Sorting
    sorted_stmt = _apply_sort(filtered_stmt, sort)

    # Pagination
    offset = (page - 1) * size
    paged_stmt = sorted_stmt.offset(offset).limit(size)

    rows = db.execute(paged_stmt).scalars().all()
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
