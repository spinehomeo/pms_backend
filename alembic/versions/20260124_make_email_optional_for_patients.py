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
    """Upgrade schema - make email optional for patients with partial unique index."""
    # Alter the email column to allow NULL values
    # This permits patients (who have NULL email) while keeping doctors/staff/admin with emails
    op.alter_column('user', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=True,
               existing_nullable=False)
    
    # Create a partial unique index that only enforces uniqueness for non-NULL emails
    # This prevents duplicate emails for doctors/staff/admin while allowing multiple NULL values for patients
    op.create_index('ix_user_email_unique_not_null', 'user', ['email'], 
                    postgresql_where=sa.text("email IS NOT NULL"), unique=True)


def downgrade() -> None:
    """Downgrade schema - revert email to required with original unique constraint."""
    # Drop the partial unique index
    op.drop_index('ix_user_email_unique_not_null', table_name='user')
    
    # Alter the email column back to NOT NULL
    op.alter_column('user', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=False,
               existing_nullable=True)
