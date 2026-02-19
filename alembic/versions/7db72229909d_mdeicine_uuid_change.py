"""medicine uuid change (production safe)

Revision ID: 7db72229909d
Revises: 98d4504f3022
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '7db72229909d'
down_revision: Union[str, Sequence[str], None] = '98d4504f3022'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enable UUID generator
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # 2. Add UUID column to medicine
    op.add_column('medicine',
        sa.Column('id_uuid', postgresql.UUID(), nullable=True)
    )

    # 3. Generate UUIDs for existing rows
    op.execute("""
        UPDATE medicine
        SET id_uuid = gen_random_uuid();
    """)

    # 4. Make UUID NOT NULL
    op.alter_column('medicine', 'id_uuid', nullable=False)

    # 5. Add UUID columns to related tables
    op.add_column('doctor_medicine_preference',
        sa.Column('medicine_id_uuid', postgresql.UUID(), nullable=True)
    )

    op.add_column('prescription_medicine',
        sa.Column('medicine_id_uuid', postgresql.UUID(), nullable=True)
    )

    # 6. Copy data using mapping
    op.execute("""
        UPDATE doctor_medicine_preference dmp
        SET medicine_id_uuid = m.id_uuid
        FROM medicine m
        WHERE dmp.medicine_id = m.id;
    """)

    op.execute("""
        UPDATE prescription_medicine pm
        SET medicine_id_uuid = m.id_uuid
        FROM medicine m
        WHERE pm.medicine_id = m.id;
    """)

    # 7. Make new columns NOT NULL
    op.alter_column('doctor_medicine_preference', 'medicine_id_uuid', nullable=False)
    op.alter_column('prescription_medicine', 'medicine_id_uuid', nullable=False)

    # 8. Drop foreign key constraints
    op.drop_constraint(
        'doctor_medicine_preference_medicine_id_fkey',
        'doctor_medicine_preference',
        type_='foreignkey'
    )

    op.drop_constraint(
        'prescription_medicine_medicine_id_fkey',
        'prescription_medicine',
        type_='foreignkey'
    )

    # 9. Drop old integer columns
    op.drop_column('doctor_medicine_preference', 'medicine_id')
    op.drop_column('prescription_medicine', 'medicine_id')

    # 10. Rename new columns
    op.alter_column('doctor_medicine_preference', 'medicine_id_uuid',
                    new_column_name='medicine_id')

    op.alter_column('prescription_medicine', 'medicine_id_uuid',
                    new_column_name='medicine_id')

    # 11. Replace primary key in medicine
    op.drop_constraint('medicine_pkey', 'medicine', type_='primary')
    op.drop_column('medicine', 'id')
    op.alter_column('medicine', 'id_uuid', new_column_name='id')
    op.create_primary_key('medicine_pkey', 'medicine', ['id'])

    # 12. Recreate foreign keys
    op.create_foreign_key(
        'doctor_medicine_preference_medicine_id_fkey',
        'doctor_medicine_preference',
        'medicine',
        ['medicine_id'],
        ['id']
    )

    op.create_foreign_key(
        'prescription_medicine_medicine_id_fkey',
        'prescription_medicine',
        'medicine',
        ['medicine_id'],
        ['id']
    )


def downgrade() -> None:
    raise Exception("Downgrade not supported for this UUID migration")
