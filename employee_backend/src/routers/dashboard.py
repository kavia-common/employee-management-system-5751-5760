"""
Dashboard router providing summary statistics for employees.
"""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.employee import Employee, EmployeeStatus
from src.services.auth_service import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    status_code=status.HTTP_200_OK,
    summary="Summary statistics",
    description="Return total employee count and counts by status.",
)
def summary(db: Session = Depends(get_db), _=Depends(get_current_user)) -> Dict[str, int]:
    """
    Return overall employee counts.
    """
    total = db.scalar(select(func.count()).select_from(Employee)) or 0
    active = db.scalar(select(func.count()).where(Employee.status == EmployeeStatus.ACTIVE)) or 0
    inactive = db.scalar(select(func.count()).where(Employee.status == EmployeeStatus.INACTIVE)) or 0
    return {"total": int(total), "active": int(active), "inactive": int(inactive)}


@router.get(
    "/department-stats",
    status_code=status.HTTP_200_OK,
    summary="Department statistics",
    description="Return counts of employees per department.",
)
def department_stats(db: Session = Depends(get_db), _=Depends(get_current_user)) -> List[dict]:
    """
    Return counts per department.
    """
    stmt = select(Employee.department, func.count()).group_by(Employee.department)
    rows = db.execute(stmt).all()
    # Exclude None departments
    stats = [{"department": d, "count": int(c)} for d, c in rows if d is not None]
    return stats
