"""Enum Changes

Revision ID: 4085cd9f9281
Revises: 20260216_availability_exceptions
Create Date: 2026-02-16 11:55:26.552566
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers
revision: str = '4085cd9f9281'
down_revision: Union[str, Sequence[str], None] = '20260216_availability_exceptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # ==========================================================
    # 1️⃣ CREATE NEW ENUM TYPES
    # ==========================================================

    exceptiontype_enum = postgresql.ENUM(
        'UNAVAILABLE', 'CUSTOM_HOURS', 'HOLIDAY',
        name='exceptiontype'
    )
    exceptiontype_enum.create(bind, checkfirst=True)

    scaleenum_enum = postgresql.ENUM(
        'C', 'X', 'Q',
        name='scaleenum'
    )
    scaleenum_enum.create(bind, checkfirst=True)

    formenum_enum = postgresql.ENUM(
        'DISKETTE', 'SOM', 'BLANKETS',
        'BIO_CHEMIC', 'HOMOEO_TABS',
        'GLOBULES', 'DILUTIONS',
        name='formenum'
    )
    formenum_enum.create(bind, checkfirst=True)

    manufacturerenum_enum = postgresql.ENUM(
        'SCHWABE', 'RECKWEG', 'LEMASAR', 'DOLISOS',
        'KAMAL', 'MASOOD', 'BM', 'KENT',
        'BROOKS', 'WARIS_SHAH', 'SELF_PACKING',
        name='manufacturerenum'
    )
    manufacturerenum_enum.create(bind, checkfirst=True)

    # ==========================================================
    # 2️⃣ CLEAN UP DATA BEFORE ENUM CONVERSION
    # ==========================================================

    # Set unknown manufacturers to NULL before conversion
    # This prevents migration failure from invalid enum values
    op.execute(
        """UPDATE doctor_medicine_stock 
           SET manufacturer = NULL 
           WHERE manufacturer NOT IN (
               'SCHWABE', 'RECKWEG', 'LEMASAR', 'DOLISOS',
               'KAMAL', 'MASOOD', 'BM', 'KENT',
               'BROOKS', 'WARIS_SHAH', 'SELF_PACKING'
           ) AND manufacturer IS NOT NULL
        """
    )

    # ==========================================================
    # 3️⃣ ALTER COLUMNS WITH PROPER CASTING
    # ==========================================================

    op.alter_column(
        'doctor_availability_exception',
        'exception_type',
        existing_type=sa.VARCHAR(length=50),
        type_=exceptiontype_enum,
        postgresql_using="exception_type::exceptiontype",
        existing_nullable=False
    )

    op.alter_column(
        'doctor_medicine_stock',
        'potency_scale',
        existing_type=postgresql.ENUM(
            'X', 'C', 'LM', 'Q', 'M', 'CM', 'MM',
            name='potencyscale'
        ),
        type_=scaleenum_enum,
        postgresql_using="potency_scale::text::scaleenum",
        existing_nullable=False
    )

    op.alter_column(
        'doctor_medicine_stock',
        'form',
        existing_type=postgresql.ENUM(
            'PILLS', 'GLOBULES', 'DROPS', 'POWDER',
            'OINTMENT', 'SUPPOSITORY', 'INJECTION',
            name='medicineform'
        ),
        type_=formenum_enum,
        postgresql_using="form::text::formenum",
        existing_nullable=False
    )

    op.alter_column(
        'doctor_medicine_stock',
        'manufacturer',
        existing_type=sa.VARCHAR(length=255),
        type_=manufacturerenum_enum,
        postgresql_using="manufacturer::manufacturerenum",
        existing_nullable=True
    )

    # ==========================================================
    # 4️⃣ OTHER STRUCTURAL CHANGES
    # ==========================================================

    op.drop_index(
        op.f('idx_exception_date'),
        table_name='doctor_availability_exception'
    )

    op.create_index(
        op.f('ix_doctor_availability_exception_doctor_id'),
        'doctor_availability_exception',
        ['doctor_id'],
        unique=False
    )

    op.alter_column(
        'doctor_medicine_stock',
        'medicine_id',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    # Add new columns as nullable first, populate, then make NOT NULL
    op.add_column(
        'patient_case',
        sa.Column(
            'chief_complaint_duration',
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
            server_default='Not Specified'
        )
    )

    # Update existing rows with default value
    op.execute("UPDATE patient_case SET chief_complaint_duration = 'Not Specified' WHERE chief_complaint_duration IS NULL")
    
    # Make the column NOT NULL
    op.alter_column(
        'patient_case',
        'chief_complaint_duration',
        nullable=False,
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=100)
    )

    op.drop_column('patient_case', 'duration')

    # Same for prescription
    op.add_column(
        'prescription',
        sa.Column(
            'prescription_duration',
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
            server_default='Not Specified'
        )
    )

    # Update existing rows with default value
    op.execute("UPDATE prescription SET prescription_duration = 'Not Specified' WHERE prescription_duration IS NULL")
    
    # Make the column NOT NULL
    op.alter_column(
        'prescription',
        'prescription_duration',
        nullable=False,
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=100)
    )

    op.drop_column('prescription', 'duration')

    op.alter_column(
        'prescription_medicine',
        'medicine_id',
        existing_type=sa.INTEGER(),
        nullable=False
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Reverse structural changes first

    op.alter_column(
        'prescription_medicine',
        'medicine_id',
        existing_type=sa.INTEGER(),
        nullable=True
    )

    op.add_column(
        'prescription',
        sa.Column('duration', sa.VARCHAR(length=100), nullable=False)
    )
    op.drop_column('prescription', 'prescription_duration')

    op.add_column(
        'patient_case',
        sa.Column('duration', sa.VARCHAR(length=100), nullable=False)
    )
    op.drop_column('patient_case', 'chief_complaint_duration')

    op.alter_column(
        'doctor_medicine_stock',
        'medicine_id',
        existing_type=sa.INTEGER(),
        nullable=True
    )

    # Convert enums back to text

    op.alter_column(
        'doctor_availability_exception',
        'exception_type',
        type_=sa.VARCHAR(length=50),
        postgresql_using="exception_type::text",
        existing_nullable=False
    )

    op.alter_column(
        'doctor_medicine_stock',
        'manufacturer',
        type_=sa.VARCHAR(length=255),
        postgresql_using="manufacturer::text",
        existing_nullable=True
    )

    # Drop newly created enum types
    postgresql.ENUM(name='exceptiontype').drop(bind, checkfirst=True)
    postgresql.ENUM(name='scaleenum').drop(bind, checkfirst=True)
    postgresql.ENUM(name='formenum').drop(bind, checkfirst=True)
    postgresql.ENUM(name='manufacturerenum').drop(bind, checkfirst=True)
