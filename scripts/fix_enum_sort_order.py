#!/usr/bin/env python
"""
Fix duplicate or inconsistent sort_order for all EnumOptions.

This script:
1. Groups options by enum_type
2. Sorts them by current sort_order + label
3. Reassigns sequential sort_order (0,1,2,...)
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


def fix_sort_orders(session: Session):
    logger.info("Fixing sort orders...\n")

    enum_types = session.exec(select(EnumType)).all()
    total_updated = 0

    for enum_type in enum_types:
        options = session.exec(
            select(EnumOption)
            .where(EnumOption.enum_type_id == enum_type.id)
        ).all()

        if not options:
            continue

        # Sort by current order, then label for stability
        options_sorted = sorted(
            options,
            key=lambda x: (x.sort_order if x.sort_order is not None else 9999, x.label)
        )

        logger.info(f"Processing {enum_type.key} ({len(options)} items)")

        for index, option in enumerate(options_sorted):
            if option.sort_order != index:
                logger.info(
                    f"  {option.value}: {option.sort_order} → {index}"
                )
                option.sort_order = index
                session.add(option)
                total_updated += 1

    session.commit()
    logger.info(f"\nSort order fix completed. Updated: {total_updated}")


def main():
    logger.info("=" * 60)
    logger.info("ENUM SORT ORDER FIX")
    logger.info("=" * 60)

    try:
        with Session(engine) as session:
            fix_sort_orders(session)

        logger.info("\n✓ Sort orders fixed successfully")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
