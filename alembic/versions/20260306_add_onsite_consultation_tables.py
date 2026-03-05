"""Add onsite consultation tables (sequence_counter and onsite_consultation_audit)

Revision ID: 20260306_add_onsite_consultation
Revises: 20260305_add_followup_payment
Create Date: 2026-03-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '20260306_add_onsite_consultation'
down_revision: Union[str, Sequence[str], None] = '20260305_add_followup_payment'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create onsite consultation tables."""
    # Create sequence_counter table for thread-safe numbering
    op.create_table(
        'sequence_counter',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('counter_type', sa.String(length=50), nullable=False),
        sa.Column('prefix', sa.String(length=50), nullable=False),
        sa.Column('current_sequence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_sequence_counter_counter_type', 'counter_type'),
        sa.Index('idx_counter_type_prefix', 'counter_type', 'prefix', unique=True),
    )
    
    # Create onsite_consultation_audit table for tracking consultations
    op.create_table(
        'onsite_consultation_audit',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('patient_id', sa.Uuid(), nullable=False),
        sa.Column('appointment_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('prescription_id', sa.Uuid(), nullable=True),
        sa.Column('follow_up_id', sa.Uuid(), nullable=True),
        sa.Column('doctor_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('is_new_patient', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('patient_phone', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patient.id'], ),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointment.id'], ),
        sa.ForeignKeyConstraint(['case_id'], ['patient_case.id'], ),
        sa.ForeignKeyConstraint(['prescription_id'], ['prescription.id'], ),
        sa.ForeignKeyConstraint(['follow_up_id'], ['follow_up.id'], ),
        sa.ForeignKeyConstraint(['doctor_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_onsite_consultation_audit_patient_id', 'patient_id'),
        sa.Index('ix_onsite_consultation_audit_appointment_id', 'appointment_id'),
        sa.Index('ix_onsite_consultation_audit_case_id', 'case_id'),
        sa.Index('ix_onsite_consultation_audit_doctor_id', 'doctor_id'),
        sa.Index('ix_onsite_consultation_audit_idempotency_key', 'idempotency_key'),
        sa.Index('idx_audit_doctor_date', 'doctor_id', 'created_at'),
        sa.Index('idx_audit_patient_phone', 'patient_phone', 'created_at'),
    )


def downgrade() -> None:
    """Downgrade schema - drop onsite consultation tables."""
    # Drop indexes and tables in reverse order
    op.drop_index('idx_audit_patient_phone', table_name='onsite_consultation_audit')
    op.drop_index('idx_audit_doctor_date', table_name='onsite_consultation_audit')
    op.drop_index('ix_onsite_consultation_audit_idempotency_key', table_name='onsite_consultation_audit')
    op.drop_index('ix_onsite_consultation_audit_doctor_id', table_name='onsite_consultation_audit')
    op.drop_index('ix_onsite_consultation_audit_case_id', table_name='onsite_consultation_audit')
    op.drop_index('ix_onsite_consultation_audit_appointment_id', table_name='onsite_consultation_audit')
    op.drop_index('ix_onsite_consultation_audit_patient_id', table_name='onsite_consultation_audit')
    op.drop_table('onsite_consultation_audit')
    
    op.drop_index('idx_counter_type_prefix', table_name='sequence_counter')
    op.drop_index('ix_sequence_counter_counter_type', table_name='sequence_counter')
    op.drop_table('sequence_counter')
