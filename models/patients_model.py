# models/patient_models.py
import uuid
from datetime import date
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel


# ========== DATABASE MODELS (CRUD) ==========
class PatientBase(SQLModel):
    """Base patient model - used for both DB and API"""
    full_name: str = Field(max_length=255, nullable=False)
    gender: str = Field(max_length=20)
    phone: str = Field(max_length=20, nullable=False)
    cnic: str = Field(max_length=15, nullable=False, unique=True)  # National ID card number
    date_of_birth: Optional[date] = Field(default=None)
    
    # Contact Information
    email: Optional[str] = Field(default=None, max_length=255)
    phone_secondary: Optional[str] = Field(default=None, max_length=20)
    
    # Addresses
    residential_address: Optional[str] = Field(default=None)
    postal_address: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None, max_length=100)
    
    # Professional Information
    occupation: Optional[str] = Field(default=None, max_length=255)
    
    # Payment Information
    payment_status: bool = Field(default=False)  # True = paid, False = unpaid
    
    # Referral Information
    referred_by: Optional[str] = Field(default=None, max_length=255)
    
    # Medical Information
    medical_history: Optional[str] = Field(default=None)
    drug_allergies: Optional[str] = Field(default=None)
    family_history: Optional[str] = Field(default=None)
    current_medications: Optional[str] = Field(default=None)
    
    # Additional Notes
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
    is_active: bool = Field(default=True)
    hashed_password: Optional[str] = Field(default=None)  # For patient login (phone + password)
    last_login: Optional[date] = Field(default=None)  # Track last login date
    
    # Relationships
    doctor: "User" = Relationship()  # Doctor who manages this patient (no back_populates - Patient is not in User relationships)
    cases: List["PatientCase"] = Relationship(back_populates="patient")
    appointments: List["Appointment"] = Relationship(back_populates="patient")
    
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
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    cnic: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    
    # Address Updates
    residential_address: Optional[str] = None
    postal_address: Optional[str] = None
    city: Optional[str] = None
    
    # Professional Updates
    occupation: Optional[str] = None
    
    # Payment Updates
    payment_status: Optional[bool] = None
    
    # Referral Updates
    referred_by: Optional[str] = None
    
    # Medical Updates
    medical_history: Optional[str] = None
    drug_allergies: Optional[str] = None
    family_history: Optional[str] = None
    current_medications: Optional[str] = None
    
    # Other Updates
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# ========== RESPONSE MODELS (API Output) ==========
class DoctorBasicInfo(SQLModel):
    """Doctor information for patient response"""
    id: uuid.UUID
    full_name: str
    specialization: Optional[str] = None
    phone: Optional[str] = None
    clinic_name: Optional[str] = None
    clinic_address: Optional[str] = None


class PatientPublic(PatientBase):
    """API OUTPUT MODEL for single patient"""
    id: uuid.UUID
    created_date: date
    last_visit_date: Optional[date] = None
    is_active: bool
    age: Optional[int] = None
    doctor: DoctorBasicInfo  # Return doctor details instead of just doctor_id


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
    payment_status: bool