"""pre-deploy schema check (SAFE FIX)

Revision ID: fe5393294599
Revises: 5885062792d4
Create Date: 2026-01-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "fe5393294599"
down_revision: Union[str, Sequence[str], None] = "5885062792d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------
    # Doctor Availability
    # -----------------------------
    op.create_table(
        "doctor_availability",
        sa.Column(
            "day_of_week",
            sa.Enum(
                "MONDAY",
                "TUESDAY",
                "WEDNESDAY",
                "THURSDAY",
                "FRIDAY",
                "SATURDAY",
                "SUNDAY",
                name="dayofweek",
            ),
            nullable=False,
        ),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_patients_per_slot", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_doctor_availability",
        "doctor_availability",
        ["doctor_id", "day_of_week", "is_available"],
    )
    op.create_index(
        "idx_doctor_day",
        "doctor_availability",
        ["doctor_id", "day_of_week"],
    )
    op.create_index(
        op.f("ix_doctor_availability_doctor_id"),
        "doctor_availability",
        ["doctor_id"],
    )

    # -----------------------------
    # Patient table changes (SAFE)
    # -----------------------------
    op.add_column(
        "patient",
        sa.Column("cnic", sa.String(length=15), nullable=True),
    )
    op.add_column(
        "patient",
        sa.Column("phone_secondary", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "patient",
        sa.Column("residential_address", sa.Text(), nullable=True),
    )
    op.add_column(
        "patient",
        sa.Column("postal_address", sa.Text(), nullable=True),
    )
    op.add_column(
        "patient",
        sa.Column("city", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "patient",
        sa.Column(
            "payment_status",
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "patient",
        sa.Column("current_medications", sa.Text(), nullable=True),
    )
    op.add_column(
        "patient",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=True,
            server_default=sa.true(),
        ),
    )

    # Optional: enforce NOT NULL on phone only if safe
    op.alter_column(
        "patient",
        "phone",
        existing_type=sa.VARCHAR(length=20),
        nullable=False,
    )

    # Unique constraint for CNIC (allows NULLs)
    op.create_unique_constraint(
        "uq_patient_cnic",
        "patient",
        ["cnic"],
    )

    # ⚠️ DO NOT drop audit_log
    # ⚠️ DO NOT drop address column automatically
    # (remove later in a dedicated cleanup migration)


def downgrade() -> None:
    # Downgrade intentionally limited to avoid data loss
    op.drop_constraint("uq_patient_cnic", "patient", type_="unique")

    op.drop_column("patient", "is_active")
    op.drop_column("patient", "current_medications")
    op.drop_column("patient", "payment_status")
    op.drop_column("patient", "city")
    op.drop_column("patient", "postal_address")
    op.drop_column("patient", "residential_address")
    op.drop_column("patient", "phone_secondary")
    op.drop_column("patient", "cnic")

    op.drop_index(op.f("ix_doctor_availability_doctor_id"), table_name="doctor_availability")
    op.drop_index("idx_doctor_day", table_name="doctor_availability")
    op.drop_index("idx_doctor_availability", table_name="doctor_availability")
    op.drop_table("doctor_availability")
