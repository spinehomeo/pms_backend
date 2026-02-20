"""Migrate from Python Enums to dynamic database-driven enum system

Revision ID: 20260219_dynamic_enums
Revises: 20260216_availability_exceptions
Create Date: 2026-02-19

This migration documents the system-wide transition from hardcoded Python Enums
to a dynamic, database-driven enum system using EnumType and EnumOption tables.

CHANGELOG:
----------
1. Converted all Enum comparisons to string literals across 7 route files
2. Updated model type hints from Enum classes to str type
3. Removed Python Enum imports (UserRole, AppointmentStatus, PatientGender, etc.)
4. Enabled runtime enum customization through admin API endpoints
5. Introduced per-doctor enum preference toggles

AFFECTED ENUM TYPES:
--------------------
- UserRole: admin, doctor, staff
- AppointmentStatus: scheduled, confirmed, in_progress, completed, cancelled, no_show
- PatientGender: male, female, other, child
- PrescriptionType: Constitutional, Classical, Intercurrent
- RepetitionEnum: OD, BD, TDS, OnceWeekly, etc.
- FormEnum: Diskette, SOM, Blankets, Globules, etc.
- ScaleEnum: C, X, Q
- ManufacturerEnum: Schwabe, Reckweg, etc.
- DayOfWeek: monday, tuesday, ..., sunday
- ExceptionType: unavailable, custom_hours, holiday

ROUTE FILES UPDATED:
--------------------
1. routes/public.py - 6 enum changes (UserRole, ExceptionType, AppointmentStatus)
2. routes/patients.py - 5 enum changes (AppointmentStatus)
3. routes/reports.py - 3 enum changes (AppointmentStatus)
4. routes/medicines.py - 5 enum changes (ScaleEnum, FormEnum, ManufacturerEnum)
5. routes/appointments.py - 10 enum changes (AppointmentStatus, UserRole)
6. routes/users.py - 5 enum changes (UserRole, PatientGender)
7. routes/doctor_availability.py - 8 enum changes (DayOfWeek, ExceptionType)

MODEL FILES UPDATED:
--------------------
1. models/appointments_model.py - Removed AppointmentStatus enum, changed status to str
2. models/__init__.py - Removed Enum exports

DATABASE IMPACT:
----------------
No schema changes required. Existing VARCHAR/TEXT columns already support string values.
All affected columns accept the now-standardized lowercase string values.

MIGRATION PATH:
---------------
This is a code-only migration with no database schema changes. The change is backward
compatible as all existing enum values are converted to their lowercase string equivalents:
- SCHEDULED → "scheduled"
- DOCTOR → "doctor"
- etc.

To verify the migration is working correctly:
1. Run pytest on all modified route files
2. Test enum filtering with string values in API queries
3. Verify admin can create new enum values via /enums endpoints
4. Confirm doctor preferences for enums are persisted correctly

ROLLBACK PATH:
--------------
If needed to rollback:
1. Re-add Enum class definitions to model files
2. Update comparisons to use Enum.VALUE syntax
3. Re-export Enum classes from __init__.py
4. The database schema requires no changes for rollback
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260219_dynamic_enums"
down_revision: Union[str, Sequence[str], None] = "7db72229909d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enum system migration upgrade.
    
    No database schema changes needed. This documents the code-level transition
    from Python Enums to database-driven dynamic enums.
    
    The EnumType and EnumOption tables are already created by a previous migration
    and are used by the /enums API endpoints to manage enum values at runtime.
    """
    # No SQL operations needed - this is a code migration
    # Verify EnumType and EnumOption tables exist
    pass


def downgrade() -> None:
    """
    Enum system migration downgrade.
    
    Rollback to Python Enum-based system by:
    1. Re-adding Enum class definitions
    2. Updating code to use Enum.VALUE syntax
    3. Re-exporting Enum classes from __init__.py
    
    No database changes needed.
    """
    # No SQL operations needed - this is a code migration
    pass
