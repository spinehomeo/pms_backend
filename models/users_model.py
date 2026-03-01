import uuid
from datetime import date
from typing import List, Optional
from enum import Enum

from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship, SQLModel


class UserRole(str, Enum):
    DOCTOR = "doctor"
    STAFF = "staff"
    ADMIN = "admin"


# ========== DATABASE MODELS (CRUD) ==========
class UserBase(SQLModel):
    """Base user model - used for both DB and API"""
    email: Optional[EmailStr] = Field(default=None, unique=True, index=True, max_length=255)
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
    is_approved: bool = Field(default=False)  # NEW: Admin approval for doctors
    rejection_reason: Optional[str] = Field(default=None, max_length=500)  # NEW: Store rejection reason
    is_superuser: bool = Field(default=False)
    join_date: date = Field(default_factory=date.today)
    last_login: Optional[date] = Field(default=None)


class User(UserBase, table=True):
    """DATABASE MODEL for users - USED FOR CRUD"""
    __tablename__ = "user"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    
    # Relationships (doctors manage patients, cases, etc.)
    cases: List["PatientCase"] = Relationship(back_populates="doctor")
    prescriptions: List["Prescription"] = Relationship(back_populates="doctor")
    appointments: List["Appointment"] = Relationship(back_populates="doctor")
    follow_ups: List["FollowUp"] = Relationship(back_populates="doctor")
    availability_slots: List["DoctorAvailability"] = Relationship(back_populates="doctor")
    availability_exceptions: List["DoctorAvailabilityException"] = Relationship(back_populates="doctor")
    
    # Finance relationships
    cash_books: List["CashBook"] = Relationship(back_populates="doctor")
    # Note: finance_transactions is read-only (viewonly) in FinanceTransaction due to multiple FK paths
    
    @property
    def is_doctor(self) -> bool:
        """Check if user is a doctor"""
        return self.role == UserRole.DOCTOR



# ========== REQUEST MODELS (API Input) ==========
class UserCreate(SQLModel):
    """API INPUT MODEL for creating users
    
    ONLY for DOCTOR, STAFF, and ADMIN roles.
    Patients are created in the Patient table directly, not in User table.
    Email is mandatory for all users (doctors, staff, admin).
    """
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.DOCTOR)
    phone: Optional[str] = Field(default=None, max_length=20)
    specialization: Optional[str] = Field(default=None, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    is_verified: Optional[bool] = Field(default=False)


class UserRegister(SQLModel):
    """API INPUT MODEL for user registration
    
    Doctors and Staff both require admin approval.
    Doctors provide medical credentials upfront.
    """
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    # NEW: Role selection (doctor or staff)
    role: UserRole = Field(default=UserRole.DOCTOR, description="Account type: doctor or staff")
    # NEW: Doctor-only verification fields
    registration_number: Optional[str] = Field(default=None, max_length=100, description="Medical license/registration number (required for doctors)")
    specialization: Optional[str] = Field(default=None, max_length=255, description="Medical specialization (for doctors)")
    clinic_name: Optional[str] = Field(default=None, max_length=255, description="Practice/clinic name (for doctors)")
    clinic_address: Optional[str] = Field(default=None, description="Practice/clinic address (for doctors)")


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
    is_approved: Optional[bool] = None  # NEW: Admin can approve/reject users


class UserUpdateMe(SQLModel):
    """API INPUT MODEL for updating own profile"""
    full_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, min_length=5, max_length=255)
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


# ========== APPROVAL WORKFLOW MODELS ==========
class ApprovalRequest(SQLModel):
    """API INPUT MODEL for approving/rejecting users"""
    action: str = Field(description="'approve' or 'reject'")
    reason: Optional[str] = Field(default=None, max_length=500, description="Rejection reason (required if action=reject)")


class ApprovalResponse(SQLModel):
    """API OUTPUT MODEL for approval action result"""
    success: bool
    message: str
    user: UserPublic


class ApprovalStats(SQLModel):
    """API OUTPUT MODEL for dashboard statistics"""
    total_pending: int
    pending_doctors: int
    pending_staff: int
    pending_unverified_email: int
    approved_today: int
    rejected_today: int
    low_stock_items: int = 0
    revenue_today: float = 0.0
    revenue_this_month: float = 0.0


class UserStats(SQLModel):
    """API OUTPUT MODEL for comprehensive user statistics"""
    total_users: int
    active_users: int
    inactive_users: int
    
    total_doctors: int
    active_doctors: int
    pending_doctors: int
    
    total_staff: int
    active_staff: int
    pending_staff: int
    
    total_admins: int
    
    pending_verification: int  # Signed up but not verified email
    pending_approval: int      # Verified but not approved
    
    created_today: int
    created_this_week: int
    created_this_month: int