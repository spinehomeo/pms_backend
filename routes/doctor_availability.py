# routes/doctor_availability.py
import uuid
from typing import Any, List, Optional
from datetime import date, time, datetime, timedelta
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
    DayOfWeek,
)
from models.appointments_model import Appointment, AppointmentStatus
from models.patients_model import Patient
from models.login_model import Message

router = APIRouter(prefix="/doctor_availability", tags=["doctor_availability"])


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
        if (availability_in.start_time < slot.end_time and 
            availability_in.end_time > slot.start_time):
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
            if (availability_in.start_time < slot.end_time and 
                availability_in.end_time > slot.start_time):
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

@router.get("/", response_model=DoctorAvailabilitiesPublic)
def get_doctor_availability(
    session: SessionDep,
    current_user: CurrentUser,
    day: Optional[DayOfWeek] = Query(None),
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
                        AppointmentStatus.SCHEDULED,
                        AppointmentStatus.CONFIRMED
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
            if (new_start < existing_slot.end_time and 
                new_end > existing_slot.start_time):
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
    day: Optional[DayOfWeek] = Query(None)
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
    # Convert day name to enum
    try:
        day_of_week = DayOfWeek(day_name.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid day. Must be one of: {', '.join([d.value for d in DayOfWeek])}"
        )
    
    # Get doctor's availability for this day
    doctor_slots = session.exec(
        select(DoctorAvailability).where(
            and_(
                DoctorAvailability.doctor_id == doctor_id if doctor_id else True,
                DoctorAvailability.day_of_week == day_of_week,
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
                        AppointmentStatus.SCHEDULED,
                        AppointmentStatus.CONFIRMED
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
