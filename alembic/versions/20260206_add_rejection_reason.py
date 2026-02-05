"""Add rejection_reason field to user table

Revision ID: 20260206_rejection_reason
Revises: 20260125_appt_unique
Create Date: 2026-02-06

This migration adds a rejection_reason column to the user table to track
the reason when an admin rejects a user's signup application (doctor or staff).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260206_rejection_reason"
down_revision: Union[str, Sequence[str], None] = "e26d1920b882"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add rejection_reason column (VARCHAR 500, nullable) to user table
    """
    op.add_column(
        "user",
        sa.Column("rejection_reason", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    """
    Drop the rejection_reason column
    """
    op.drop_column("user", "rejection_reason")
