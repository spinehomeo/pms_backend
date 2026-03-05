# scripts/setup_onsite_consultation.py
"""
Setup Script for Onsite Consultation Tables
===========================================

This script initializes all necessary tables and indexes for the onsite consultation system:
- SequenceCounter table (thread-safe numbering)
- OnsiteConsultationAudit table (audit trail)

Can be run manually if Alembic migrations haven't been applied yet.

Usage:
    python -m scripts.setup_onsite_consultation
"""

from sqlmodel import Session, create_engine, SQLModel

from core.config import settings
from models.onsite_consultation_model import SequenceCounter, OnsiteConsultationAudit


def setup_tables():
    """Create onsite consultation tables in the database."""

    engine = create_engine(str(settings.DATABASE_URL), echo=True)

    # Create tables
    SQLModel.metadata.create_all(engine)

    print("✓ SequenceCounter table created")
    print("✓ OnsiteConsultationAudit table created")
    print("\nOnsite consultation tables initialized successfully.")


if __name__ == "__main__":
    setup_tables()
