#!/usr/bin/env python
"""
Check prescription data in database to verify null/Unknown values.
Run with: uv run python scripts/check_prescription_data.py
"""
import sys
from sqlmodel import Session, select
from sqlalchemy import text

sys.path.insert(0, str(__file__).rsplit('\\', 2)[0])

from core.db import engine
from models.medicines_model import Medicine
from models.prescriptions_model import Prescription, PrescriptionMedicine


def check_medicines():
    """Check medicine potency values."""
    with Session(engine) as session:
        medicines = session.exec(select(Medicine)).all()
        
        print("\n" + "="*80)
        print("MEDICINES CHECK")
        print("="*80)
        print(f"Total medicines: {len(medicines)}")
        
        # Group by potency value
        potency_group = {}
        for med in medicines:
            key = med.potency or "NULL"
            if key not in potency_group:
                potency_group[key] = []
            potency_group[key].append(med.name)
        
        for potency, names in sorted(potency_group.items()):
            print(f"\nPotency = '{potency}' ({len(names)} medicines):")
            for name in names[:5]:
                print(f"  - {name}")
            if len(names) > 5:
                print(f"  ... and {len(names) - 5} more")


def check_prescriptions():
    """Check prescription data."""
    with Session(engine) as session:
        prescriptions = session.exec(select(Prescription)).all()
        
        print("\n" + "="*80)
        print("PRESCRIPTIONS CHECK")
        print("="*80)
        print(f"Total prescriptions: {len(prescriptions)}")
        
        if prescriptions:
            rx = prescriptions[0]
            print(f"\nSample prescription (ID: {rx.id}):")
            print(f"  - prescription_duration: {rx.prescription_duration}")
            print(f"  - duration_days: {rx.duration_days}")
            print(f"  - prescription_date: {rx.prescription_date}")
            
            # Check medicines in this prescription
            medicines_in_rx = session.exec(
                select(PrescriptionMedicine).where(
                    PrescriptionMedicine.prescription_id == rx.id
                )
            ).all()
            
            print(f"\n  Medicines in prescription ({len(medicines_in_rx)}):")
            for pm in medicines_in_rx[:3]:
                print(f"    - {pm.medicine.name}")
                print(f"      quantity_prescribed: {pm.quantity_prescribed}")
                print(f"      frequency: {pm.frequency}")
                print(f"      potency: {pm.medicine.potency}")


def check_raw_sql():
    """Check raw database stats."""
    with Session(engine) as session:
        print("\n" + "="*80)
        print("RAW DATABASE STATISTICS")
        print("="*80)
        
        # Medicines with Unknown potency
        result = session.exec(
            text("SELECT COUNT(*) as cnt FROM medicine WHERE potency = 'Unknown'")
        ).first()
        print(f"\nMedicines with potency = 'Unknown': {result[0]}")
        
        # Prescriptions with null duration_days
        result = session.exec(
            text("SELECT COUNT(*) as cnt FROM prescription WHERE duration_days IS NULL")
        ).first()
        print(f"Prescriptions with duration_days = NULL: {result[0]}")
        
        # PrescriptionMedicines with null quantity_prescribed
        result = session.exec(
            text("SELECT COUNT(*) as cnt FROM prescription_medicine WHERE quantity_prescribed IS NULL")
        ).first()
        print(f"PrescriptionMedicines with quantity_prescribed = NULL: {result[0]}")
        
        # PrescriptionMedicines with null frequency
        result = session.exec(
            text("SELECT COUNT(*) as cnt FROM prescription_medicine WHERE frequency IS NULL")
        ).first()
        print(f"PrescriptionMedicines with frequency = NULL: {result[0]}")


if __name__ == "__main__":
    try:
        check_medicines()
        check_prescriptions()
        check_raw_sql()
        print("\n" + "="*80 + "\n")
    except Exception as e:
        print(f"\n✗ Error checking data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
