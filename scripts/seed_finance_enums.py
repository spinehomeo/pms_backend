#!/usr/bin/env python
"""
Standalone script to seed finance-related enum types and options into the database.

Finance Enums:
  - TransactionNature: Cash flow direction (CASH_IN, CASH_OUT)
  - TransactionCategory: Transaction classification (MEDICINE_PURCHASE, CONSULTATION, etc.)

Usage:
    python scripts/seed_finance_enums.py
    
Or from uv:
    uv run scripts/seed_finance_enums.py
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
# FINANCE ENUM SEEDS
# ============================================================================

FINANCE_ENUM_TYPE_SEEDS = [
    ("TransactionNature", "Transaction Nature", "Cash flow direction for financial transactions"),
    ("TransactionCategory", "Transaction Category", "Purpose or classification of financial transactions"),
]

FINANCE_ENUM_OPTIONS_SEEDS = {
    "TransactionNature": [
        ("CASH_IN", "Cash In - Income / Sales / Receipts"),
        ("CASH_OUT", "Cash Out - Expenses / Purchases / Payments"),
    ],
    "TransactionCategory": [
        ("MEDICINE_PURCHASE", "Medicine Purchase - Medicines and pharmacy stock"),
        ("CONSULTATION", "Consultation - Patient consultation income"),
        ("EQUIPMENT", "Equipment - Medical or clinic equipment"),
        ("UTILITIES", "Utilities - Electricity, water, internet"),
        ("SALARY", "Salary - Staff salary payments"),
        ("RENT", "Rent - Clinic or office rent"),
        ("LAB_INCOME", "Lab Income - Laboratory test income"),
        ("PROCEDURE_INCOME", "Procedure Income - Minor procedure income"),
        ("OTHER", "Other - Miscellaneous"),
    ],
}


def seed_finance_enum_types(session: Session) -> None:
    """Seed finance enum types into the database"""
    logger.info("Starting to seed finance enum types...")
    
    for key, label, description in FINANCE_ENUM_TYPE_SEEDS:
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
            logger.info(f"✓ Created finance enum type: {key}")
        else:
            logger.info(f"⊘ Finance enum type '{key}' already exists")
    
    session.commit()
    logger.info("Finance enum types seeded successfully\n")


def seed_finance_enum_options(session: Session) -> None:
    """Seed finance enum options into the database"""
    logger.info("Starting to seed finance enum options...")
    
    total_options = 0
    
    for enum_type_key, options in FINANCE_ENUM_OPTIONS_SEEDS.items():
        # Get the enum type
        enum_type = session.exec(
            select(EnumType).where(EnumType.key == enum_type_key)
        ).first()
        
        if not enum_type:
            logger.warning(f"✗ Finance enum type '{enum_type_key}' not found, skipping options")
            continue
        
        logger.info(f"\n  Seeding finance options for '{enum_type_key}':")
        
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
    logger.info(f"\n✓ Finance enum options seeded successfully ({total_options} new options added)\n")


def main() -> None:
    """Main entry point"""
    logger.info("=" * 70)
    logger.info("FINANCE ENUM SEEDING SCRIPT")
    logger.info("=" * 70 + "\n")
    
    try:
        with Session(engine) as session:
            seed_finance_enum_types(session)
            seed_finance_enum_options(session)
        
        logger.info("=" * 70)
        logger.info("✓ FINANCE ENUMS SEEDED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info("\nYou can now use the finance enum endpoints:")
        logger.info("  GET  /enums/doctor/TransactionNature")
        logger.info("  GET  /enums/doctor/TransactionCategory")
        logger.info("  POST /finance/transactions")
        
    except Exception as e:
        logger.error(f"\n✗ Error seeding finance enums: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
