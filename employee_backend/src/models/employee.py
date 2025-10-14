"""
Employee model definition.

Represents employees managed by the system, with organizational data, contact
details, compensation metadata, and employment status. Includes a self-referential
foreign key to represent manager/subordinate relationships.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class EmployeeStatus(str, enum.Enum):
    """Enumerated employment statuses."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# PUBLIC_INTERFACE
class Employee(Base):
    """Employee entity with organizational context and metadata."""

    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("email", name="uq_employees_email"),
        # Additional multi-column or named indexes can be added as needed
        Index("ix_employees_department", "department"),
        Index("ix_employees_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identity and contact
    first_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Organization and role
    department: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    manager_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Compensation and employment
    salary: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    date_hired: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[EmployeeStatus] = mapped_column(
        SAEnum(EmployeeStatus, name="employee_status"),
        nullable=False,
        default=EmployeeStatus.ACTIVE,
        server_default=EmployeeStatus.ACTIVE.value,
    )

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # ORM relationship for managerial hierarchy
    manager: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        remote_side="Employee.id",
        backref="subordinates",
        uselist=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - repr primarily for debugging
        return (
            f"Employee(id={self.id!r}, name={self.first_name!r} {self.last_name!r}, "
            f"status={self.status!r}, department={self.department!r})"
        )
