# models/appointment_models.py
import uuid
from datetime import date, datetime, time
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel
import sqlalchemy as sa


class AppointmentBase(SQLModel):
    """Base appointment model"""
    appointment_date: date
    appointment_time: time
    duration_minutes: int = Field(default=30, ge=15)
    status: str = Field(default="scheduled")
    consultation_type: str = Field(default="first", max_length=50)
    reason: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class Appointment(AppointmentBase, table=True):
    """DATABASE MODEL for appointments - USED FOR CRUD"""
    __tablename__ = "appointment"
    
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
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Composite indexes
    __table_args__ = (
        sa.Index('idx_appointment_datetime', 'appointment_date', 'appointment_time'),
        sa.Index('idx_doctor_appointments', 'doctor_id', 'appointment_date', 'status'),
    )
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="appointments")
    doctor: "User" = Relationship(back_populates="appointments")
    case: Optional["PatientCase"] = Relationship(back_populates="appointment")


# ========== REQUEST MODELS (API Input) ==========
class AppointmentCreate(AppointmentBase):
    """API INPUT MODEL for creating appointments"""
    patient_id: uuid.UUID


class AppointmentUpdate(SQLModel):
    """API INPUT MODEL for updating appointments"""
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    consultation_type: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


# ========== RESPONSE MODELS (API Output) ==========
class AppointmentPublic(AppointmentBase):
    """API OUTPUT MODEL for single appointment"""
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    created_at: datetime
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None


class AppointmentsPublic(SQLModel):
    """API OUTPUT MODEL for list of appointments"""
    data: List[AppointmentPublic]
    count: int


class UpcomingAppointmentsResponse(SQLModel):
    """API OUTPUT MODEL for upcoming appointments"""
    appointments: List[AppointmentPublic]
    grouped_by_date: dict
    from_date: str
    to_date: str


class AvailabilityResponse(SQLModel):
    """API OUTPUT MODEL for availability check"""
    date: str
    day_of_week: str
    availability_slots: List[dict]
    booked_slots: List[dict]
    available_slots: List[dict]
    total_available: int