"""Make dosage column nullable in prescription table

Revision ID: 20260314_make_dosage_nullable
Revises: 20260306_add_onsite_consultation
Create Date: 2026-03-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '20260314_make_dosage_nullable'
down_revision: Union[str, Sequence[str], None] = '20260306_add_onsite_consultation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - make dosage nullable."""
    op.alter_column(
        'prescription',
        'dosage',
        existing_type=sa.String(length=200),
        nullable=True
    )


def downgrade() -> None:
    """Downgrade schema - make dosage not null."""
    op.alter_column(
        'prescription',
        'dosage',
        existing_type=sa.String(length=200),
        nullable=False
    )
