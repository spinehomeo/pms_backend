#!/usr/bin/env python
"""
Cleanup script for EnumOptions

This script:
1. Removes duplicate options (case-insensitive)
2. Converts values to lowercase
3. Converts labels to Title Case
4. Keeps only one record per unique value

Usage:
    python scripts/cleanup_enum_options.py
"""

import sys
import logging
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db import engine
from models.enum_option_model import EnumType, EnumOption


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def title_case(text: str) -> str:
    """Convert text to Title Case safely"""
    if not text:
        return text
    return text.strip().title()


def normalize_value(value: str) -> str:
    """Normalize value for storage"""
    return value.strip().lower()


def cleanup_enum_options(session: Session):
    logger.info("Starting EnumOptions cleanup...\n")

    enum_types = session.exec(select(EnumType)).all()

    total_deleted = 0
    total_updated = 0

    for enum_type in enum_types:
        logger.info(f"Processing: {enum_type.key}")

        options = session.exec(
            select(EnumOption).where(
                EnumOption.enum_type_id == enum_type.id
            )
        ).all()

        # Group by normalized value
        grouped = defaultdict(list)

        for opt in options:
            normalized = normalize_value(opt.value)
            grouped[normalized].append(opt)

        for normalized_value, group in grouped.items():

            # Keep the first option, delete others
            keep_option = group[0]

            # Normalize value + label
            new_label = title_case(keep_option.label or keep_option.value)

            if keep_option.value != normalized_value:
                keep_option.value = normalized_value
                total_updated += 1

            if keep_option.label != new_label:
                keep_option.label = new_label
                total_updated += 1

            session.add(keep_option)

            # Delete duplicates
            if len(group) > 1:
                logger.info(
                    f"  Removing duplicates for '{normalized_value}' ({len(group)-1} removed)"
                )

                for duplicate in group[1:]:
                    session.delete(duplicate)
                    total_deleted += 1

    session.commit()

    logger.info("\nCleanup completed")
    logger.info(f"Updated records: {total_updated}")
    logger.info(f"Deleted duplicates: {total_deleted}")


def main():
    logger.info("=" * 60)
    logger.info("ENUM CLEANUP SCRIPT")
    logger.info("=" * 60)

    try:
        with Session(engine) as session:
            cleanup_enum_options(session)

        logger.info("\n✓ Enum cleanup completed successfully")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
