#!/usr/bin/env python
"""
Sync missing enum values based on provided DB snapshot.

Fixes:
- sets enum_type (NOT NULL)
- sets enum_type_id
- safe to run multiple times
- no autoflush issues
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db import engine
from models.enum_option_model import EnumType, EnumOption


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Missing values based on your JSON
# ------------------------------------------------------------------
ENUMS_TO_ADD = {
    "ExceptionType": [
        "unavailable",
        "custom_hours",
    ],

    "ManufacturerEnum": [
        "schwabe",
        "reckweg",
        "lemasar",
        "dolisos",
        "kamal",
        "masood",
        "bm",
        "kent",
        "brooks",
        "waris shah",
        "self packing",
    ],

    "FormEnum": [
        "diskette",
        "som",
        "blankets",
        "bio chemic",
        "homoeo tabs",
        "dilutions",
    ],
}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def labelize(value: str) -> str:
    return value.replace("_", " ").title()


def get_enum_type(session: Session, key: str) -> EnumType:
    with session.no_autoflush:
        enum_type = session.exec(
            select(EnumType).where(EnumType.key == key)
        ).first()

    if not enum_type:
        raise Exception(f"EnumType not found: {key}")

    return enum_type


def get_existing_values(session: Session, enum_type_id):
    with session.no_autoflush:
        options = session.exec(
            select(EnumOption).where(EnumOption.enum_type_id == enum_type_id)
        ).all()

    return {o.value for o in options}, len(options)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def sync_enums(session: Session):
    total_added = 0

    logger.info("\nSyncing enums from summary...\n")

    for enum_key, values in ENUMS_TO_ADD.items():
        logger.info(f"Processing: {enum_key}")

        enum_type = get_enum_type(session, enum_key)
        existing_values, current_count = get_existing_values(session, enum_type.id)

        sort_order = current_count

        for value in values:
            value = value.strip().lower()

            if value in existing_values:
                logger.info(f"  Exists: {value}")
                continue

            option = EnumOption(
                enum_type=enum_type.key,          # REQUIRED (fix)
                enum_type_id=enum_type.id,
                value=value,
                label=labelize(value),
                sort_order=sort_order,
                is_active=True,
                is_system=True,
                created_at=datetime.utcnow(),
                created_by=None,
            )

            session.add(option)
            logger.info(f"  Added: {value}")

            sort_order += 1
            total_added += 1

    session.commit()

    logger.info("\nCompleted")
    logger.info(f"Total added: {total_added}")


def main():
    logger.info("=" * 60)
    logger.info("SYNC ENUMS FROM PROVIDED DATA")
    logger.info("=" * 60)

    try:
        with Session(engine) as session:
            sync_enums(session)

        logger.info("\n✓ Sync successful")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
