# models/doctor_availability_model.py
import uuid
from datetime import time
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum
import sqlalchemy as sa


class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


# ========== DATABASE MODELS (CRUD) ==========
class DoctorAvailabilityBase(SQLModel):
    """Base doctor availability model"""
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    is_available: bool = Field(default=True)
    max_patients_per_slot: Optional[int] = Field(default=None, ge=1)
    notes: Optional[str] = Field(default=None)


class DoctorAvailability(DoctorAvailabilityBase, table=True):
    """DATABASE MODEL for doctor availability - USED FOR CRUD"""
    __tablename__ = "doctor_availability"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    
    # Composite indexes for efficient querying
    __table_args__ = (
        sa.Index('idx_doctor_day', 'doctor_id', 'day_of_week'),
        sa.Index('idx_doctor_availability', 'doctor_id', 'day_of_week', 'is_available'),
    )
    
    # Relationships
    doctor: "User" = Relationship(back_populates="availability_slots")


# ========== REQUEST MODELS (API Input) ==========
class DoctorAvailabilityCreate(DoctorAvailabilityBase):
    """API INPUT MODEL for creating doctor availability"""
    pass


class DoctorAvailabilityUpdate(SQLModel):
    """API INPUT MODEL for updating doctor availability"""
    day_of_week: Optional[DayOfWeek] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_available: Optional[bool] = None
    max_patients_per_slot: Optional[int] = None
    notes: Optional[str] = None


class DoctorAvailabilityBulkCreate(SQLModel):
    """API INPUT MODEL for bulk creating availability for multiple days"""
    availability_slots: List[DoctorAvailabilityCreate]


# ========== RESPONSE MODELS (API Output) ==========
class DoctorAvailabilityPublic(DoctorAvailabilityBase):
    """API OUTPUT MODEL for single availability"""
    id: uuid.UUID
    doctor_id: uuid.UUID


class DoctorAvailabilitiesPublic(SQLModel):
    """API OUTPUT MODEL for list of availabilities"""
    data: List[DoctorAvailabilityPublic]
    count: int


class DoctorScheduleResponse(SQLModel):
    """API OUTPUT MODEL for doctor's weekly schedule"""
    doctor_id: uuid.UUID
    schedule: dict  # day_of_week -> list of time slots


class AvailableSlotCheck(SQLModel):
    """API OUTPUT MODEL for checking available slots on a specific day"""
    day_of_week: DayOfWeek
    available_slots: List[dict]
    total_slots: int
    booked_count: int
