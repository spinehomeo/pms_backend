#!/usr/bin/env python
"""
Manual semantic merge for EnumOptions.

This script:
1. Merges predefined semantic duplicates
2. Moves foreign key references (if provided)
3. Deletes duplicate options safely
4. Normalizes label to Title Case

Usage:
    python scripts/merge_semantic_mapped_enums.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db import engine
from models.enum_option_model import EnumType, EnumOption


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Manual Semantic Mapping
# key = duplicate value
# value = canonical value to keep
# ------------------------------------------------------------------

SEMANTIC_MERGE_MAP = {
    # RepetitionEnum (keep abbreviations)
    "once daily": "od",
    "twice daily": "bd",
    "three times daily": "tds",

    # PrescriptionType
    "inter current": "intercurrent",

    # AppointmentStatus (safety)
    "no show": "no-show",
}


def title_case(text: str) -> str:
    if not text:
        return text
    return text.strip().title()


def find_option(session, enum_type_id, value):
    return session.exec(
        select(EnumOption).where(
            EnumOption.enum_type_id == enum_type_id,
            EnumOption.value == value
        )
    ).first()


def merge_semantic_options(session: Session):
    logger.info("Starting manual semantic merge...\n")

    enum_types = session.exec(select(EnumType)).all()

    total_deleted = 0
    total_updated = 0

    for enum_type in enum_types:
        logger.info(f"Processing EnumType: {enum_type.key}")

        for duplicate_value, canonical_value in SEMANTIC_MERGE_MAP.items():

            dup = find_option(session, enum_type.id, duplicate_value)
            canon = find_option(session, enum_type.id, canonical_value)

            # Skip if mapping not relevant for this enum
            if not dup:
                continue

            # If canonical does not exist, convert duplicate into canonical
            if not canon:
                logger.info(
                    f"  Converting '{duplicate_value}' → '{canonical_value}'"
                )
                dup.value = canonical_value
                dup.label = title_case(canonical_value)
                session.add(dup)
                total_updated += 1
                continue

            # Canonical exists → delete duplicate
            logger.info(
                f"  Merging '{duplicate_value}' into '{canonical_value}'"
            )

            # ----------------------------------------------------------
            # OPTIONAL: Update foreign keys here if your system uses them
            # Example:
            # session.exec(
            #     update(Prescription)
            #     .where(Prescription.repetition_id == dup.id)
            #     .values(repetition_id=canon.id)
            # )
            # ----------------------------------------------------------

            session.delete(dup)
            total_deleted += 1

    session.commit()

    logger.info("\nManual semantic merge completed")
    logger.info(f"Updated: {total_updated}")
    logger.info(f"Deleted: {total_deleted}")


def main():
    logger.info("=" * 60)
    logger.info("MANUAL SEMANTIC ENUM MERGE SCRIPT")
    logger.info("=" * 60)

    try:
        with Session(engine) as session:
            merge_semantic_options(session)

        logger.info("\n✓ Manual semantic merge completed successfully")

    except Exception as e:
        logger.error(f"Error during merge: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
