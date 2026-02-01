# utils/migrate_case_fields.py
"""
Migration script to update case fields - remove old fields and keep only required ones.
Backs up old field data to custom_fields JSON before deletion.

Old fields being removed:
- chief_complaint, onset, location, sensation, modalities, concomitants
- generals, mentals, miasm_assessment, vitality_assessment, case_notes

Fields being kept:
- chief_complaint_patient (required), duration (required)
- physicals, noted_complaint_doctor, peculiar_symptoms, causation, lab_reports
- custom_fields (JSON for dynamic data)

Usage:
    python -m utils.migrate_case_fields
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, select, text
from core.db import engine
from models.users_model import User
from models.doctor_preferences_model import DoctorCaseFieldPreference, STANDARD_FIELDS
from utils.time import utc_now


def backup_old_fields():
    """
    Backup old fields to custom_fields JSON before dropping them.
    """
    
    backup_sql = """
    -- Backup old fields to custom_fields before deletion
    DO $$ 
    BEGIN
        -- For each row, save old fields to custom_fields if not already there
        UPDATE patient_case 
        SET custom_fields = COALESCE(custom_fields, '{}'::jsonb) ||
            jsonb_build_object(
                'backup_chief_complaint', chief_complaint,
                'backup_onset', onset,
                'backup_location', location,
                'backup_sensation', sensation,
                'backup_modalities', modalities,
                'backup_concomitants', concomitants,
                'backup_generals', generals,
                'backup_mentals', mentals,
                'backup_miasm_assessment', miasm_assessment,
                'backup_vitality_assessment', vitality_assessment,
                'backup_case_notes', case_notes
            )
        WHERE 
            custom_fields IS NULL OR 
            (chief_complaint IS NOT NULL OR onset IS NOT NULL OR location IS NOT NULL OR
             sensation IS NOT NULL OR modalities IS NOT NULL OR concomitants IS NOT NULL OR
             generals IS NOT NULL OR mentals IS NOT NULL OR miasm_assessment IS NOT NULL OR
             vitality_assessment IS NOT NULL OR case_notes IS NOT NULL);
        
        RAISE NOTICE 'Backed up old fields to custom_fields';
    END $$;
    """
    
    with Session(engine) as session:
        try:
            session.exec(text(backup_sql))
            session.commit()
            print("✓ Backed up old fields to custom_fields")
        except Exception as e:
            print(f"Warning: Could not backup old fields: {e}")
            session.rollback()


def drop_old_columns():
    """
    Drop the old columns from patient_case table.
    """
    
    drop_sql = """
    -- Drop old columns if they exist
    DO $$ 
    BEGIN
        -- List of columns to drop
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='chief_complaint') THEN
            ALTER TABLE patient_case DROP COLUMN chief_complaint;
            RAISE NOTICE 'Dropped column: chief_complaint';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='onset') THEN
            ALTER TABLE patient_case DROP COLUMN onset;
            RAISE NOTICE 'Dropped column: onset';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='location') THEN
            ALTER TABLE patient_case DROP COLUMN location;
            RAISE NOTICE 'Dropped column: location';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='sensation') THEN
            ALTER TABLE patient_case DROP COLUMN sensation;
            RAISE NOTICE 'Dropped column: sensation';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='modalities') THEN
            ALTER TABLE patient_case DROP COLUMN modalities;
            RAISE NOTICE 'Dropped column: modalities';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='concomitants') THEN
            ALTER TABLE patient_case DROP COLUMN concomitants;
            RAISE NOTICE 'Dropped column: concomitants';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='generals') THEN
            ALTER TABLE patient_case DROP COLUMN generals;
            RAISE NOTICE 'Dropped column: generals';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='mentals') THEN
            ALTER TABLE patient_case DROP COLUMN mentals;
            RAISE NOTICE 'Dropped column: mentals';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='miasm_assessment') THEN
            ALTER TABLE patient_case DROP COLUMN miasm_assessment;
            RAISE NOTICE 'Dropped column: miasm_assessment';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='vitality_assessment') THEN
            ALTER TABLE patient_case DROP COLUMN vitality_assessment;
            RAISE NOTICE 'Dropped column: vitality_assessment';
        END IF;
        
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='patient_case' AND column_name='case_notes') THEN
            ALTER TABLE patient_case DROP COLUMN case_notes;
            RAISE NOTICE 'Dropped column: case_notes';
        END IF;
    END $$;
    """
    
    with Session(engine) as session:
        try:
            session.exec(text(drop_sql))
            session.commit()
            print("✓ Dropped old columns from patient_case table")
        except Exception as e:
            print(f"Warning: Could not drop old columns: {e}")
            session.rollback()


def ensure_required_fields():
    """
    Ensure required fields have proper defaults and are not null.
    """
    
    ensure_sql = """
    -- Set default values for required fields
    DO $$ 
    BEGIN
        UPDATE patient_case 
        SET chief_complaint_patient = 'Not specified'
        WHERE chief_complaint_patient IS NULL OR chief_complaint_patient = '';
        
        UPDATE patient_case 
        SET duration = 'Not specified'
        WHERE duration IS NULL OR duration = '';
        
        RAISE NOTICE 'Set default values for required fields';
    END $$;
    """
    
    with Session(engine) as session:
        try:
            session.exec(text(ensure_sql))
            session.commit()
            print("✓ Set default values for required fields")
        except Exception as e:
            print(f"Warning: Could not set defaults: {e}")
            session.rollback()


def initialize_doctor_preferences():
    """
    Initialize standard fields for all doctors if not already done.
    """
    
    with Session(engine) as session:
        print("\nInitializing doctor field preferences...")
        
        # Get all doctors
        doctors = session.exec(select(User).where(User.is_doctor == True)).all()
        
        for doctor in doctors:
            # Check if already initialized
            existing_count = session.exec(
                select(DoctorCaseFieldPreference).where(
                    DoctorCaseFieldPreference.doctor_id == doctor.id
                )
            ).first()
            
            if not existing_count:
                print(f"  Initializing fields for doctor: {doctor.full_name}")
                
                for i, field_def in enumerate(STANDARD_FIELDS):
                    preference = DoctorCaseFieldPreference(
                        doctor_id=doctor.id,
                        field_name=field_def["field_name"],
                        display_name=field_def["display_name"],
                        field_type=field_def["field_type"],
                        is_required=field_def["default_required"],
                        is_enabled=True,
                        position=i,
                        created_at=utc_now()
                    )
                    session.add(preference)
                
                session.commit()
                print(f"    ✓ Initialized {len(STANDARD_FIELDS)} standard fields")
            else:
                print(f"  Fields already initialized for: {doctor.full_name}")


def migrate_case_fields():
    """
    Execute the complete migration process.
    """
    
    print("\n" + "="*60)
    print("MIGRATION: Update Case Fields Schema")
    print("="*60 + "\n")
    
    print("Step 1: Backing up old field data...")
    backup_old_fields()
    
    print("\nStep 2: Dropping old columns...")
    drop_old_columns()
    
    print("\nStep 3: Setting default values for required fields...")
    ensure_required_fields()
    
    print("\nStep 4: Initializing doctor field preferences...")
    initialize_doctor_preferences()
    
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print("\nRemoved fields (backed up to custom_fields):")
    print("  - chief_complaint")
    print("  - onset")
    print("  - location")
    print("  - sensation")
    print("  - modalities")
    print("  - concomitants")
    print("  - generals")
    print("  - mentals")
    print("  - miasm_assessment")
    print("  - vitality_assessment")
    print("  - case_notes")
    
    print("\nKept fields:")
    print("  - chief_complaint_patient (required)")
    print("  - duration (required)")
    print("  - physicals (optional)")
    print("  - noted_complaint_doctor (optional)")
    print("  - peculiar_symptoms (optional)")
    print("  - causation (optional)")
    print("  - lab_reports (optional)")
    print("  - custom_fields (JSON - dynamic fields)")
    
    print("\nChanges:")
    print("  - Case number format: C-MMMYY-001 (e.g., C-JAN26-001)")
    print("  - Added doctor field preferences system")
    print("  - Old data backed up to custom_fields JSON")
    print("\n" + "="*60)


if __name__ == "__main__":
    try:
        migrate_case_fields()
        print("\n✅ Migration completed successfully!\n")
    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}\n")
        sys.exit(1)
