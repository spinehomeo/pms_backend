# Doctor Availability Exception Implementation Guide

## Overview
This guide provides a scalable solution to handle date-specific unavailability for doctors without modifying the existing `DoctorAvailability` model.

---

## 1. Database Model (SQLAlchemy)

```python
# app/models.py or app/models/availability.py

from sqlalchemy import Column, String, Date, Time, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import date

class DoctorAvailabilityException(Base):
    """
    Represents date-specific unavailability or custom availability for doctors.
    Overrides the regular weekly schedule defined in DoctorAvailability.
    """
    __tablename__ = "doctor_availability_exceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    exception_date = Column(Date, nullable=False, index=True)
    
    # Exception type: 'unavailable', 'custom_hours', or 'holiday'
    exception_type = Column(String(50), nullable=False, default="unavailable")
    
    # Optional: For custom hours on specific dates
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    
    # Reason for the exception (optional)
    reason = Column(Text, nullable=True)
    
    # Soft delete flag
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    doctor = relationship("User", back_populates="availability_exceptions")

    # Unique constraint: One exception per doctor per date
    __table_args__ = (
        Index('idx_doctor_exception_date', 'doctor_id', 'exception_date'),
        UniqueConstraint('doctor_id', 'exception_date', name='uq_doctor_exception_date'),
    )
```

---

## 2. Pydantic Schemas

```python
# app/schemas/availability.py

from pydantic import BaseModel, Field, validator
from datetime import date, time
from uuid import UUID
from enum import Enum
from typing import Optional

class ExceptionType(str, Enum):
    """Types of availability exceptions"""
    UNAVAILABLE = "unavailable"  # Doctor is completely unavailable
    CUSTOM_HOURS = "custom_hours"  # Doctor has different hours this day
    HOLIDAY = "holiday"  # Public holiday or personal leave


class DoctorAvailabilityExceptionCreate(BaseModel):
    """Schema for creating an availability exception"""
    exception_date: date = Field(..., description="Specific date for the exception")
    exception_type: ExceptionType = Field(default=ExceptionType.UNAVAILABLE)
    start_time: Optional[time] = Field(None, description="Start time for custom hours")
    end_time: Optional[time] = Field(None, description="End time for custom hours")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for exception")

    @validator('exception_date')
    def validate_future_date(cls, v):
        """Ensure exception date is not in the past"""
        if v < date.today():
            raise ValueError("Exception date cannot be in the past")
        return v

    @validator('end_time')
    def validate_time_range(cls, v, values):
        """Ensure end time is after start time for custom hours"""
        if values.get('exception_type') == ExceptionType.CUSTOM_HOURS:
            if not values.get('start_time') or not v:
                raise ValueError("Both start_time and end_time required for custom hours")
            if v <= values['start_time']:
                raise ValueError("end_time must be after start_time")
        return v


class DoctorAvailabilityExceptionUpdate(BaseModel):
    """Schema for updating an availability exception"""
    exception_type: Optional[ExceptionType] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class DoctorAvailabilityExceptionPublic(BaseModel):
    """Schema for returning exception data"""
    id: UUID
    doctor_id: UUID
    exception_date: date
    exception_type: ExceptionType
    start_time: Optional[time]
    end_time: Optional[time]
    reason: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class DoctorAvailabilityExceptionsPublic(BaseModel):
    """Schema for returning list of exceptions"""
    data: list[DoctorAvailabilityExceptionPublic]
    count: int
```

---

## 3. Router Endpoints

```python
# app/routers/doctoravailability.py (add these endpoints)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional

router = APIRouter(prefix="/doctor-availability", tags=["🩺 Doctor Availability"])


@router.post("/exceptions", response_model=DoctorAvailabilityExceptionPublic)
async def create_availability_exception(
    *,
    session: Session = Depends(get_db),
    exception_in: DoctorAvailabilityExceptionCreate,
    current_user: User = Depends(get_current_active_doctor)
):
    """
    Create a date-specific availability exception.
    
    **Use cases:**
    - Mark a specific date as unavailable (vacation, sick leave)
    - Set custom hours for a specific date (early closure, late opening)
    - Mark public holidays
    
    **Access:** Doctor only (can only create exceptions for themselves)
    """
    # Check if exception already exists
    existing = session.query(DoctorAvailabilityException).filter(
        DoctorAvailabilityException.doctor_id == current_user.id,
        DoctorAvailabilityException.exception_date == exception_in.exception_date,
        DoctorAvailabilityException.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Exception already exists for {exception_in.exception_date}"
        )
    
    # Create new exception
    exception = DoctorAvailabilityException(
        doctor_id=current_user.id,
        **exception_in.model_dump()
    )
    
    session.add(exception)
    session.commit()
    session.refresh(exception)
    
    return exception


@router.get("/exceptions", response_model=DoctorAvailabilityExceptionsPublic)
async def list_availability_exceptions(
    *,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_doctor),
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    skip: int = 0,
    limit: int = 100
):
    """
    List all availability exceptions for the current doctor.
    
    **Access:** Doctor only
    """
    query = session.query(DoctorAvailabilityException).filter(
        DoctorAvailabilityException.doctor_id == current_user.id,
        DoctorAvailabilityException.is_active == True
    )
    
    if start_date:
        query = query.filter(DoctorAvailabilityException.exception_date >= start_date)
    if end_date:
        query = query.filter(DoctorAvailabilityException.exception_date <= end_date)
    
    query = query.order_by(DoctorAvailabilityException.exception_date)
    
    count = query.count()
    exceptions = query.offset(skip).limit(limit).all()
    
    return {"data": exceptions, "count": count}


@router.get("/exceptions/{exception_id}", response_model=DoctorAvailabilityExceptionPublic)
async def get_availability_exception(
    *,
    session: Session = Depends(get_db),
    exception_id: UUID,
    current_user: User = Depends(get_current_active_doctor)
):
    """Get a specific availability exception by ID"""
    exception = session.query(DoctorAvailabilityException).filter(
        DoctorAvailabilityException.id == exception_id,
        DoctorAvailabilityException.doctor_id == current_user.id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    return exception


@router.put("/exceptions/{exception_id}", response_model=DoctorAvailabilityExceptionPublic)
async def update_availability_exception(
    *,
    session: Session = Depends(get_db),
    exception_id: UUID,
    exception_in: DoctorAvailabilityExceptionUpdate,
    current_user: User = Depends(get_current_active_doctor)
):
    """Update an availability exception"""
    exception = session.query(DoctorAvailabilityException).filter(
        DoctorAvailabilityException.id == exception_id,
        DoctorAvailabilityException.doctor_id == current_user.id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    update_data = exception_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(exception, field, value)
    
    session.commit()
    session.refresh(exception)
    
    return exception


@router.delete("/exceptions/{exception_id}")
async def delete_availability_exception(
    *,
    session: Session = Depends(get_db),
    exception_id: UUID,
    current_user: User = Depends(get_current_active_doctor)
):
    """
    Delete (soft delete) an availability exception.
    This will restore normal weekly schedule for that date.
    """
    exception = session.query(DoctorAvailabilityException).filter(
        DoctorAvailabilityException.id == exception_id,
        DoctorAvailabilityException.doctor_id == current_user.id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    # Soft delete
    exception.is_active = False
    session.commit()
    
    return {"message": "Exception deleted successfully"}
```

---

## 4. Core Logic: Checking Availability

```python
# app/services/availability_service.py

from datetime import date, time, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from uuid import UUID

class AvailabilityService:
    """Service for checking doctor availability with exception handling"""
    
    @staticmethod
    def is_doctor_available(
        session: Session,
        doctor_id: UUID,
        check_date: date,
        check_time: time
    ) -> bool:
        """
        Check if doctor is available at specific date and time.
        
        Logic:
        1. First check for date-specific exceptions
        2. If exception exists:
           - If UNAVAILABLE or HOLIDAY: return False
           - If CUSTOM_HOURS: check if time is within custom hours
        3. If no exception, fall back to regular weekly schedule
        
        Returns:
            bool: True if doctor is available, False otherwise
        """
        
        # Step 1: Check for date-specific exception
        exception = session.query(DoctorAvailabilityException).filter(
            DoctorAvailabilityException.doctor_id == doctor_id,
            DoctorAvailabilityException.exception_date == check_date,
            DoctorAvailabilityException.is_active == True
        ).first()
        
        if exception:
            # Handle different exception types
            if exception.exception_type in ['unavailable', 'holiday']:
                return False
            
            elif exception.exception_type == 'custom_hours':
                # Check if time falls within custom hours
                if exception.start_time and exception.end_time:
                    return exception.start_time <= check_time <= exception.end_time
                return False
        
        # Step 2: No exception found, check regular weekly schedule
        day_name = check_date.strftime('%A')  # Get day name (Monday, Tuesday, etc.)
        
        availability = session.query(DoctorAvailability).filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.day_of_week == day_name,
            DoctorAvailability.is_active == True
        ).first()
        
        if not availability:
            return False
        
        # Check if time is within working hours
        return availability.start_time <= check_time <= availability.end_time
    
    
    @staticmethod
    def get_available_slots(
        session: Session,
        doctor_id: UUID,
        check_date: date,
        slot_duration: int = 30  # minutes
    ) -> List[dict]:
        """
        Get all available time slots for a doctor on a specific date.
        Respects both regular schedule and exceptions.
        
        Returns:
            List of dicts with 'start_time' and 'end_time' for each available slot
        """
        # Check for exception first
        exception = session.query(DoctorAvailabilityException).filter(
            DoctorAvailabilityException.doctor_id == doctor_id,
            DoctorAvailabilityException.exception_date == check_date,
            DoctorAvailabilityException.is_active == True
        ).first()
        
        if exception:
            if exception.exception_type in ['unavailable', 'holiday']:
                return []  # No slots available
            
            elif exception.exception_type == 'custom_hours':
                start = exception.start_time
                end = exception.end_time
            else:
                return []
        else:
            # Use regular weekly schedule
            day_name = check_date.strftime('%A')
            availability = session.query(DoctorAvailability).filter(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.day_of_week == day_name,
                DoctorAvailability.is_active == True
            ).first()
            
            if not availability:
                return []
            
            start = availability.start_time
            end = availability.end_time
        
        # Generate slots
        slots = []
        current = datetime.combine(check_date, start)
        end_datetime = datetime.combine(check_date, end)
        
        while current + timedelta(minutes=slot_duration) <= end_datetime:
            slots.append({
                'start_time': current.time(),
                'end_time': (current + timedelta(minutes=slot_duration)).time()
            })
            current += timedelta(minutes=slot_duration)
        
        return slots
    
    
    @staticmethod
    def get_availability_calendar(
        session: Session,
        doctor_id: UUID,
        start_date: date,
        end_date: date
    ) -> dict:
        """
        Get a calendar view of doctor availability for a date range.
        Shows regular schedule + exceptions.
        
        Returns:
            Dict with dates as keys and availability info as values
        """
        calendar = {}
        current_date = start_date
        
        while current_date <= end_date:
            day_name = current_date.strftime('%A')
            
            # Check for exception
            exception = session.query(DoctorAvailabilityException).filter(
                DoctorAvailabilityException.doctor_id == doctor_id,
                DoctorAvailabilityException.exception_date == current_date,
                DoctorAvailabilityException.is_active == True
            ).first()
            
            if exception:
                calendar[str(current_date)] = {
                    'available': exception.exception_type == 'custom_hours',
                    'type': exception.exception_type,
                    'start_time': str(exception.start_time) if exception.start_time else None,
                    'end_time': str(exception.end_time) if exception.end_time else None,
                    'reason': exception.reason
                }
            else:
                # Regular schedule
                availability = session.query(DoctorAvailability).filter(
                    DoctorAvailability.doctor_id == doctor_id,
                    DoctorAvailability.day_of_week == day_name,
                    DoctorAvailability.is_active == True
                ).first()
                
                if availability:
                    calendar[str(current_date)] = {
                        'available': True,
                        'type': 'regular',
                        'start_time': str(availability.start_time),
                        'end_time': str(availability.end_time),
                        'reason': None
                    }
                else:
                    calendar[str(current_date)] = {
                        'available': False,
                        'type': 'not_scheduled',
                        'start_time': None,
                        'end_time': None,
                        'reason': None
                    }
            
            current_date += timedelta(days=1)
        
        return calendar
```

---

## 5. Integration with Appointment Booking

```python
# app/routers/appointments.py (modify existing endpoint)

@router.post("/appointments", response_model=AppointmentPublic)
async def create_appointment(
    *,
    session: Session = Depends(get_db),
    appointment_in: AppointmentCreate,
    current_patient: Patient = Depends(get_current_active_patient)
):
    """
    Create new appointment (with availability checking).
    """
    # Check if doctor is available at requested date/time
    is_available = AvailabilityService.is_doctor_available(
        session=session,
        doctor_id=appointment_in.doctor_id,
        check_date=appointment_in.appointment_date,
        check_time=appointment_in.appointment_time
    )
    
    if not is_available:
        raise HTTPException(
            status_code=400,
            detail="Doctor is not available at the requested date and time"
        )
    
    # Continue with appointment creation...
    # [rest of your existing code]
```

---

## 6. Migration Script

```python
# alembic/versions/xxxx_add_availability_exceptions.py

"""Add doctor availability exceptions table

Revision ID: xxxx
Revises: previous_revision
Create Date: 2025-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'xxxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'doctor_availability_exceptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exception_date', sa.Date(), nullable=False),
        sa.Column('exception_type', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('end_time', sa.Time(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['doctor_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doctor_id', 'exception_date', name='uq_doctor_exception_date')
    )
    
    op.create_index(
        'idx_doctor_exception_date',
        'doctor_availability_exceptions',
        ['doctor_id', 'exception_date']
    )

def downgrade():
    op.drop_index('idx_doctor_exception_date', table_name='doctor_availability_exceptions')
    op.drop_table('doctor_availability_exceptions')
```

---

## 7. Usage Examples

### Example 1: Doctor marks vacation days
```python
# POST /doctor-availability/exceptions
{
  "exception_date": "2025-03-15",
  "exception_type": "unavailable",
  "reason": "Personal vacation"
}
```

### Example 2: Doctor has early closing on specific day
```python
# POST /doctor-availability/exceptions
{
  "exception_date": "2025-03-20",
  "exception_type": "custom_hours",
  "start_time": "09:00:00",
  "end_time": "13:00:00",
  "reason": "Half-day schedule for conference"
}
```

### Example 3: Mark public holiday
```python
# POST /doctor-availability/exceptions
{
  "exception_date": "2025-04-14",
  "exception_type": "holiday",
  "reason": "National holiday - Baisakhi"
}
```

---

## 8. Benefits of This Approach

✅ **No changes to existing model** - `DoctorAvailability` remains untouched
✅ **Scalable** - Can handle any number of exceptions
✅ **Flexible** - Supports different exception types (unavailable, custom hours, holidays)
✅ **Performance** - Indexed queries, efficient lookups
✅ **Clean separation** - Regular schedule vs exceptions are separate concerns
✅ **Backward compatible** - Existing appointment logic works with minor modifications
✅ **Future-proof** - Easy to extend with new exception types

---

## 9. Alternative Approaches (Why They're Less Ideal)

### ❌ Option 1: Add date fields to existing model
- Violates single responsibility principle
- Makes queries complex (weekly pattern OR specific dates)
- Difficult to maintain
- Data duplication issues

### ❌ Option 2: Use `is_active` flag dynamically
- Would require creating new records for each exception date
- Creates data bloat
- Makes it hard to distinguish permanent vs temporary unavailability
- No clear "restore to normal" mechanism

### ❌ Option 3: Store exceptions as JSON in existing table
- Loses relational benefits
- Can't query efficiently
- No referential integrity
- Difficult to validate

---

## 10. Next Steps

1. Create the database migration
2. Add the new model to your SQLAlchemy models
3. Create the Pydantic schemas
4. Add the exception endpoints to your router
5. Integrate `AvailabilityService` into appointment booking flow
6. Update frontend to allow doctors to set exceptions
7. Update appointment booking UI to respect exceptions

This solution gives you maximum flexibility while keeping your architecture clean and maintainable!
