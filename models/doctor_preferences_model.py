# models/doctor_preferences_model.py
import uuid
import sqlalchemy as sa
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


class DoctorCaseFieldPreference(SQLModel, table=True):
    """Store doctor's preferred case fields and their configurations"""
    __tablename__ = "doctor_case_field_preference"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    
    # Field name as stored in database
    field_name: str = Field(max_length=100, index=True)
    
    # Display name for the field (can be different from field_name)
    display_name: str = Field(max_length=100)
    
    # Field type: text, textarea, number, date, select, etc.
    field_type: str = Field(default="text", max_length=50)
    
    # Whether this field is required
    is_required: bool = Field(default=False)
    
    # Whether this field is enabled for this doctor
    is_enabled: bool = Field(default=True)
    
    # Position/order in the form
    position: int = Field(default=0)
    
    # Field configuration (options for select, validation rules, etc.)
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Composite unique constraint
    __table_args__ = (
        sa.UniqueConstraint('doctor_id', 'field_name', name='uq_doctor_field'),
    )


class DoctorCaseTemplate(SQLModel):
    """Response model for doctor's case template"""
    doctor_id: uuid.UUID
    template_name: Optional[str] = None
    fields: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


# Standard field definitions that doctors can enable/disable
STANDARD_FIELDS = [
    {"field_name": "chief_complaint_patient", "display_name": "Chief Complaint (Patient's Words)", "field_type": "textarea", "default_required": True},
    {"field_name": "chief_complaint_duration", "display_name": "Chief Complaint Duration", "field_type": "text", "default_required": True},
    {"field_name": "physicals", "display_name": "Physical Examination", "field_type": "textarea", "default_required": False},
    {"field_name": "noted_complaint_doctor", "display_name": "Noted Complaint (Doctor)", "field_type": "textarea", "default_required": False},
    {"field_name": "peculiar_symptoms", "display_name": "Peculiar Symptoms", "field_type": "textarea", "default_required": False},
    {"field_name": "causation", "display_name": "Causation", "field_type": "text", "default_required": False},
    {"field_name": "lab_reports", "display_name": "Lab Reports", "field_type": "textarea", "default_required": False},
]


class DoctorFollowUpFieldPreference(SQLModel, table=True):
    """Store doctor's preferred follow-up fields and their configurations"""
    __tablename__ = "doctor_followup_field_preference"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    
    # Field name as stored in database
    field_name: str = Field(max_length=100, index=True)
    
    # Display name for the field (can be different from field_name)
    display_name: str = Field(max_length=100)
    
    # Field type: text, textarea, number, date, select, etc.
    field_type: str = Field(default="text", max_length=50)
    
    # Whether this field is required
    is_required: bool = Field(default=False)
    
    # Whether this field is enabled for this doctor
    is_enabled: bool = Field(default=True)
    
    # Position/order in the form
    position: int = Field(default=0)
    
    # Field configuration (options for select, validation rules, etc.)
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Composite unique constraint
    __table_args__ = (
        sa.UniqueConstraint('doctor_id', 'field_name', name='uq_doctor_followup_field'),
    )


# Standard field definitions for follow-ups that doctors can enable/disable
FOLLOWUP_STANDARD_FIELDS = [
    {"field_name": "subjective_improvement", "display_name": "Subjective Improvement", "field_type": "textarea", "default_required": False},
    {"field_name": "objective_findings", "display_name": "Objective Findings", "field_type": "textarea", "default_required": False},
    {"field_name": "aggravation", "display_name": "Aggravation", "field_type": "textarea", "default_required": False},
    {"field_name": "amelioration", "display_name": "Amelioration", "field_type": "textarea", "default_required": False},
    {"field_name": "new_symptoms", "display_name": "New Symptoms", "field_type": "textarea", "default_required": False},
    {"field_name": "general_state", "display_name": "General State", "field_type": "textarea", "default_required": False},
    {"field_name": "plan", "display_name": "Plan", "field_type": "textarea", "default_required": False},
]
