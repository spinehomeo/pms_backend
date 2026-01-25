"""
Public API Models - used for public endpoints (no authentication required)
"""
from datetime import date, time
from typing import Optional, Dict, Any
from uuid import UUID
from sqlmodel import SQLModel
from pydantic import EmailStr


class PatientRegisterPublic(SQLModel):
    """Public patient registration request model"""
    full_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None


class PatientRegisterPhoneOnly(SQLModel):
    """Patient registration with phone number and name only"""
    full_name: str
    phone: str
    password: str = None  # Optional - can be set during first login
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "phone": "03001234567",
                "password": "SecurePass123"
            }
        }


class PatientRegisterSimple(SQLModel):
    """Simplified patient registration - name, gender, phone, and doctor_id"""
    full_name: str
    gender: str  # "male", "female", "other", "child"
    phone: str
    doctor_id: UUID  # Doctor selected from main website
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "gender": "male",
                "phone": "03001234567",
                "doctor_id": "d4e7e6f0-579c-402a-b266-98de85604a54"
            }
        }


class PatientLoginSimple(SQLModel):
    """Simplified patient login - name and phone only"""
    full_name: str
    phone: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "phone": "03001234567"
            }
        }


class PatientLoginRequest(SQLModel):
    """Patient login request - using phone number instead of email"""
    phone: str
    password: str
    remember_me: bool = False


class PatientLoginResponse(SQLModel):
    """Patient login response with token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    patient: Dict[str, Any]


class PatientQuickAccessResponse(SQLModel):
    """Patient quick access response - combines registration and login"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    patient: Dict[str, Any]
    message: str = "Patient registered and logged in successfully"


class PublicBookingRequest(SQLModel):
    """Public appointment booking request model - aligned with quick-access flow"""
    doctor_id: str
    full_name: str
    phone: str
    gender: str = "other"  # Optional: can be "male", "female", "other", "child"
    appointment_date: date
    appointment_time: time
    reason: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "doctor_id": "uuid",
                "full_name": "John Doe",
                "phone": "03001234567",
                "gender": "male",
                "appointment_date": "2026-01-25",
                "appointment_time": "14:30",
                "reason": "General checkup"
            }
        }


class DoctorPublicInfo(SQLModel):
    """Public information about a doctor"""
    id: str
    full_name: str
    specialization: Optional[str] = None
    clinic_name: Optional[str] = None
    consultation_fee: Optional[float] = None


class AvailableSlot(SQLModel):
    """Available appointment slot"""
    start: str
    end: str
    duration_minutes: int = 30
    booked: bool = False  # Whether this slot is already booked


class AvailabilityResponse(SQLModel):
    """Availability check response"""
    date: str
    day_of_week: str
    available_slots: list[AvailableSlot]
    doctor: Optional[DoctorPublicInfo] = None
    message: Optional[str] = None


class AppointmentBookingResponse(SQLModel):
    """Appointment booking response"""
    success: bool
    appointment_id: Optional[str] = None
    message: str
