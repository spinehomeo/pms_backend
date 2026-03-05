# models/followup_models.py
import uuid
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


# ========== DATABASE MODELS (CRUD) ==========
class FollowUpBase(SQLModel):
    """Base follow-up model"""
    subjective_improvement: Optional[str] = Field(default=None)
    objective_findings: Optional[str] = Field(default=None)
    aggravation: Optional[str] = Field(default=None)
    amelioration: Optional[str] = Field(default=None)
    new_symptoms: Optional[str] = Field(default=None)
    general_state: Optional[str] = Field(default=None)
    plan: Optional[str] = Field(default=None)
    
    # Dynamic fields stored as JSON
    custom_fields: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )


class FollowUp(FollowUpBase, table=True):
    """DATABASE MODEL for follow-ups - USED FOR CRUD"""
    __tablename__ = "follow_up"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: uuid.UUID = Field(
        foreign_key="patient_case.id",
        nullable=False,
        index=True
    )
    prescription_id: uuid.UUID = Field(
        foreign_key="prescription.id",
        nullable=False,
        index=True
    )
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    follow_up_date: date = Field(default_factory=date.today)
    interval_days: int = Field(default=30, ge=7)
    next_follow_up_date: Optional[date] = Field(default=None)
    status: str = Field(default="scheduled", max_length=50)  # From FollowupStatus enum: scheduled, confirmed, completed, case_closed, patient_left, cancelled
    
    # Payment tracking - Followup is treated as next appointment with payment workflow
    payment_confirmed: bool = Field(default=False)
    payment_confirmed_date: Optional[datetime] = Field(default=None)
    
    # Relationships
    case: "PatientCase" = Relationship(back_populates="follow_ups")
    prescription: "Prescription" = Relationship(back_populates="follow_ups")
    doctor: "User" = Relationship(back_populates="follow_ups")


# ========== REQUEST MODELS (API Input) ==========
class FollowUpCreate(SQLModel):
    """API INPUT MODEL for creating follow-ups"""
    case_id: uuid.UUID
    prescription_id: uuid.UUID
    subjective_improvement: Optional[str] = None
    objective_findings: Optional[str] = None
    aggravation: Optional[str] = None
    amelioration: Optional[str] = None
    new_symptoms: Optional[str] = None
    general_state: Optional[str] = None
    plan: Optional[str] = None
    next_follow_up_date: Optional[date] = None
    status: Optional[str] = Field(default="scheduled", max_length=50)  # From FollowupStatus enum
    payment_confirmed: Optional[bool] = Field(default=False)  # Payment confirmation status
    custom_fields: Optional[Dict[str, Any]] = None  # Dynamic custom fields


class FollowUpUpdate(SQLModel):
    """API INPUT MODEL for updating follow-ups"""
    subjective_improvement: Optional[str] = None
    objective_findings: Optional[str] = None
    aggravation: Optional[str] = None
    amelioration: Optional[str] = None
    new_symptoms: Optional[str] = None
    general_state: Optional[str] = None
    plan: Optional[str] = None
    next_follow_up_date: Optional[date] = None
    status: Optional[str] = Field(None, max_length=50)  # From FollowupStatus enum
    payment_confirmed: Optional[bool] = None  # Payment confirmation status
    custom_fields: Optional[Dict[str, Any]] = None  # Dynamic custom fields


# ========== RESPONSE MODELS (API Output) ==========
class FollowUpPublic(FollowUpBase):
    """API OUTPUT MODEL for single follow-up"""
    id: uuid.UUID
    case_id: uuid.UUID
    prescription_id: uuid.UUID
    doctor_id: uuid.UUID
    follow_up_date: date
    interval_days: int
    next_follow_up_date: Optional[date] = None
    status: str  # From FollowupStatus enum
    payment_confirmed: bool = False  # Payment confirmation status
    payment_confirmed_date: Optional[datetime] = None  # When payment was confirmed
    patient_name: Optional[str] = None
    case_number: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class FollowUpsPublic(SQLModel):
    """API OUTPUT MODEL for list of follow-ups"""
    data: List[FollowUpPublic]
    count: int


class CaseFollowupsResponse(SQLModel):
    """API OUTPUT MODEL for case follow-ups"""
    case_id: uuid.UUID
    followups: List[FollowUpPublic]
    timeline: List[dict]
    total_followups: int
    first_followup: Optional[FollowUpPublic]
    latest_followup: Optional[FollowUpPublic]


class DueFollowupsResponse(SQLModel):
    """API OUTPUT MODEL for due follow-ups"""
    overdue_count: int
    due_today_count: int
    upcoming_count: int
    overdue_items: List[FollowUpPublic]
    due_today_items: List[FollowUpPublic]
    upcoming_items: List[dict]  # Contains follow-up + days_until