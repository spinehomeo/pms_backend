# models/case_models.py
import uuid
from datetime import date
from typing import Optional, List, Dict, Any
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


# ========== DATABASE MODELS (CRUD) ==========
class PatientCaseBase(SQLModel):
    """Base case model - keeping only required fields"""
    # Required fields
    chief_complaint_patient: str = Field(max_length=500)
    chief_complaint_duration: str = Field(max_length=100)
    
    # Optional standard fields
    physicals: Optional[str] = Field(default=None)
    noted_complaint_doctor: Optional[str] = Field(default=None, max_length=500)
    peculiar_symptoms: Optional[str] = Field(default=None)
    causation: Optional[str] = Field(default=None)
    lab_reports: Optional[str] = Field(default=None)
    
    # Dynamic fields stored as JSON
    custom_fields: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )


class PatientCase(PatientCaseBase, table=True):
    """DATABASE MODEL for patient cases - USED FOR CRUD"""
    __tablename__ = "patient_case"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    patient_id: uuid.UUID = Field(
        foreign_key="patient.id",
        nullable=False,
        index=True
    )
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    appointment_id: Optional[uuid.UUID] = Field(
        foreign_key="appointment.id",
        nullable=True,
        index=True
    )
    case_date: date = Field(default_factory=date.today)
    case_number: str = Field(max_length=50, unique=True, index=True)
    status: str = Field(default="open", max_length=50)  # From CaseStatus enum: open, active, closed, archived
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="cases")
    doctor: "User" = Relationship(back_populates="cases")
    appointment: Optional["Appointment"] = Relationship(back_populates="case")
    prescriptions: List["Prescription"] = Relationship(back_populates="case")
    follow_ups: List["FollowUp"] = Relationship(back_populates="case")


# ========== REQUEST MODELS (API Input) ==========
class PatientCaseCreate(SQLModel):
    """API INPUT MODEL for creating cases"""
    patient_id: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None
    
    # Required fields
    chief_complaint_patient: str
    chief_complaint_duration: str
    
    # Optional standard fields
    physicals: Optional[str] = None
    noted_complaint_doctor: Optional[str] = None
    peculiar_symptoms: Optional[str] = None
    causation: Optional[str] = None
    lab_reports: Optional[str] = None
    
    # Dynamic custom fields
    custom_fields: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(default="open", max_length=50)  # From CaseStatus enum


class PatientCaseUpdate(SQLModel):
    """API INPUT MODEL for updating cases"""
    # All fields are optional for updates
    chief_complaint_patient: Optional[str] = None
    chief_complaint_duration: Optional[str] = None
    physicals: Optional[str] = None
    noted_complaint_doctor: Optional[str] = None
    peculiar_symptoms: Optional[str] = None
    causation: Optional[str] = None
    lab_reports: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, max_length=50)  # From CaseStatus enum


# ========== RESPONSE MODELS (API Output) ==========
class PatientCasePublic(SQLModel):
    """API OUTPUT MODEL for single case"""
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None
    case_date: date
    case_number: str
    status: str  # From CaseStatus enum
    
    # Core required fields
    chief_complaint_patient: str
    chief_complaint_duration: str
    
    # Optional standard fields
    physicals: Optional[str] = None
    noted_complaint_doctor: Optional[str] = None
    peculiar_symptoms: Optional[str] = None
    causation: Optional[str] = None
    lab_reports: Optional[str] = None
    
    # Dynamic custom fields
    custom_fields: Optional[Dict[str, Any]] = None
    
    # Relationship data
    patient_name: Optional[str] = None  # Will be populated from relationship
    patient_phone: Optional[str] = None  # Will be populated from relationship
    patient_city: Optional[str] = None  # Will be populated from relationship


class CasesPublic(SQLModel):
    """API OUTPUT MODEL for list of cases"""
    data: List[PatientCasePublic]
    count: int


class CaseTimelineResponse(SQLModel):
    """API OUTPUT MODEL for case timeline"""
    case: PatientCasePublic
    followups: List["FollowUpPublic"] = []
    prescriptions: List["PrescriptionPublic"] = []
    total_followups: int = 0
    total_prescriptions: int = 0