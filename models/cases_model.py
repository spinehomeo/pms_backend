# models/case_models.py
import uuid
from datetime import date
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel


# ========== DATABASE MODELS (CRUD) ==========
class PatientCaseBase(SQLModel):
    """Base case model"""
    chief_complaint: str = Field(max_length=500)
    duration: str = Field(max_length=100)
    onset: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    sensation: Optional[str] = Field(default=None)
    modalities: Optional[str] = Field(default=None)
    concomitants: Optional[str] = Field(default=None)
    generals: Optional[str] = Field(default=None)
    mentals: Optional[str] = Field(default=None)
    physicals: Optional[str] = Field(default=None)
    miasm_assessment: Optional[str] = Field(default=None)
    vitality_assessment: Optional[str] = Field(default=None)
    case_notes: Optional[str] = Field(default=None)


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
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="cases")
    doctor: "User" = Relationship(back_populates="cases")
    appointment: Optional["Appointment"] = Relationship(back_populates="case")
    prescription: Optional["Prescription"] = Relationship(back_populates="case")
    follow_ups: List["FollowUp"] = Relationship(back_populates="case")


# ========== REQUEST MODELS (API Input) ==========
class PatientCaseCreate(PatientCaseBase):
    """API INPUT MODEL for creating cases"""
    patient_id: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None


class PatientCaseUpdate(SQLModel):
    """API INPUT MODEL for updating cases"""
    chief_complaint: Optional[str] = None
    duration: Optional[str] = None
    onset: Optional[str] = None
    location: Optional[str] = None
    sensation: Optional[str] = None
    modalities: Optional[str] = None
    concomitants: Optional[str] = None
    generals: Optional[str] = None
    mentals: Optional[str] = None
    physicals: Optional[str] = None
    miasm_assessment: Optional[str] = None
    vitality_assessment: Optional[str] = None
    case_notes: Optional[str] = None


# ========== RESPONSE MODELS (API Output) ==========
class PatientCasePublic(PatientCaseBase):
    """API OUTPUT MODEL for single case"""
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None
    case_date: date
    case_number: str
    patient_name: Optional[str] = None  # Will be populated from relationship


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