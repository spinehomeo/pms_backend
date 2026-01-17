"""Add doctor availability table

Revision ID: 20260117_doctor_availability
Revises: 72b5e3eba95c
Create Date: 2026-01-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260117_doctor_availability'
down_revision: Union[str, Sequence[str], None] = '72b5e3eba95c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type for day of week if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE dayofweek AS ENUM (
                'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create doctor_availability table
    op.create_table(
        'doctor_availability',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('doctor_id', sa.Uuid(), nullable=False),
        sa.Column('day_of_week', sa.String(50), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_patients_per_slot', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['doctor_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_doctor_day', 'doctor_availability', ['doctor_id', 'day_of_week'])
    op.create_index('idx_doctor_availability', 'doctor_availability', ['doctor_id', 'day_of_week', 'is_available'])
    op.create_index('idx_doctor_id', 'doctor_availability', ['doctor_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_doctor_id', table_name='doctor_availability')
    op.drop_index('idx_doctor_availability', table_name='doctor_availability')
    op.drop_index('idx_doctor_day', table_name='doctor_availability')
    
    # Drop table
    op.drop_table('doctor_availability')
    
    # Drop enum type
    op.execute("""
        DO $$ BEGIN
            DROP TYPE IF EXISTS dayofweek;
        EXCEPTION WHEN dependent_objects_still_exist THEN null;
        END $$;
    """)
