#!/usr/bin/env python
"""
Update FollowupStatus enum options.

Standalone script to update FollowupStatus enum with:
1. Change "Confirmed (Payment Confirmed)" label to "Payment Confirmed"
2. Add new status "patient_left" for when patient doesn't respond or willing to continue

Usage:
    python scripts/update_followup_enums.py
    
Or from uv:
    uv run scripts/update_followup_enums.py
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


def update_followup_enums(session: Session) -> None:
    """Update FollowupStatus enum options"""
    logger.info("Starting FollowupStatus enum updates...\n")
    
    # Get FollowupStatus enum type
    enum_type = session.exec(
        select(EnumType).where(EnumType.key == "FollowupStatus")
    ).first()
    
    if not enum_type:
        logger.error("✗ FollowupStatus enum type not found")
        return
    
    # Update 1: Change "confirmed" label from "Confirmed (Payment Confirmed)" to "Payment Confirmed"
    confirmed_option = session.exec(
        select(EnumOption).where(
            EnumOption.enum_type_id == enum_type.id,
            EnumOption.value == "confirmed"
        )
    ).first()
    
    if confirmed_option:
        old_label = confirmed_option.label
        confirmed_option.label = "Payment Confirmed"
        session.add(confirmed_option)
        logger.info(f"✓ Updated 'confirmed' status label")
        logger.info(f"  From: '{old_label}'")
        logger.info(f"  To:   '{confirmed_option.label}'")
    else:
        logger.warning("⊘ 'confirmed' status not found in FollowupStatus")
    
    # Update 2: Add new "patient_left" status if it doesn't exist
    patient_left_option = session.exec(
        select(EnumOption).where(
            EnumOption.enum_type_id == enum_type.id,
            EnumOption.value == "patient_left"
        )
    ).first()
    
    if not patient_left_option:
        # Get current max sort_order
        existing_options = session.exec(
            select(EnumOption).where(
                EnumOption.enum_type_id == enum_type.id
            )
        ).all()
        
        max_sort_order = max([opt.sort_order for opt in existing_options], default=0)
        
        new_option = EnumOption(
            enum_type_id=enum_type.id,
            enum_type="FollowupStatus",
            value="patient_left",
            label="Patient Left",
            sort_order=max_sort_order + 1,
            is_system=True,
            is_active=True,
        )
        session.add(new_option)
        logger.info(f"✓ Added new 'patient_left' status")
        logger.info(f"  Label: 'Patient Left'")
        logger.info(f"  Sort Order: {new_option.sort_order}")
    else:
        logger.info(f"⊘ 'patient_left' status already exists")
    
    session.commit()
    logger.info("\n✓ FollowupStatus enum updates completed successfully")


def main() -> None:
    """Main entry point"""
    logger.info("=" * 70)
    logger.info("FOLLOWUP STATUS ENUM UPDATE SCRIPT")
    logger.info("=" * 70 + "\n")
    
    try:
        with Session(engine) as session:
            update_followup_enums(session)
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ FOLLOWUP ENUMS UPDATED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info("\nUpdated FollowupStatus options:")
        logger.info("  - scheduled      → Scheduled")
        logger.info("  - confirmed      → Payment Confirmed")
        logger.info("  - completed      → Completed")
        logger.info("  - case_closed    → Case Closed")
        logger.info("  - patient_left   → Patient Left (NEW)")
        logger.info("  - cancelled      → Cancelled")
        
    except Exception as e:
        logger.error(f"\n✗ Error updating enums: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
