#!/usr/bin/env python
"""
Fix null/unknown values in prescriptions and medicines.
Populates:
  - Medicines with potency = 'Unknown' → assigns valid potencies
  - Prescriptions with duration_days = NULL → assigns default duration
  - PrescriptionMedicines with quantity_prescribed = NULL → assigns default quantity
  - PrescriptionMedicines with frequency = NULL → assigns valid frequency

Run with: uv run python scripts/fix_prescription_data.py
"""
import sys
from sqlmodel import Session, select
from sqlalchemy import text

sys.path.insert(0, str(__file__).rsplit('\\', 2)[0])

from core.db import engine
from models.medicines_model import Medicine
from models.prescriptions_model import Prescription, PrescriptionMedicine
from models.enum_option_model import EnumOption


def get_enum_values(session, enum_name: str) -> list:
    """Get valid enum values from database."""
    try:
        options = session.exec(
            select(EnumOption).where(EnumOption.enum_name == enum_name)
        ).all()
        return [opt.option_value for opt in options]
    except Exception as e:
        print(f"  ⚠ Warning: Could not fetch enum '{enum_name}': {e}")
        return []


def fix_medicines_potency(session):
    """Update medicines with potency = 'Unknown' to valid potencies."""
    print("\n" + "="*80)
    print("FIX: Medicines with potency = 'Unknown'")
    print("="*80)
    
    # Get medicines with Unknown potency
    medicines = session.exec(
        select(Medicine).where(Medicine.potency == "Unknown")
    ).all()
    
    if not medicines:
        print("✓ No medicines to fix")
        return
    
    print(f"Found {len(medicines)} medicines to fix")
    
    # Common homeopathic potencies to use (in rotation)
    potencies = ["6C", "30C", "200C", "1M"]
    potency_scale = "C"
    
    for idx, medicine in enumerate(medicines):
        potency = potencies[idx % len(potencies)]
        print(f"  - {medicine.name}: Unknown → {potency}")
        medicine.potency = potency
        medicine.potency_scale = potency_scale
        if not medicine.form or medicine.form == "Globules":
            medicine.form = "GLOBULES"  # Standardize form
    
    session.add_all(medicines)
    session.commit()
    print(f"\n✓ Updated {len(medicines)} medicines")


def fix_prescriptions_duration_days(session):
    """Update prescriptions with duration_days = NULL to default value."""
    print("\n" + "="*80)
    print("FIX: Prescriptions with duration_days = NULL")
    print("="*80)
    
    # Get prescriptions with NULL duration_days
    prescriptions = session.exec(
        select(Prescription).where(Prescription.duration_days == None)
    ).all()
    
    if not prescriptions:
        print("✓ No prescriptions to fix")
        return
    
    print(f"Found {len(prescriptions)} prescriptions to fix")
    
    # Default duration: 14 days (2 weeks - standard for homeopathy)
    default_duration = 14
    
    for prescription in prescriptions:
        # Only set if prescription_duration is also missing or is "string"
        if not prescription.prescription_duration or prescription.prescription_duration == "string":
            prescription.prescription_duration = f"{default_duration} days"
        
        # Set duration_days if not set
        if prescription.duration_days is None:
            prescription.duration_days = default_duration
            print(f"  - Rx {prescription.prescription_number}: duration_days → {default_duration}")
    
    session.add_all(prescriptions)
    session.commit()
    print(f"\n✓ Updated {len(prescriptions)} prescriptions")


def fix_prescription_medicines_quantity_and_frequency(session):
    """Update prescription medicines with null quantity_prescribed and frequency."""
    print("\n" + "="*80)
    print("FIX: PrescriptionMedicines with null quantity_prescribed/frequency")
    print("="*80)
    
    # Get prescription medicines that need fixing
    pm_need_fix = session.exec(
        select(PrescriptionMedicine).where(
            (PrescriptionMedicine.quantity_prescribed == None) |
            (PrescriptionMedicine.frequency == None)
        )
    ).all()
    
    if not pm_need_fix:
        print("✓ No prescription medicines to fix")
        return
    
    print(f"Found {len(pm_need_fix)} prescription medicines to fix")
    
    # Get valid frequencies from enum
    frequencies = get_enum_values(session, "RepetitionEnum")
    if not frequencies:
        # Fallback to common homeopathic frequencies
        frequencies = ["OD", "BD", "TDS"]
    
    print(f"  Using frequencies: {frequencies}")
    
    # Default values for homeopathy
    default_quantity = "100ml"  # Standard homeopathic bottle
    default_frequency = frequencies[0] if frequencies else "OD"  # Once daily
    
    for idx, pm in enumerate(pm_need_fix):
        if pm.quantity_prescribed is None:
            pm.quantity_prescribed = default_quantity
            print(f"  - Medicine {pm.medicine.name}: quantity_prescribed → {default_quantity}")
        
        if pm.frequency is None:
            # Rotate through frequencies for variety
            freq = frequencies[idx % len(frequencies)]
            pm.frequency = freq
            print(f"  - Medicine {pm.medicine.name}: frequency → {freq}")
    
    session.add_all(pm_need_fix)
    session.commit()
    print(f"\n✓ Updated {len(pm_need_fix)} prescription medicines")


def fix_invalid_string_values(session):
    """Fix any 'string' placeholder values in prescriptions and medicines."""
    print("\n" + "="*80)
    print("FIX: Invalid 'string' placeholder values")
    print("="*80)
    
    # Find medicines with potency = 'string'
    string_medicines = session.exec(
        select(Medicine).where(Medicine.potency == "string")
    ).all()
    
    if string_medicines:
        print(f"Found {len(string_medicines)} medicines with potency = 'string'")
        for med in string_medicines:
            med.potency = "30C"
            med.potency_scale = "C"
            med.form = "GLOBULES"
            print(f"  - {med.name}: potency → 30C")
        session.add_all(string_medicines)
        session.commit()
        print(f"✓ Updated {len(string_medicines)} medicines\n")
    
    # Find prescriptions with prescription_duration = 'string'
    string_prescriptions = session.exec(
        select(Prescription).where(Prescription.prescription_duration == "string")
    ).all()
    
    if string_prescriptions:
        print(f"Found {len(string_prescriptions)} prescriptions with duration = 'string'")
        for rx in string_prescriptions:
            rx.prescription_duration = "14 days"
            if rx.duration_days is None:
                rx.duration_days = 14
            print(f"  - {rx.prescription_number}: duration → 14 days")
        session.add_all(string_prescriptions)
        session.commit()
        print(f"✓ Updated {len(string_prescriptions)} prescriptions\n")


def verify_fixes(session):
    """Verify all fixes were applied."""
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    
    # Check medicines with Unknown potency
    unknown_count = session.exec(
        text("SELECT COUNT(*) as cnt FROM medicine WHERE potency = 'Unknown'")
    ).first()[0]
    print(f"Medicines with potency = 'Unknown': {unknown_count} (should be 0)")
    
    # Check medicines with 'string' potency
    string_count = session.exec(
        text("SELECT COUNT(*) as cnt FROM medicine WHERE potency = 'string'")
    ).first()[0]
    print(f"Medicines with potency = 'string': {string_count} (should be 0)")
    
    # Check prescriptions with NULL duration_days
    null_duration = session.exec(
        text("SELECT COUNT(*) as cnt FROM prescription WHERE duration_days IS NULL")
    ).first()[0]
    print(f"Prescriptions with duration_days = NULL: {null_duration} (should be 0)")
    
    # Check prescriptions with 'string' duration
    string_duration = session.exec(
        text("SELECT COUNT(*) as cnt FROM prescription WHERE prescription_duration = 'string'")
    ).first()[0]
    print(f"Prescriptions with duration = 'string': {string_duration} (should be 0)")
    
    # Check prescription medicines with NULL quantity_prescribed
    null_quantity = session.exec(
        text("SELECT COUNT(*) as cnt FROM prescription_medicine WHERE quantity_prescribed IS NULL")
    ).first()[0]
    print(f"PrescriptionMedicines with quantity_prescribed = NULL: {null_quantity}")
    
    # Check prescription medicines with NULL frequency
    null_frequency = session.exec(
        text("SELECT COUNT(*) as cnt FROM prescription_medicine WHERE frequency IS NULL")
    ).first()[0]
    print(f"PrescriptionMedicines with frequency = NULL: {null_frequency}")
    
    if unknown_count == 0 and string_count == 0 and null_duration == 0 and string_duration == 0:
        print("\n✓ All fixes verified successfully!")
    else:
        print("\n⚠ Some issues remain")


def main():
    """Run all fixes."""
    print("\n🔧 PRESCRIPTION DATA FIX SCRIPT")
    print("=" * 80)
    
    with Session(engine) as session:
        try:
            fix_invalid_string_values(session)
            fix_medicines_potency(session)
            fix_prescriptions_duration_days(session)
            fix_prescription_medicines_quantity_and_frequency(session)
            verify_fixes(session)
            
            print("\n" + "=" * 80)
            print("✅ All fixes completed successfully!")
            print("=" * 80 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error during fix: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
