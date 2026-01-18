"""merge audit_log and patient schema branches

Revision ID: 5885062792d4
Revises: a1b2c3d4e5f6, 20260117_patient_schema
Create Date: 2026-01-18 05:27:09.991086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '5885062792d4'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', '20260117_patient_schema')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
