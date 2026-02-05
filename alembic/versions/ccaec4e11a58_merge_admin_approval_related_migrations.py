"""merge admin approval related migrations

Revision ID: ccaec4e11a58
Revises: 187fa5974688, 20260206_rejection_reason, 20d81cf32f2e
Create Date: 2026-02-06 02:12:02.767516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccaec4e11a58'
down_revision: Union[str, Sequence[str], None] = ('187fa5974688', '20260206_rejection_reason', '20d81cf32f2e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
