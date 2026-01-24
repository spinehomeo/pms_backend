"""make email optional for patients

Revision ID: 20260124_email_optional
Revises: 89e09060d5ff
Create Date: 2026-01-24 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260124_email_optional'
down_revision: Union[str, Sequence[str], None] = '89e09060d5ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - make email optional for patients."""
    # Drop the unique constraint on email to allow NULL values
    op.drop_constraint('user_email_key', 'user', type_='unique')
    
    # Alter the email column to allow NULL values
    op.alter_column('user', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=True,
               existing_nullable=False)
    
    # Re-create unique index that allows NULL values
    op.create_unique_constraint('user_email_key', 'user', ['email'], 
                                postgresql_where=sa.text("email IS NOT NULL"))


def downgrade() -> None:
    """Downgrade schema - revert email to required."""
    # Drop the conditional unique constraint
    op.drop_constraint('user_email_key', 'user', type_='unique')
    
    # Alter the email column back to NOT NULL
    op.alter_column('user', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=False,
               existing_nullable=True)
    
    # Re-create the original unique constraint
    op.create_unique_constraint('user_email_key', 'user', ['email'])
