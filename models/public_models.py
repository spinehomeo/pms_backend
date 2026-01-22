"""
Public API Models - used for public endpoints (no authentication required)
"""
from datetime import date, time
from typing import Optional
from sqlmodel import SQLModel
from pydantic import EmailStr


class PatientRegisterPublic(SQLModel):
    """Public patient registration request model"""
    full_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None


class PublicBookingRequest(SQLModel):
    """Public appointment booking request model"""
    doctor_id: str
    patient_email: EmailStr
    appointment_date: date
    appointment_time: time
    reason: Optional[str] = None


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
