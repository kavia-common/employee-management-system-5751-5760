"""
Employees router providing protected CRUD operations with pagination and filtering.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.employee import EmployeeStatus
from src.schemas.employee import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeRead,
    EmployeeUpdate,
    Pagination,
)
from src.services.auth_service import get_current_user
from src.services.employee_service import (
    create_employee_record,
    delete_employee_record,
    get_employee_record,
    list_employee_records,
    update_employee_record,
)

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get(
    "",
    response_model=EmployeeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List employees",
    description="List employees with pagination and optional search/filters.",
)
def list_employees_api(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, description="Search term applied to first/last name or email"),
    department: str | None = Query(None, description="Filter by department"),
    status_filter: EmployeeStatus | None = Query(None, alias="status", description="Filter by employment status"),
    sort: str | None = Query(
        None,
        description=(
            "Sort order. Examples: 'last_name', 'last_name:desc', '-date_hired'. "
            "Allowed fields: id, first_name, last_name, email, department, title, "
            "salary, date_hired, status, created_at, updated_at. Defaults to '-id'."
        ),
    ),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    List employees.

    Query Parameters
    ----------------
    page : int
        Page number starting from 1
    size : int
        Page size (1-100)
    search : str | None
        Search term applied to name and email
    department : str | None
        Department filter
    status : EmployeeStatus | None
        Status filter (ACTIVE/INACTIVE)
    sort : str | None
        Sort specifier, e.g., 'last_name:asc' or '-date_hired'. Defaults to '-id'.
    """
    rows, total, page_num, pages = list_employee_records(
        db,
        page=page,
        size=size,
        search=search,
        department=department,
        status=status_filter,
        sort=sort,
    )
    data = [EmployeeRead.model_validate(r) for r in rows]
    return EmployeeListResponse(
        data=data, pagination=Pagination(total=total, page=page_num, size=size, pages=pages)
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeRead,
    status_code=status.HTTP_200_OK,
    summary="Get employee by ID",
    description="Retrieve an employee by their unique identifier.",
)
def get_employee_api(employee_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Get a single employee by ID."""
    employee = get_employee_record(db, employee_id)
    return EmployeeRead.model_validate(employee)


@router.post(
    "",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create employee",
    description="Create a new employee record.",
)
def create_employee_api(payload: EmployeeCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Create a new employee."""
    employee = create_employee_record(db, data=payload.model_dump())
    return EmployeeRead.model_validate(employee)


@router.put(
    "/{employee_id}",
    response_model=EmployeeRead,
    status_code=status.HTTP_200_OK,
    summary="Update employee",
    description="Update an existing employee record.",
)
def update_employee_api(
    employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)
):
    """Update an employee by ID."""
    employee = update_employee_record(db, employee_id=employee_id, data=payload.model_dump(exclude_unset=True))
    return EmployeeRead.model_validate(employee)


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete employee",
    description="Delete an employee record by ID.",
)
def delete_employee_api(employee_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Delete an employee by ID."""
    delete_employee_record(db, employee_id)
    return None
