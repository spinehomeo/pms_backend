#!/usr/bin/env python
"""
Merge semantic duplicate EnumOptions.

This script:
1. Detects duplicates ignoring spaces and hyphens
2. Keeps one canonical record
3. Converts label to Title Case
4. Deletes extra duplicate records safely

Usage:
    python scripts/merge_enum_duplicates.py
"""

import sys
import logging
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db import engine
from models.enum_option_model import EnumType, EnumOption


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Normalization helpers
# -------------------------------------------------------------------

def semantic_key(value: str) -> str:
    """
    Normalize value for semantic comparison.
    Removes spaces and hyphens, lowercase.
    Example:
        'No Show' -> 'noshow'
        'no-show' -> 'noshow'
        'inter current' -> 'intercurrent'
    """
    return value.replace(" ", "").replace("-", "").lower().strip()


def title_case(text: str) -> str:
    if not text:
        return text
    return text.strip().title()


# -------------------------------------------------------------------
# Main merge logic
# -------------------------------------------------------------------

def merge_enum_options(session: Session):
    logger.info("Starting semantic merge of enum options...\n")

    enum_types = session.exec(select(EnumType)).all()

    total_deleted = 0
    total_updated = 0

    for enum_type in enum_types:
        logger.info(f"Processing EnumType: {enum_type.key}")

        options = session.exec(
            select(EnumOption).where(
                EnumOption.enum_type_id == enum_type.id
            )
        ).all()

        grouped = defaultdict(list)

        for opt in options:
            key = semantic_key(opt.value)
            grouped[key].append(opt)

        for key, group in grouped.items():
            if len(group) == 1:
                continue  # No duplicates

            logger.info(
                f"  Found semantic duplicates for '{key}' -> {len(group)} records"
            )

            # Prefer system option if exists
            keep_option = None
            for opt in group:
                if opt.is_system:
                    keep_option = opt
                    break

            # Otherwise keep first
            if not keep_option:
                keep_option = group[0]

            # Normalize kept record
            normalized_value = keep_option.value.strip().lower()
            normalized_label = title_case(keep_option.label or keep_option.value)

            if keep_option.value != normalized_value:
                keep_option.value = normalized_value
                total_updated += 1

            if keep_option.label != normalized_label:
                keep_option.label = normalized_label
                total_updated += 1

            session.add(keep_option)

            # Delete others
            for opt in group:
                if opt.id != keep_option.id:
                    logger.info(
                        f"    Deleting duplicate: {opt.value} (id={opt.id})"
                    )
                    session.delete(opt)
                    total_deleted += 1

    session.commit()

    logger.info("\nMerge completed")
    logger.info(f"Updated records: {total_updated}")
    logger.info(f"Deleted duplicates: {total_deleted}")


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------

def main():
    logger.info("=" * 60)
    logger.info("ENUM SEMANTIC MERGE SCRIPT")
    logger.info("=" * 60)

    try:
        with Session(engine) as session:
            merge_enum_options(session)

        logger.info("\n✓ Semantic merge completed successfully")

    except Exception as e:
        logger.error(f"Error during merge: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
