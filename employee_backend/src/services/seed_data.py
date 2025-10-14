"""
Development-only seed data helpers.

This module provides functions to insert sample data into the database
to support local development and demos. It MUST NOT run in production.

Security:
- No secrets are stored here.
- Seeding is guarded by environment checks in the caller.

Usage:
- Called from app startup in development if SEED_ON_STARTUP is enabled/defaulted.
"""
from __future__ import annotations

from datetime import date
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.employee import Employee, EmployeeStatus


def _has_any_employees(db: Session) -> bool:
    """Return True if the employees table contains any rows."""
    # Use exists-like check via select 1 limit 1 for portability
    row = db.execute(select(Employee.id).limit(1)).first()
    return row is not None


def _sample_employees() -> List[Employee]:
    """Construct a fixed set of sample employees for development."""
    return [
        Employee(
            first_name="Alice",
            last_name="Johnson",
            email="alice.johnson@example.com",
            phone="555-0101",
            department="Engineering",
            title="Software Engineer",
            salary=120000,
            status=EmployeeStatus.ACTIVE,
            date_hired=date(2022, 5, 12),
        ),
        Employee(
            first_name="Bob",
            last_name="Martinez",
            email="bob.martinez@example.com",
            phone="555-0102",
            department="Engineering",
            title="DevOps Engineer",
            salary=115000,
            status=EmployeeStatus.ACTIVE,
            date_hired=date(2021, 9, 1),
        ),
        Employee(
            first_name="Carol",
            last_name="Wong",
            email="carol.wong@example.com",
            phone="555-0103",
            department="Sales",
            title="Account Executive",
            salary=95000,
            status=EmployeeStatus.INACTIVE,
            date_hired=date(2020, 3, 3),
        ),
        Employee(
            first_name="David",
            last_name="Lee",
            email="david.lee@example.com",
            phone="555-0104",
            department="HR",
            title="HR Generalist",
            salary=80000,
            status=EmployeeStatus.ACTIVE,
            date_hired=date(2023, 1, 23),
        ),
        Employee(
            first_name="Emma",
            last_name="Brown",
            email="emma.brown@example.com",
            phone="555-0105",
            department="Engineering",
            title="QA Engineer",
            salary=90000,
            status=EmployeeStatus.ACTIVE,
            date_hired=date(2022, 11, 30),
        ),
    ]


# PUBLIC_INTERFACE
def seed_sample_employees_if_needed(db: Session) -> int:
    """
    Insert sample employees if the table is empty.

    Returns
    -------
    int
        Number of employees created (0 if no-op).
    """
    if _has_any_employees(db):
        return 0

    samples = _sample_employees()
    db.add_all(samples)
    db.commit()
    # Return count inserted
    return len(samples)
