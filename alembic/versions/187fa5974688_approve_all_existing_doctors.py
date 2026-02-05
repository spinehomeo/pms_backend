"""approve all existing doctors

Revision ID: 187fa5974688
Revises: d89e53a0cd12
Create Date: 2026-02-06 00:31:42.110340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '187fa5974688'
down_revision: Union[str, Sequence[str], None] = 'd89e53a0cd12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
