# models/patient_models.py
import uuid
from datetime import date
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum


class PatientGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    CHILD = "child"


# ========== DATABASE MODELS (CRUD) ==========
class PatientBase(SQLModel):
    """Base patient model - used for both DB and API"""
    full_name: str = Field(max_length=255, nullable=False)
    date_of_birth: Optional[date] = Field(default=None)
    gender: PatientGender
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None)
    occupation: Optional[str] = Field(default=None, max_length=255)
    referred_by: Optional[str] = Field(default=None, max_length=255)
    medical_history: Optional[str] = Field(default=None)
    drug_allergies: Optional[str] = Field(default=None)
    family_history: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class Patient(PatientBase, table=True):
    """DATABASE MODEL for patients - USED FOR CRUD"""
    __tablename__ = "patient"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    created_date: date = Field(default_factory=date.today)
    last_visit_date: Optional[date] = Field(default=None)
    
    # Relationships
    doctor: "User" = Relationship(back_populates="patients")
    cases: List["PatientCase"] = Relationship(back_populates="patient")
    appointments: List["Appointment"] = Relationship(back_populates="patient")
    medicine_usage_logs: List["MedicineUsageLog"] = Relationship(back_populates="patient")
    
    @property
    def age(self) -> Optional[int]:
        """Calculate age dynamically"""
        if not self.date_of_birth:
            return None
        today = date.today()
        age = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age


# ========== REQUEST MODELS (API Input) ==========
class PatientCreate(PatientBase):
    """API INPUT MODEL for creating patients"""
    pass


class PatientUpdate(SQLModel):
    """API INPUT MODEL for updating patients"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    occupation: Optional[str] = None
    medical_history: Optional[str] = None
    drug_allergies: Optional[str] = None
    family_history: Optional[str] = None
    notes: Optional[str] = None


# ========== RESPONSE MODELS (API Output) ==========
class PatientPublic(PatientBase):
    """API OUTPUT MODEL for single patient"""
    id: uuid.UUID
    doctor_id: uuid.UUID
    created_date: date
    last_visit_date: Optional[date] = None
    age: Optional[int] = None
    
    @property
    def age(self) -> Optional[int]:
        """Calculate age for API response"""
        if not self.date_of_birth:
            return None
        today = date.today()
        age = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age


class PatientsPublic(SQLModel):
    """API OUTPUT MODEL for list of patients"""
    data: List[PatientPublic]
    count: int


class PatientStats(SQLModel):
    """API OUTPUT MODEL for patient statistics"""
    patient_id: uuid.UUID
    total_cases: int
    total_appointments: int
    total_prescriptions: int
    last_visit_date: Optional[date]
    age: Optional[int]