# models/doctor_availability_exception_model.py
import uuid
from datetime import date, time, datetime
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum
import sqlalchemy as sa


class ExceptionType(str, Enum):
    """Types of availability exceptions"""
    UNAVAILABLE = "unavailable"  # Doctor is completely unavailable
    CUSTOM_HOURS = "custom_hours"  # Doctor has different hours this day
    HOLIDAY = "holiday"  # Public holiday or personal leave


# ========== DATABASE MODELS (CRUD) ==========
class DoctorAvailabilityExceptionBase(SQLModel):
    """Base doctor availability exception model"""
    exception_date: date
    exception_type: ExceptionType
    start_time: Optional[time] = Field(default=None)
    end_time: Optional[time] = Field(default=None)
    reason: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)


class DoctorAvailabilityException(DoctorAvailabilityExceptionBase, table=True):
    """DATABASE MODEL for doctor availability exceptions - USED FOR CRUD"""
    __tablename__ = "doctor_availability_exception"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Composite indexes for efficient querying
    __table_args__ = (
        sa.Index('idx_doctor_exception_date', 'doctor_id', 'exception_date'),
        sa.UniqueConstraint('doctor_id', 'exception_date', name='uq_doctor_exception_date'),
    )
    
    # Relationships
    doctor: "User" = Relationship(back_populates="availability_exceptions")


# ========== REQUEST MODELS (API Input) ==========
class DoctorAvailabilityExceptionCreate(SQLModel):
    """API INPUT MODEL for creating availability exception"""
    exception_date: date = Field(description="Specific date for the exception")
    exception_type: ExceptionType = Field(default=ExceptionType.UNAVAILABLE)
    start_time: Optional[time] = Field(default=None, description="Start time for custom hours")
    end_time: Optional[time] = Field(default=None, description="End time for custom hours")
    reason: Optional[str] = Field(default=None, max_length=500, description="Reason for exception")


class DoctorAvailabilityExceptionUpdate(SQLModel):
    """API INPUT MODEL for updating availability exception"""
    exception_type: Optional[ExceptionType] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


# ========== RESPONSE MODELS (API Output) ==========
class DoctorAvailabilityExceptionPublic(DoctorAvailabilityExceptionBase):
    """API OUTPUT MODEL for single exception"""
    id: uuid.UUID
    doctor_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DoctorAvailabilityExceptionsPublic(SQLModel):
    """API OUTPUT MODEL for list of exceptions"""
    data: List[DoctorAvailabilityExceptionPublic]
    count: int
