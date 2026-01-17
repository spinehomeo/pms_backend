"""Update patient schema with new fields

Revision ID: 20260117_patient_schema
Revises: 20260117_doctor_availability
Create Date: 2026-01-17 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '20260117_patient_schema'
down_revision: Union[str, Sequence[str], None] = '20260117_doctor_availability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to patient table
    op.add_column('patient', sa.Column('cnic', sa.String(length=15), nullable=True, unique=True))
    op.add_column('patient', sa.Column('phone_secondary', sa.String(length=20), nullable=True))
    op.add_column('patient', sa.Column('residential_address', sa.String(), nullable=True))
    op.add_column('patient', sa.Column('postal_address', sa.String(), nullable=True))
    op.add_column('patient', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('patient', sa.Column('payment_status', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('patient', sa.Column('current_medications', sa.String(), nullable=True))
    op.add_column('patient', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    
    # Create indexes for frequently searched fields
    op.create_index('idx_patient_cnic', 'patient', ['cnic'])
    op.create_index('idx_patient_city', 'patient', ['city'])
    op.create_index('idx_patient_payment_status', 'patient', ['payment_status'])
    op.create_index('idx_patient_doctor_city', 'patient', ['doctor_id', 'city'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_patient_doctor_city', table_name='patient')
    op.drop_index('idx_patient_payment_status', table_name='patient')
    op.drop_index('idx_patient_city', table_name='patient')
    op.drop_index('idx_patient_cnic', table_name='patient')
    
    # Remove added columns
    op.drop_column('patient', 'is_active')
    op.drop_column('patient', 'current_medications')
    op.drop_column('patient', 'payment_status')
    op.drop_column('patient', 'city')
    op.drop_column('patient', 'postal_address')
    op.drop_column('patient', 'residential_address')
    op.drop_column('patient', 'phone_secondary')
    op.drop_column('patient', 'cnic')
