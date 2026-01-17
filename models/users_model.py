import uuid
from datetime import date
from typing import List, Optional
from enum import Enum

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


class UserRole(str, Enum):
    DOCTOR = "doctor"
    STAFF = "staff"
    ADMIN = "admin"
    PATIENT = "patient"


# ========== DATABASE MODELS (CRUD) ==========
class UserBase(SQLModel):
    """Base user model - used for both DB and API"""
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    full_name: str = Field(max_length=255, nullable=False)
    role: UserRole = Field(default=UserRole.DOCTOR)
    phone: Optional[str] = Field(default=None, max_length=20)
    specialization: Optional[str] = Field(default=None, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    clinic_name: Optional[str] = Field(default=None, max_length=255)
    clinic_address: Optional[str] = Field(default=None)
    consultation_fee: Optional[float] = Field(default=None, ge=0)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    join_date: date = Field(default_factory=date.today)
    last_login: Optional[date] = Field(default=None)


class User(UserBase, table=True):
    """DATABASE MODEL for users - USED FOR CRUD"""
    __tablename__ = "user"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    
    # Relationships (based on other model files)
    patients: List["Patient"] = Relationship(back_populates="doctor")
    cases: List["PatientCase"] = Relationship(back_populates="doctor")
    prescriptions: List["Prescription"] = Relationship(back_populates="doctor")
    appointments: List["Appointment"] = Relationship(back_populates="doctor")
    medicine_stock: List["DoctorMedicineStock"] = Relationship(back_populates="doctor")
    follow_ups: List["FollowUp"] = Relationship(back_populates="doctor")
    availability_slots: List["DoctorAvailability"] = Relationship(back_populates="doctor")
    
    @property
    def is_doctor(self) -> bool:
        """Check if user is a doctor"""
        return self.role == UserRole.DOCTOR



# ========== REQUEST MODELS (API Input) ==========
class UserCreate(SQLModel):
    """API INPUT MODEL for creating users"""
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.DOCTOR)
    phone: Optional[str] = Field(default=None, max_length=20)
    specialization: Optional[str] = Field(default=None, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)


class UserRegister(SQLModel):
    """API INPUT MODEL for user registration"""
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)


class UserUpdate(SQLModel):
    """API INPUT MODEL for updating users (admin)"""
    email: Optional[EmailStr] = Field(default=None, max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=255)
    role: Optional[UserRole] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    specialization: Optional[str] = Field(default=None, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    clinic_name: Optional[str] = Field(default=None, max_length=255)
    clinic_address: Optional[str] = None
    consultation_fee: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserUpdateMe(SQLModel):
    """API INPUT MODEL for updating own profile"""
    full_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    specialization: Optional[str] = Field(default=None, max_length=255)
    clinic_name: Optional[str] = Field(default=None, max_length=255)
    clinic_address: Optional[str] = None
    consultation_fee: Optional[float] = Field(default=None, ge=0)


class UpdatePassword(SQLModel):
    """API INPUT MODEL for changing password"""
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# ========== RESPONSE MODELS (API Output) ==========
class UserPublic(UserBase):
    """API OUTPUT MODEL for single user"""
    id: uuid.UUID


class UsersPublic(SQLModel):
    """API OUTPUT MODEL for list of users"""
    data: List[UserPublic]
    count: int


class DoctorStats(SQLModel):
    """API OUTPUT MODEL for doctor statistics"""
    total_patients: int = 0
    total_cases: int = 0
    total_appointments: int = 0
    total_prescriptions: int = 0
    upcoming_appointments: int = 0
    pending_followups: int = 0
    low_stock_items: int = 0
    revenue_today: float = 0.0
    revenue_this_month: float = 0.0