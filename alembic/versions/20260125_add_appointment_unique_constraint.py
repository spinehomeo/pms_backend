"""Add UNIQUE constraint to prevent double booking

Revision ID: 20260125_add_appointment_unique_constraint
Revises: fe5393294599
Create Date: 2026-01-25

This migration adds a database-level constraint to prevent race condition double booking.
The constraint ensures no two appointments can be scheduled for the same doctor
at the same date and time (excluding cancelled appointments).

This provides production-grade safety at the DB level, preventing double-booking
even when concurrent requests arrive simultaneously.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260125_add_appointment_unique_constraint"
down_revision: Union[str, Sequence[str], None] = "fe5393294599"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add UNIQUE constraint on (doctor_id, appointment_date, appointment_time)
    where status != 'cancelled'
    
    This prevents two appointments from being scheduled for the same time slot,
    effectively preventing double-booking at the database level.
    """
    op.create_index(
        "idx_appointment_no_double_booking",
        "appointment",
        [
            "doctor_id",
            "appointment_date",
            "appointment_time",
        ],
        unique=True,
        postgresql_where=sa.text("status != 'cancelled'"),
    )


def downgrade() -> None:
    """
    Drop the unique constraint index
    """
    op.drop_index("idx_appointment_no_double_booking", table_name="appointment")
