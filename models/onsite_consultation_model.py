# models/onsite_consultation_model.py
"""
Onsite Consultation Models
===========================
Models for onsite/walk-in consultations with:
- Thread-safe sequence counter for case/prescription numbering
- Audit trail for consultation creation
- Idempotency tracking
"""

import uuid
from datetime import date, datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column
import sqlalchemy as sa


# ============================================================================
# SEQUENCE COUNTER TABLE (Thread-Safe Numbering)
# ============================================================================

class SequenceCounter(SQLModel, table=True):
    """
    Thread-safe counter for generating sequential case/prescription numbers.
    Uses database-level locking to prevent race conditions.
    
    Example:
        - Counter prefix: "C-MAR26" (case number)
        - Current sequence: 017
        - Next number: "C-MAR26-018"
    """
    __tablename__ = "sequence_counter"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    counter_type: str = Field(
        max_length=50,
        nullable=False,
        index=True,
    )  # "case" | "prescription"
    prefix: str = Field(max_length=50, nullable=False)  # e.g. "C-MAR26" or "RX-2026-03"
    current_sequence: int = Field(default=0, ge=0)  # Current sequence number
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Composite index: (counter_type, prefix) for fast lookups with locking
    __table_args__ = (
        sa.Index("idx_counter_type_prefix", "counter_type", "prefix", unique=True),
    )


# ============================================================================
# CONSULTATION AUDIT TRAIL
# ============================================================================

class OnsiteConsultationAudit(SQLModel, table=True):
    """
    Audit trail for all onsite consultations.
    Tracks who created the consultation and when.
    
    Useful for:
    - Dispute resolution ("Who created this entry?")
    - Compliance/regulatory reports
    - Doctor activity tracking
    """
    __tablename__ = "onsite_consultation_audit"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # IDs of created resources
    patient_id: uuid.UUID = Field(foreign_key="patient.id", nullable=False, index=True)
    appointment_id: uuid.UUID = Field(foreign_key="appointment.id", nullable=False, index=True)
    case_id: uuid.UUID = Field(foreign_key="patient_case.id", nullable=False, index=True)
    prescription_id: Optional[uuid.UUID] = Field(foreign_key="prescription.id", nullable=True)
    follow_up_id: Optional[uuid.UUID] = Field(foreign_key="follow_up.id", nullable=True)
    
    # Who created it
    doctor_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    
    # When created
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.now().astimezone().tzinfo))
    
    # Optional idempotency key to prevent duplicate submissions
    # If client provides same idempotency_key within 24h, return cached response
    idempotency_key: Optional[str] = Field(max_length=255, nullable=True, index=True)
    
    # Track if patient was new or existing
    is_new_patient: bool = Field(default=True)
    patient_phone: str = Field(max_length=20)  # For quick lookup of duplicates
    
    # Indexes for audit queries
    __table_args__ = (
        sa.Index("idx_audit_doctor_date", "doctor_id", "created_at"),
        sa.Index("idx_audit_patient_phone", "patient_phone", "created_at"),
        sa.Index("idx_audit_idempotency", "idempotency_key"),
    )


# ============================================================================
# REQUEST SCHEMAS (API Input) — Imported from onsite_consultation.py
# ============================================================================
# These are re-exported from onsite_consultation.py to keep definitions together.
# See the route file for full schema definitions.
