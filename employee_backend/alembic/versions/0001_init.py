"""Initial schema: users and employees tables with constraints and indexes.

Revision ID: 0001
Revises: 
Create Date: 2025-01-01 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Create employees table
    employee_status = sa.Enum("ACTIVE", "INACTIVE", name="employee_status")
    employee_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("department", sa.String(length=120), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("manager_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("salary", sa.Numeric(12, 2), nullable=True),
        sa.Column("date_hired", sa.Date(), nullable=True),
        sa.Column("status", employee_status, nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_employees_email"),
    )
    op.create_index("ix_employees_email", "employees", ["email"], unique=True)
    op.create_index("ix_employees_department", "employees", ["department"], unique=False)
    op.create_index("ix_employees_status", "employees", ["status"], unique=False)


def downgrade() -> None:
    # Drop indexes and tables in reverse order
    op.drop_index("ix_employees_status", table_name="employees")
    op.drop_index("ix_employees_department", table_name="employees")
    op.drop_index("ix_employees_email", table_name="employees")
    op.drop_table("employees")

    # Drop the enum type if supported (e.g., PostgreSQL)
    employee_status = sa.Enum("ACTIVE", "INACTIVE", name="employee_status")
    bind = op.get_bind()
    try:
        employee_status.drop(bind, checkfirst=True)
    except Exception:
        # Some dialects (like SQLite) do not support dropping enums; ignore safely
        pass

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
