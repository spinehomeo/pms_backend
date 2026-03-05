#!/usr/bin/env python
"""
Standalone script to seed all enum types and options into the database.

Includes: RepetitionEnum, PrescriptionType, UserRole, PatientGender, ConsultationType,
          AppointmentStatus, PrescriptionStatus, FollowupStatus, CaseStatus, 
          ScaleEnum, FormEnum, ManufacturerEnum, DayOfWeek, ExceptionType
          
Finance enums (TransactionNature, TransactionCategory) are seeded separately in:
  scripts/seed_finance_enums.py

Usage:
    python scripts/seed_enums.py
    
Or from uv:
    uv run scripts/seed_enums.py
"""

import sys
import logging
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db import engine
from models.enum_option_model import EnumType, EnumOption


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================================
# ENUM SEEDS - All 10 Enum Types + Options
# ============================================================================

ENUM_TYPE_SEEDS = [
    ("RepetitionEnum", "Repetition", "Prescription repetition frequency"),
    ("PrescriptionType", "Prescription Type", "Types of homeopathic prescriptions"),
    ("UserRole", "User Role", "System roles"),
    ("PatientGender", "Patient Gender", "Gender options for patient profile"),
    ("ConsultationType", "Consultation Type", "Types of consultation appointments"),
    ("AppointmentStatus", "Appointment Status", "Lifecycle status of appointments"),
    ("PrescriptionStatus", "Prescription Status", "Lifecycle status of prescriptions"),
    ("FollowupStatus", "Followup Status", "Status of follow-up appointments"),
    ("CaseStatus", "Case Status", "Status of patient cases"),
    ("ScaleEnum", "Scale", "Medicine potency scale"),
    ("FormEnum", "Medicine Form", "Physical form of medicine"),
    ("ManufacturerEnum", "Manufacturer", "Medicine manufacturers"),
    ("DayOfWeek", "Day of Week", "Days for doctor availability"),
    ("ExceptionType", "Exception Type", "Availability exception categories"),
]

ENUM_OPTIONS_SEEDS = {
    "RepetitionEnum": [
        ("OD", "Once Daily (OD)"),
        ("BD", "Twice Daily (BD)"),
        ("TDS", "Three Times Daily (TDS)"),
        ("Once Weekly", "Once Weekly"),
        ("Once in 10 Days", "Once in 10 Days"),
        ("Fortnightly", "Fortnightly"),
        ("Monthly", "Monthly"),
    ],
    "PrescriptionType": [
        ("Constitutional", "Constitutional"),
        ("Classical", "Classical"),
        ("Inter Current", "Inter Current"),
        ("Pure Bio Chemic", "Pure Bio Chemic"),
        ("Mother Tincture", "Mother Tincture"),
        ("Patent", "Patent"),
    ],
    "UserRole": [
        ("admin", "Admin"),
        ("doctor", "Doctor"),
        ("staff", "Staff"),
    ],
    "PatientGender": [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
        ("child", "Child"),
    ],
    "ConsultationType": [
        ("first", "First Consultation"),
        ("follow-up", "Follow-up Consultation"),
        ("emergency", "Emergency Consultation"),
        ("review", "Review Consultation"),
    ],
    "AppointmentStatus": [
        ("scheduled", "Scheduled"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
        ("no-show", "No Show"),
    ],
    "PrescriptionStatus": [
        ("open", "Open"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ],
    "FollowupStatus": [
        ("scheduled", "Scheduled"),
        ("confirmed", "Payment Confirmed"),
        ("completed", "Completed"),
        ("case_closed", "Case Closed"),
        ("patient_left", "Patient Left"),
        ("cancelled", "Cancelled"),
    ],
    "CaseStatus": [
        ("open", "Open"),
        ("active", "Active"),
        ("closed", "Closed"),
        ("archived", "Archived"),
    ],
    "ScaleEnum": [
        ("X", "Decimal (X)"),
        ("C", "Centesimal (C)"),
        ("LM", "LM Potency"),
        ("Q", "Quinquagintamillesimal (Q)"),
        ("M", "Fifty Millesimal (M)"),
        ("CM", "Hundred Millesimal (CM)"),
        ("MM", "Thousand Millesimal (MM)"),
    ],
    "FormEnum": [
        ("Tablet", "Tablet"),
        ("Syrup", "Syrup"),
        ("Capsule", "Capsule"),
        ("Injection", "Injection"),
        ("Drops", "Drops"),
        ("Globules", "Globules"),
        ("Powder", "Powder"),
    ],
    "ManufacturerEnum": [
        ("Manufacturer A", "Manufacturer A"),
        ("Manufacturer B", "Manufacturer B"),
        ("Local", "Local"),
    ],
    "DayOfWeek": [
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        ("saturday", "Saturday"),
        ("sunday", "Sunday"),
    ],
    "ExceptionType": [
        ("Holiday", "Holiday"),
        ("Emergency", "Emergency"),
        ("Personal Leave", "Personal Leave"),
    ],
}


def seed_enum_types(session: Session) -> None:
    """Seed all 10 enum types into the database"""
    logger.info("Starting to seed enum types...")
    
    for key, label, description in ENUM_TYPE_SEEDS:
        existing = session.exec(
            select(EnumType).where(EnumType.key == key)
        ).first()
        
        if not existing:
            enum_type = EnumType(
                key=key,
                label=label,
                description=description,
                is_system=True,
                is_active=True,
            )
            session.add(enum_type)
            logger.info(f"✓ Created enum type: {key}")
        else:
            logger.info(f"⊘ Enum type '{key}' already exists")
    
    session.commit()
    logger.info("Enum types seeded successfully\n")


def seed_enum_options(session: Session) -> None:
    """Seed all enum options into the database"""
    logger.info("Starting to seed enum options...")
    
    total_options = 0
    
    for enum_type_key, options in ENUM_OPTIONS_SEEDS.items():
        # Get the enum type
        enum_type = session.exec(
            select(EnumType).where(EnumType.key == enum_type_key)
        ).first()
        
        if not enum_type:
            logger.warning(f"✗ Enum type '{enum_type_key}' not found, skipping options")
            continue
        
        logger.info(f"\n  Seeding options for '{enum_type_key}':")
        
        for i, (value, label) in enumerate(options):
            existing = session.exec(
                select(EnumOption).where(
                    EnumOption.enum_type_id == enum_type.id,
                    EnumOption.value == value
                )
            ).first()
            
            if not existing:
                option = EnumOption(
                    enum_type_id=enum_type.id,
                    enum_type=enum_type_key,
                    value=value,
                    label=label,
                    sort_order=i,
                    is_system=True,
                    is_active=True,
                )
                session.add(option)
                logger.info(f"    ✓ {value}")
                total_options += 1
            else:
                logger.info(f"    ⊘ {value} (already exists)")
    
    session.commit()
    logger.info(f"\n✓ Enum options seeded successfully ({total_options} new options added)\n")


def main() -> None:
    """Main entry point"""
    logger.info("=" * 70)
    logger.info("ENUM SEEDING SCRIPT")
    logger.info("=" * 70 + "\n")
    
    try:
        with Session(engine) as session:
            seed_enum_types(session)
            seed_enum_options(session)
        
        logger.info("=" * 70)
        logger.info("✓ ALL CORE ENUMS SEEDED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info("\nNext steps:")
        logger.info("  1. Seed finance enums: python scripts/seed_finance_enums.py")
        logger.info("  2. Use enum endpoints:")
        logger.info("     GET  /enums/doctor/all")
        logger.info("     GET  /enums/doctor/{enum_type_key}")
        
    except Exception as e:
        logger.error(f"\n✗ Error seeding enums: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
