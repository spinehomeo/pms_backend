# routes/doctor_availability.py
import uuid
from typing import Any, List, Optional
from datetime import date, time, datetime, timedelta, timezone
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Path
from sqlmodel import func, select, and_, or_

from api.deps import CurrentUser, SessionDep
from models.doctor_availability_model import (
    DoctorAvailability,
    DoctorAvailabilityCreate,
    DoctorAvailabilityUpdate,
    DoctorAvailabilityBulkCreate,
    DoctorAvailabilityPublic,
    DoctorAvailabilitiesPublic,
    DoctorScheduleResponse,
    AvailableSlotCheck,
)
from models.doctor_availability_exception_model import (
    DoctorAvailabilityException,
    DoctorAvailabilityExceptionCreate,
    DoctorAvailabilityExceptionUpdate,
    DoctorAvailabilityExceptionPublic,
    DoctorAvailabilityExceptionsPublic,
)
from models.appointments_model import Appointment
from models.patients_model import Patient
from models.login_model import Message

router = APIRouter(prefix="/doctor_availability", tags=["⏰ Doctor Availability"])


# ========== CREATE OPERATIONS ==========

@router.post("/", response_model=DoctorAvailabilityPublic)
def create_doctor_availability(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    availability_in: DoctorAvailabilityCreate
) -> Any:
    """
    Create a new availability slot for the doctor.
    
    A doctor can have multiple time slots per day (e.g., 9-12 AM and 3-5 PM).
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create availability slots")
    
    # Validate time slot
    if availability_in.start_time >= availability_in.end_time:
        raise HTTPException(
            status_code=400,
            detail="Start time must be before end time"
        )
    
    # Check for overlapping slots on the same day
    existing_slots = session.exec(
        select(DoctorAvailability).where(
            and_(
                DoctorAvailability.doctor_id == current_user.id,
                DoctorAvailability.day_of_week == availability_in.day_of_week
            )
        )
    ).all()
    
    for slot in existing_slots:
        # Check if new slot overlaps with existing slot
        # Convert to naive time if needed for comparison
        start_time = availability_in.start_time.replace(tzinfo=None) if hasattr(availability_in.start_time, 'tzinfo') and availability_in.start_time.tzinfo else availability_in.start_time
        end_time = availability_in.end_time.replace(tzinfo=None) if hasattr(availability_in.end_time, 'tzinfo') and availability_in.end_time.tzinfo else availability_in.end_time
        
        if (start_time < slot.end_time and 
            end_time > slot.start_time):
            raise HTTPException(
                status_code=409,
                detail=f"Time slot overlaps with existing slot: {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"
            )
    
    availability = DoctorAvailability.model_validate(
        availability_in,
        update={"doctor_id": current_user.id}
    )
    session.add(availability)
    session.commit()
    session.refresh(availability)
    
    return availability


@router.post("/bulk", response_model=DoctorAvailabilitiesPublic)
def create_doctor_availability_bulk(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    availability_bulk: DoctorAvailabilityBulkCreate
) -> Any:
    """
    Create multiple availability slots for the doctor at once.
    
    Useful for setting up weekly schedule.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create availability slots")
    
    created_slots = []
    
    for availability_in in availability_bulk.availability_slots:
        # Validate time slot
        if availability_in.start_time >= availability_in.end_time:
            raise HTTPException(
                status_code=400,
                detail=f"Start time must be before end time for {availability_in.day_of_week}"
            )
        
        # Check for overlapping slots on the same day
        existing_slots = session.exec(
            select(DoctorAvailability).where(
                and_(
                    DoctorAvailability.doctor_id == current_user.id,
                    DoctorAvailability.day_of_week == availability_in.day_of_week
                )
            )
        ).all()
        
        overlap_found = False
        for slot in existing_slots:
            # Convert to naive time if needed for comparison
            start_time = availability_in.start_time.replace(tzinfo=None) if hasattr(availability_in.start_time, 'tzinfo') and availability_in.start_time.tzinfo else availability_in.start_time
            end_time = availability_in.end_time.replace(tzinfo=None) if hasattr(availability_in.end_time, 'tzinfo') and availability_in.end_time.tzinfo else availability_in.end_time
            
            if (start_time < slot.end_time and 
                end_time > slot.start_time):
                overlap_found = True
                break
        
        if overlap_found:
            raise HTTPException(
                status_code=409,
                detail=f"One or more time slots overlap with existing availability"
            )
        
        availability = DoctorAvailability.model_validate(
            availability_in,
            update={"doctor_id": current_user.id}
        )
        session.add(availability)
        created_slots.append(availability)
    
    session.commit()
    for slot in created_slots:
        session.refresh(slot)
    
    return DoctorAvailabilitiesPublic(data=created_slots, count=len(created_slots))


# ========== READ OPERATIONS ==========

@router.get("/schedule", response_model=DoctorScheduleResponse)
def get_doctor_weekly_schedule(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get the doctor's complete weekly schedule organized by day.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can view their schedule")
    
    slots = session.exec(
        select(DoctorAvailability)
        .where(DoctorAvailability.doctor_id == current_user.id)
        .order_by(DoctorAvailability.day_of_week, DoctorAvailability.start_time)
    ).all()
    
    # Organize by day of week
    schedule = {}
    for slot in slots:
        day_name = slot.day_of_week.value
        if day_name not in schedule:
            schedule[day_name] = []
        
        schedule[day_name].append({
            "id": str(slot.id),
            "start_time": slot.start_time.strftime("%H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"),
            "is_available": slot.is_available,
            "max_patients_per_slot": slot.max_patients_per_slot,
            "notes": slot.notes
        })
    
    return DoctorScheduleResponse(
        doctor_id=current_user.id,
        schedule=schedule
    )


@router.get("/schedule/patient-info", response_model=DoctorScheduleResponse)
def get_doctor_schedule_with_patient_info(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get doctor's weekly schedule with patient appointment details.
    
    Shows which slots are booked and by which patients.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can view their schedule")
    
    slots = session.exec(
        select(DoctorAvailability)
        .where(DoctorAvailability.doctor_id == current_user.id)
        .order_by(DoctorAvailability.day_of_week, DoctorAvailability.start_time)
    ).all()
    
    # Organize by day of week with appointment info
    schedule = {}
    for slot in slots:
        day_name = slot.day_of_week.value
        if day_name not in schedule:
            schedule[day_name] = []
        
        # Get appointments for this slot
        booked_count = 0
        patients_booked = []
        
        # Get today's date and calculate the actual date for this day of week
        today = date.today()
        day_order = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
        days_ahead = (day_order[slot.day_of_week.value] - today.weekday()) % 7
        slot_date = today + timedelta(days=days_ahead)
        
        appointments = session.exec(
            select(Appointment)
            .where(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.appointment_date == slot_date,
                    Appointment.status.in_([
                        "scheduled",
                        "confirmed"
                    ])
                )
            )
        ).all()
        
        for appt in appointments:
            # Check if appointment falls within this slot
            appt_end_time = (
                datetime.combine(date.today(), appt.appointment_time) +
                timedelta(minutes=appt.duration_minutes)
            ).time()
            
            if appt.appointment_time >= slot.start_time and appt.appointment_time < slot.end_time:
                booked_count += 1
                patients_booked.append({
                    "patient_name": appt.patient.full_name,
                    "patient_phone": appt.patient.phone,
                    "appointment_time": appt.appointment_time.strftime("%H:%M"),
                    "duration": appt.duration_minutes,
                    "status": appt.status.value
                })
        
        schedule[day_name].append({
            "id": str(slot.id),
            "start_time": slot.start_time.strftime("%H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"),
            "is_available": slot.is_available,
            "max_patients_per_slot": slot.max_patients_per_slot,
            "booked_count": booked_count,
            "patients_booked": patients_booked,
            "notes": slot.notes
        })
    
    return DoctorScheduleResponse(
        doctor_id=current_user.id,
        schedule=schedule
    )


# ========== AVAILABILITY EXCEPTIONS ==========

@router.post("/exceptions", response_model=DoctorAvailabilityExceptionPublic)
def create_availability_exception(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    exception_in: DoctorAvailabilityExceptionCreate
) -> Any:
    """
    Create a date-specific availability exception.
    
    **Use cases:**
    - Mark a specific date as unavailable (vacation, sick leave)
    - Set custom hours for a specific date (early closure, late opening)
    - Mark public holidays
    
    **Access:** Doctor only (can only create exceptions for themselves)
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create availability exceptions")
    
    # Check if exception date is not in the past
    if exception_in.exception_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Exception date cannot be in the past"
        )
    
    # Validate time range for custom hours
    if exception_in.exception_type == "custom_hours":
        if not exception_in.start_time or not exception_in.end_time:
            raise HTTPException(
                status_code=400,
                detail="Both start_time and end_time are required for custom_hours exception"
            )
        if exception_in.end_time <= exception_in.start_time:
            raise HTTPException(
                status_code=400,
                detail="end_time must be after start_time"
            )
    
    # Check if exception already exists
    existing = session.exec(
        select(DoctorAvailabilityException).where(
            and_(
                DoctorAvailabilityException.doctor_id == current_user.id,
                DoctorAvailabilityException.exception_date == exception_in.exception_date,
                DoctorAvailabilityException.is_active == True
            )
        )
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
    
    return DoctorAvailabilityExceptionPublic.model_validate(exception)


@router.get("/exceptions", response_model=DoctorAvailabilityExceptionsPublic)
def list_availability_exceptions(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    exception_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
) -> Any:
    """
    List all availability exceptions for the current doctor.
    
    **Access:** Doctor only
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can view their exceptions")
    
    query = select(DoctorAvailabilityException).where(
        and_(
            DoctorAvailabilityException.doctor_id == current_user.id,
            DoctorAvailabilityException.is_active == True
        )
    )
    
    if start_date:
        query = query.where(DoctorAvailabilityException.exception_date >= start_date)
    if end_date:
        query = query.where(DoctorAvailabilityException.exception_date <= end_date)
    if exception_type:
        query = query.where(DoctorAvailabilityException.exception_type == exception_type)
    
    count_query = select(func.count()).select_from(DoctorAvailabilityException).where(
        and_(
            DoctorAvailabilityException.doctor_id == current_user.id,
            DoctorAvailabilityException.is_active == True
        )
    )
    
    if start_date:
        count_query = count_query.where(DoctorAvailabilityException.exception_date >= start_date)
    if end_date:
        count_query = count_query.where(DoctorAvailabilityException.exception_date <= end_date)
    if exception_type:
        count_query = count_query.where(DoctorAvailabilityException.exception_type == exception_type)
    
    query = query.order_by(DoctorAvailabilityException.exception_date)
    
    count = session.exec(count_query).one()
    exceptions = session.exec(query.offset(skip).limit(limit)).all()
    
    # Convert to response models to avoid relationship serialization issues
    exception_list = [
        DoctorAvailabilityExceptionPublic.model_validate(exc)
        for exc in exceptions
    ]
    
    return DoctorAvailabilityExceptionsPublic(data=exception_list, count=count)


@router.get("/exceptions/{exception_id}", response_model=DoctorAvailabilityExceptionPublic)
def get_availability_exception(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    exception_id: uuid.UUID = Path(..., description="Exception UUID")
) -> Any:
    """Get a specific availability exception by ID"""
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can view their exceptions")
    
    exception = session.get(DoctorAvailabilityException, exception_id)
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    if exception.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this exception")
    
    return DoctorAvailabilityExceptionPublic.model_validate(exception)


@router.put("/exceptions/{exception_id}", response_model=DoctorAvailabilityExceptionPublic)
def update_availability_exception(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    exception_id: uuid.UUID,
    exception_in: DoctorAvailabilityExceptionUpdate
) -> Any:
    """Update an availability exception"""
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update their exceptions")
    
    exception = session.get(DoctorAvailabilityException, exception_id)
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    if exception.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this exception")
    
    # Validate time range if updating to custom hours
    new_type = exception_in.exception_type or exception.exception_type
    new_start = exception_in.start_time or exception.start_time
    new_end = exception_in.end_time or exception.end_time
    
    if new_type == "custom_hours":
        if not new_start or not new_end:
            raise HTTPException(
                status_code=400,
                detail="Both start_time and end_time are required for custom_hours exception"
            )
        if new_end <= new_start:
            raise HTTPException(
                status_code=400,
                detail="end_time must be after start_time"
            )
    
    update_dict = exception_in.model_dump(exclude_unset=True)
    exception.sqlmodel_update(update_dict)
    session.add(exception)
    session.commit()
    session.refresh(exception)
    
    return DoctorAvailabilityExceptionPublic.model_validate(exception)


@router.delete("/exceptions/{exception_id}")
def delete_availability_exception(
    session: SessionDep,
    current_user: CurrentUser,
    exception_id: uuid.UUID
) -> Message:
    """
    Delete (soft delete) an availability exception.
    This will restore normal weekly schedule for that date.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete their exceptions")
    
    exception = session.get(DoctorAvailabilityException, exception_id)
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    if exception.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this exception")
    
    # Soft delete
    exception.is_active = False
    session.add(exception)
    session.commit()
    
    return Message(message="Exception deleted successfully")


# ========== PATIENT-RELATED AVAILABILITY CHECKS ==========

@router.get("/check/{day_name}", response_model=AvailableSlotCheck)
def check_available_slots_for_day(
    session: SessionDep,
    day_name: str,
    doctor_id: Optional[uuid.UUID] = Query(None)
) -> Any:
    """
    Check available time slots for a specific day.
    
    Patients can use this to see what slots are available to book with a doctor.
    If doctor_id is not provided, uses current authenticated doctor.
    """
    # Convert day name to string for validation
    day_name_lower = day_name.lower()
    valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if day_name_lower not in valid_days:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid day. Must be one of: {', '.join(valid_days)}"
        )
    
    # Get doctor's availability for this day
    doctor_slots = session.exec(
        select(DoctorAvailability).where(
            and_(
                DoctorAvailability.doctor_id == doctor_id if doctor_id else True,
                DoctorAvailability.day_of_week == day_name_lower,
                DoctorAvailability.is_available == True
            )
        ).order_by(DoctorAvailability.start_time)
    ).all()
    
    if not doctor_slots:
        raise HTTPException(
            status_code=404,
            detail=f"No available slots for {day_name}"
        )
    
    # Calculate available slots considering existing appointments
    available_slots = []
    booked_count = 0
    
    for slot in doctor_slots:
        # Get next occurrence of this day
        today = date.today()
        day_order = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
        days_ahead = (day_order[day_of_week.value] - today.weekday()) % 7
        slot_date = today + timedelta(days=days_ahead)
        
        # Get appointments for this slot
        appointments = session.exec(
            select(Appointment).where(
                and_(
                    Appointment.doctor_id == slot.doctor_id,
                    Appointment.appointment_date == slot_date,
                    Appointment.status.in_([
                        "scheduled",
                        "confirmed"
                    ])
                )
            )
        ).all()
        
        booked_count += len(appointments)
        
        # Calculate 30-minute sub-slots within this availability window
        current_time = datetime.combine(slot_date, slot.start_time)
        end_time = datetime.combine(slot_date, slot.end_time)
        
        while current_time + timedelta(minutes=30) <= end_time:
            slot_start = current_time.time()
            slot_end = (current_time + timedelta(minutes=30)).time()
            
            # Check if this 30-min slot is booked
            is_booked = False
            for appt in appointments:
                appt_end_time = (
                    datetime.combine(date.today(), appt.appointment_time) +
                    timedelta(minutes=appt.duration_minutes)
                ).time()
                
                if (slot_start < appt_end_time and slot_end > appt.appointment_time):
                    is_booked = True
                    break
            
            if not is_booked:
                available_slots.append({
                    "start": slot_start.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M"),
                    "duration_minutes": 30
                })
            
            current_time += timedelta(minutes=30)
    
    return AvailableSlotCheck(
        day_of_week=day_of_week,
        available_slots=available_slots,
        total_slots=len(available_slots),
        booked_count=booked_count
    )


@router.get("/calendar")
def get_availability_calendar(
    session: SessionDep,
    current_user: CurrentUser,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)")
) -> Any:
    """
    Get a calendar view of doctor availability for a date range.
    Shows regular schedule + exceptions.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can view their calendar")
    
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date"
        )
    
    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=400,
            detail="Date range cannot exceed 365 days"
        )
    
    from utils.availability_service import get_availability_calendar
    
    calendar = get_availability_calendar(session, current_user.id, start_date, end_date)
    
    return {"calendar": calendar}


@router.get("/{slot_id}", response_model=DoctorAvailabilityPublic)
def get_doctor_availability_slot(
    session: SessionDep,
    current_user: CurrentUser,
    slot_id: uuid.UUID = Path(..., description="Availability slot UUID")
) -> Any:
    """
    Get a specific availability slot by ID.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can view their availability")
    
    slot = session.get(DoctorAvailability, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Availability slot not found")
    
    if slot.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this slot")
    
    return slot


@router.get("/", response_model=DoctorAvailabilitiesPublic)
def get_doctor_availability(
    session: SessionDep,
    current_user: CurrentUser,
    day: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> Any:
    """
    Get all availability slots for the current doctor.
    
    Optionally filter by day of week.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can view their availability")
    
    statement = (
        select(DoctorAvailability)
        .where(DoctorAvailability.doctor_id == current_user.id)
        .order_by(DoctorAvailability.day_of_week, DoctorAvailability.start_time)
        .offset(skip)
        .limit(limit)
    )
    
    count_statement = (
        select(func.count())
        .select_from(DoctorAvailability)
        .where(DoctorAvailability.doctor_id == current_user.id)
    )
    
    if day:
        statement = statement.where(DoctorAvailability.day_of_week == day)
        count_statement = count_statement.where(DoctorAvailability.day_of_week == day)
    
    slots = session.exec(statement).all()
    count = session.exec(count_statement).one()
    
    return DoctorAvailabilitiesPublic(data=slots, count=count)


# ========== UPDATE OPERATIONS ==========

@router.put("/{slot_id}", response_model=DoctorAvailabilityPublic)
def update_doctor_availability(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    slot_id: uuid.UUID,
    availability_in: DoctorAvailabilityUpdate
) -> Any:
    """
    Update an availability slot.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update their availability")
    
    slot = session.get(DoctorAvailability, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Availability slot not found")
    
    if slot.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this slot")
    
    # If updating time, validate and check for overlaps
    if availability_in.start_time or availability_in.end_time:
        new_start = availability_in.start_time or slot.start_time
        new_end = availability_in.end_time or slot.end_time
        
        if new_start >= new_end:
            raise HTTPException(
                status_code=400,
                detail="Start time must be before end time"
            )
        
        # Check for overlapping slots
        check_day = availability_in.day_of_week or slot.day_of_week
        existing_slots = session.exec(
            select(DoctorAvailability).where(
                and_(
                    DoctorAvailability.doctor_id == current_user.id,
                    DoctorAvailability.day_of_week == check_day,
                    DoctorAvailability.id != slot_id
                )
            )
        ).all()
        
        for existing_slot in existing_slots:
            # Convert to naive time if needed for comparison
            start = new_start.replace(tzinfo=None) if hasattr(new_start, 'tzinfo') and new_start.tzinfo else new_start
            end = new_end.replace(tzinfo=None) if hasattr(new_end, 'tzinfo') and new_end.tzinfo else new_end
            
            if (start < existing_slot.end_time and 
                end > existing_slot.start_time):
                raise HTTPException(
                    status_code=409,
                    detail=f"Updated time slot overlaps with existing slot: {existing_slot.start_time.strftime('%H:%M')} - {existing_slot.end_time.strftime('%H:%M')}"
                )
    
    update_dict = availability_in.model_dump(exclude_unset=True)
    slot.sqlmodel_update(update_dict)
    session.add(slot)
    session.commit()
    session.refresh(slot)
    
    return slot


@router.patch("/{slot_id}/toggle", response_model=DoctorAvailabilityPublic)
def toggle_availability_status(
    session: SessionDep,
    current_user: CurrentUser,
    slot_id: uuid.UUID
) -> Any:
    """
    Toggle the availability status of a slot (enable/disable).
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update their availability")
    
    slot = session.get(DoctorAvailability, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Availability slot not found")
    
    if slot.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this slot")
    
    slot.is_available = not slot.is_available
    session.add(slot)
    session.commit()
    session.refresh(slot)
    
    return slot


# ========== DELETE OPERATIONS ==========

@router.delete("/{slot_id}")
def delete_doctor_availability(
    session: SessionDep,
    current_user: CurrentUser,
    slot_id: uuid.UUID
) -> Message:
    """
    Delete an availability slot.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete their availability")
    
    slot = session.get(DoctorAvailability, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Availability slot not found")
    
    if slot.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this slot")
    
    session.delete(slot)
    session.commit()
    
    return Message(message="Availability slot deleted successfully")


@router.delete("/")
def delete_all_doctor_availability(
    session: SessionDep,
    current_user: CurrentUser,
    day: Optional[str] = Query(None)
) -> Message:
    """
    Delete all availability slots for the doctor.
    
    Optionally filter by specific day of week.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete their availability")
    
    query = select(DoctorAvailability).where(
        DoctorAvailability.doctor_id == current_user.id
    )
    
    if day:
        query = query.where(DoctorAvailability.day_of_week == day)
    
    slots = session.exec(query).all()
    
    for slot in slots:
        session.delete(slot)
    
    session.commit()
    
    count = len(slots)
    return Message(message=f"Deleted {count} availability slot(s) successfully")

