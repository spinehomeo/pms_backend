"""add duration_days to prescription

Revision ID: 20260222_add_duration_days
Revises: fe5393294599
Create Date: 2026-02-22

What this migration does
------------------------
Adds a single nullable integer column `duration_days` to the `prescription` table.

This is the structured counterpart to the existing free-text `prescription_duration`
field (e.g. "30 days"). Having an integer value allows the backend to automatically
calculate follow-up dates via:

    follow_up_date = prescription_date + duration_days

The column is nullable so that existing prescriptions and any prescription created
without providing `duration_days` continue to work without change.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260222_add_duration_days'
down_revision = '4dd790bf463d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'prescription',
        sa.Column(
            'duration_days',
            sa.Integer(),
            nullable=True,
            comment='Integer version of prescription_duration for auto follow-up date calculation'
        )
    )


def downgrade() -> None:
    op.drop_column('prescription', 'duration_days')
