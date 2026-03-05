# Migration Template for Onsite Consultation Tables
# 
# This file serves as a reference for creating an Alembic migration.
# To create the actual migration, run:
#
#   alembic revision --autogenerate -m "Add onsite consultation tables"
#   alembic upgrade head
#
# This template shows what the migration should contain.

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    """Create onsite consultation tables."""
    
    # SequenceCounter table
    op.create_table(
        'sequence_counter',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('counter_type', sa.String(length=50), nullable=False),
        sa.Column('prefix', sa.String(length=50), nullable=False),
        sa.Column('current_sequence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_counter_type_prefix',
        'sequence_counter',
        ['counter_type', 'prefix'],
        unique=True
    )
    
    # OnsiteConsultationAudit table
    op.create_table(
        'onsite_consultation_audit',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('appointment_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('prescription_id', sa.UUID(), nullable=True),
        sa.Column('follow_up_id', sa.UUID(), nullable=True),
        sa.Column('doctor_id', sa.UUID(), nullable=False),
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
    )
    op.create_index('idx_audit_doctor_date', 'onsite_consultation_audit', ['doctor_id', 'created_at'])
    op.create_index('idx_audit_patient_phone', 'onsite_consultation_audit', ['patient_phone', 'created_at'])
    op.create_index('idx_audit_idempotency', 'onsite_consultation_audit', ['idempotency_key'])
    op.create_index('idx_audit_patient_id', 'onsite_consultation_audit', ['patient_id'])


def downgrade():
    """Drop onsite consultation tables."""
    
    op.drop_index('idx_audit_patient_id', table_name='onsite_consultation_audit')
    op.drop_index('idx_audit_idempotency', table_name='onsite_consultation_audit')
    op.drop_index('idx_audit_patient_phone', table_name='onsite_consultation_audit')
    op.drop_index('idx_audit_doctor_date', table_name='onsite_consultation_audit')
    op.drop_table('onsite_consultation_audit')
    
    op.drop_index('idx_counter_type_prefix', table_name='sequence_counter')
    op.drop_table('sequence_counter')
