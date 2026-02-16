"""Add doctor_availability_exception table

Revision ID: 20260216_availability_exceptions
Revises: 47ae1a1bc15a
Create Date: 2026-02-16

This migration creates the doctor_availability_exception table to handle
date-specific availability exceptions for doctors (vacations, custom hours, holidays).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "20260216_availability_exceptions"
down_revision: Union[str, Sequence[str], None] = "47ae1a1bc15a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create doctor_availability_exception table
    """
    op.create_table(
        'doctor_availability_exception',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exception_date', sa.Date(), nullable=False),
        sa.Column('exception_type', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('end_time', sa.Time(), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['doctor_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doctor_id', 'exception_date', name='uq_doctor_exception_date')
    )
    
    # Create indexes for efficient querying
    op.create_index(
        'idx_doctor_exception_date',
        'doctor_availability_exception',
        ['doctor_id', 'exception_date']
    )
    op.create_index(
        'idx_exception_date',
        'doctor_availability_exception',
        ['exception_date']
    )


def downgrade() -> None:
    """
    Drop doctor_availability_exception table and indexes
    """
    op.drop_index('idx_exception_date', table_name='doctor_availability_exception')
    op.drop_index('idx_doctor_exception_date', table_name='doctor_availability_exception')
    op.drop_table('doctor_availability_exception')
