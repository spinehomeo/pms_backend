#!/usr/bin/env python
"""
Standalone script to add "onsite" consultation type to the ConsultationType enum.

Adds Onsite Consultation Type:
  - onsite: Walk-in / Onsite Consultation

Usage:
    python scripts/seed_consultation_type_onsite.py
    
Or from uv:
    uv run scripts/seed_consultation_type_onsite.py
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
# CONSULTATION TYPE ONSITE SEED
# ============================================================================

CONSULTATION_TYPE_ONSITE = ("onsite", "Onsite Consultation")


def seed_consultation_type_onsite(session: Session) -> None:
    """Add onsite consultation type to ConsultationType enum"""
    logger.info("=" * 70)
    logger.info("CONSULTATION TYPE ONSITE SEEDING SCRIPT")
    logger.info("=" * 70 + "\n")
    
    # Get the ConsultationType enum type
    enum_type = session.exec(
        select(EnumType).where(EnumType.key == "ConsultationType")
    ).first()
    
    if not enum_type:
        logger.error("✗ ConsultationType enum not found in database")
        logger.error("  Please ensure the system enums are seeded first")
        sys.exit(1)
    
    logger.info(f"Found ConsultationType enum (ID: {enum_type.id})\n")
    
    # Check if onsite option already exists
    existing = session.exec(
        select(EnumOption).where(
            (EnumOption.enum_type_id == enum_type.id) &
            (EnumOption.value == "onsite")
        )
    ).first()
    
    if existing:
        logger.warning("✗ Onsite consultation type already exists in the database")
        logger.warning(f"  Value: {existing.value}")
        logger.warning(f"  Label: {existing.label}")
        logger.warning(f"  Active: {existing.is_active}")
        return
    
    # Get the current max sort_order
    max_sort = session.exec(
        select(EnumOption).where(
            EnumOption.enum_type_id == enum_type.id
        )
    ).all()
    
    sort_order = len(max_sort)  # Next position after existing options
    
    # Create the new onsite option
    value, label = CONSULTATION_TYPE_ONSITE
    onsite_option = EnumOption(
        enum_type_id=enum_type.id,
        enum_type="ConsultationType",
        value=value,
        label=label,
        sort_order=sort_order,
        is_system=True,
        is_active=True,
    )
    
    session.add(onsite_option)
    session.commit()
    
    logger.info(f"✓ Successfully added 'onsite' consultation type")
    logger.info(f"  Value: {value}")
    logger.info(f"  Label: {label}")
    logger.info(f"  Sort Order: {sort_order}")
    logger.info(f"  System: True (cannot be deleted)")
    
    logger.info("\n" + "=" * 70)
    logger.info("✓ CONSULTATION TYPE ONSITE SEEDED SUCCESSFULLY")
    logger.info("=" * 70)
    logger.info("\nYou can now use 'onsite' as a consultation_type value:")
    logger.info("  POST /consultations/onsite")
    logger.info("  Body: { ... \"consultation_type\": \"onsite\", ... }")


def main() -> None:
    """Main entry point"""
    try:
        with Session(engine) as session:
            seed_consultation_type_onsite(session)
    except Exception as e:
        logger.error(f"\n✗ Error seeding consultation type onsite: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
