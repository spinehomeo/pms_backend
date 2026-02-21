# api/routes/appointments.py
import uuid
from typing import Any, List, Optional
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Path
from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select, and_, or_, text

from api.deps import CurrentUser, SessionDep, CurrentPatient
from models.appointments_model import (
    Appointment, AppointmentCreate, AppointmentUpdate, AppointmentPublic, 
    AppointmentsPublic
)
from models.doctor_availability_model import DoctorAvailability, DayOfWeek
from models.patients_model import Patient
from models.login_model import Message
from utils.availability_service import is_doctor_available
from utils.enum_service import EnumService

router = APIRouter(prefix="/appointments", tags=["📅 Appointments"])


def _get_day_of_week_name(date_obj: date) -> str:
    """Convert date to day of week name for availability lookup"""
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return day_names[date_obj.weekday()]


def _validate_availability(
    session: SessionDep,
    doctor_id: uuid.UUID,
    appointment_date: date,
    appointment_time: time,
    duration_minutes: int,
    exclude_appointment_id: Optional[uuid.UUID] = None
) -> bool:
    """
    Validate if appointment time falls within doctor's availability slots.
    Checks for exceptions first, then falls back to regular availability.
    Returns True if valid, raises HTTPException if not.
    """
    # Use the new availability service that checks for exceptions
    if not is_doctor_available(session, doctor_id, appointment_date, appointment_time):
        # Get doctor's regular availability for this day to show available times
        day_name = _get_day_of_week_name(appointment_date)
        
        availability_slots = session.exec(
            select(DoctorAvailability).where(
                and_(
                    DoctorAvailability.doctor_id == doctor_id,
                    DoctorAvailability.day_of_week == day_name,
                    DoctorAvailability.is_available == True
                )
            )
        ).all()
        
        if availability_slots:
            available_times = [
                f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}"
                for slot in availability_slots
            ]
            raise HTTPException(
                status_code=409,
                detail=f"Appointment time not within doctor's availability. Available: {', '.join(available_times)}"
            )
        else:
            raise HTTPException(
                status_code=409,
                detail=f"Doctor is not available on {day_name}s or has marked this date as unavailable"
            )
    
    return True


@router.post("/validate-availability")
def validate_appointment_availability(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_date: date = Query(...),
    appointment_time: time = Query(...),
    duration_minutes: int = Query(30, ge=15)
) -> Any:
    """
    Check if a specific time slot is available for the doctor.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can check availability")
    
    try:
        _validate_availability(
            session, current_user.id, appointment_date, 
            appointment_time, duration_minutes
        )
        return {"available": True, "message": "Time slot is available"}
    except HTTPException as e:
        return {"available": False, "message": e.detail}

@router.get("/", response_model=AppointmentsPublic)
def read_appointments(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    date_filter: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    patient_id: Optional[uuid.UUID] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
) -> Any:
    """
    Retrieve appointments with filtering options.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access appointments")
    
    # Base query
    count_statement = (
        select(func.count())
        .select_from(Appointment)
        .where(Appointment.doctor_id == current_user.id)
    )
    
    statement = (
        select(Appointment)
        .where(Appointment.doctor_id == current_user.id)
        .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
        .offset(skip)
        .limit(limit)
    )
    
    # Apply filters
    if date_filter:
        count_statement = count_statement.where(
            Appointment.appointment_date == date_filter
        )
        statement = statement.where(
            Appointment.appointment_date == date_filter
        )
    else:
        if from_date:
            count_statement = count_statement.where(
                Appointment.appointment_date >= from_date
            )
            statement = statement.where(
                Appointment.appointment_date >= from_date
            )
        
        if to_date:
            count_statement = count_statement.where(
                Appointment.appointment_date <= to_date
            )
            statement = statement.where(
                Appointment.appointment_date <= to_date
            )
    
    if status:
        # Validate status against dynamic enum
        if not EnumService.validate_value(session, "AppointmentStatus", status, current_user.id):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status '{status}'. Use /enums/doctor/AppointmentStatus to get valid options."
            )
        count_statement = count_statement.where(Appointment.status == status)
        statement = statement.where(Appointment.status == status)
    
    if patient_id:
        # Verify patient belongs to doctor
        patient = session.get(Patient, patient_id)
        if not patient or patient.doctor_id != current_user.id:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        count_statement = count_statement.where(Appointment.patient_id == patient_id)
        statement = statement.where(Appointment.patient_id == patient_id)
    
    count = session.exec(count_statement).one()
    appointments = session.exec(statement).all()
    
    # Populate patient details
    response_appointments = []
    for appt in appointments:
        appt_response = AppointmentPublic.model_validate(appt)
        appt_response.patient_name = appt.patient.full_name if appt.patient else None
        appt_response.patient_phone = appt.patient.phone if appt.patient else None
        response_appointments.append(appt_response)
    
    return AppointmentsPublic(data=response_appointments, count=count)


@router.get("/today", response_model=AppointmentsPublic)
def read_today_appointments(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get today's appointments.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access appointments")
    
    today = date.today()
    
    statement = (
        select(Appointment)
        .where(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.appointment_date == today
            )
        )
        .order_by(Appointment.appointment_time.asc())
    )
    
    appointments = session.exec(statement).all()
    
    # Populate patient details
    response_appointments = []
    for appt in appointments:
        appt_response = AppointmentPublic.model_validate(appt)
        appt_response.patient_name = appt.patient.full_name if appt.patient else None
        appt_response.patient_phone = appt.patient.phone if appt.patient else None
        response_appointments.append(appt_response)
    
    return AppointmentsPublic(data=response_appointments, count=len(response_appointments))


@router.get("/upcoming")
def read_upcoming_appointments(
    session: SessionDep,
    current_user: CurrentUser,
    days: int = Query(7, ge=1, le=365)
) -> Any:
    """
    Get upcoming appointments.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access appointments")
    
    today = date.today()
    future_date = today.replace(day=today.day + days)
    
    # Get active appointment statuses for this doctor
    active_statuses = EnumService.get_doctor_options(session, "AppointmentStatus", current_user.id)
    status_values = [opt.value for opt in active_statuses if opt.value in ["scheduled", "confirmed"]]
    
    if not status_values:
        # If no statuses match, return empty result
        return {
            "appointments": [],
            "grouped_by_date": {},
            "from_date": today.isoformat(),
            "to_date": future_date.isoformat()
        }
    
    statement = (
        select(Appointment)
        .where(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.appointment_date >= today,
                Appointment.appointment_date <= future_date,
                Appointment.status.in_(status_values)
            )
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc())
    )
    
    appointments = session.exec(statement).all()
    
    # Populate patient details
    response_appointments = []
    for appt in appointments:
        appt_dict = {
            **appt.__dict__,
            "patient_name": appt.patient.full_name if appt.patient else None,
            "patient_phone": appt.patient.phone if appt.patient else None
        }
        response_appointments.append(AppointmentPublic(**appt_dict))
    
    # Group by date
    appointments_by_date = {}
    for appointment in response_appointments:
        date_str = appointment.appointment_date.isoformat()
        if date_str not in appointments_by_date:
            appointments_by_date[date_str] = []
        appointments_by_date[date_str].append(appointment)
    
    return {
        "appointments": response_appointments,
        "grouped_by_date": appointments_by_date,
        "from_date": today.isoformat(),
        "to_date": future_date.isoformat()
    }


@router.get("/{appointment_id}", response_model=AppointmentPublic)
def read_appointment(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: uuid.UUID = Path(..., description="Appointment UUID")
) -> Any:
    """
    Get appointment by ID.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access appointments")
    
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this appointment")
    
    appt_response = AppointmentPublic.model_validate(appointment)
    appt_response.patient_name = appointment.patient.full_name if appointment.patient else None
    appt_response.patient_phone = appointment.patient.phone if appointment.patient else None
    return appt_response


@router.post("/", response_model=AppointmentPublic)
def create_appointment(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    appointment_in: AppointmentCreate
) -> Any:
    """
    Create new appointment.
    Validates against doctor's availability slots and booking conflicts.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create appointments")
    
    # Verify patient belongs to doctor
    patient = session.get(Patient, appointment_in.patient_id)
    if not patient or patient.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Validate appointment status if provided
    if hasattr(appointment_in, 'status') and appointment_in.status:
        if not EnumService.validate_value(session, "AppointmentStatus", appointment_in.status, current_user.id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{appointment_in.status}'. Use /enums/doctor/AppointmentStatus to get valid options."
            )
    
    # Validate consultation type if provided
    if hasattr(appointment_in, 'consultation_type') and appointment_in.consultation_type:
        if not EnumService.validate_value(session, "ConsultationType", appointment_in.consultation_type, current_user.id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid consultation type '{appointment_in.consultation_type}'. Use /enums/doctor/ConsultationType to get valid options."
            )
    
    # Validate appointment time is within doctor's availability
    _validate_availability(
        session,
        current_user.id,
        appointment_in.appointment_date,
        appointment_in.appointment_time,
        appointment_in.duration_minutes
    )
    
    # Check for scheduling conflicts
    # Strip timezone info to match TIME WITHOUT TIME ZONE column
    appointment_time = (
        appointment_in.appointment_time.replace(tzinfo=None) 
        if appointment_in.appointment_time.tzinfo else 
        appointment_in.appointment_time
    )
    appointment_end_time = (
        datetime.combine(date.today(), appointment_time) + 
        timedelta(minutes=appointment_in.duration_minutes)
    ).time()
    
    # Get available status values for conflict check
    active_statuses = EnumService.get_doctor_options(session, "AppointmentStatus", current_user.id)
    conflict_check_statuses = [opt.value for opt in active_statuses if opt.value in ["scheduled", "confirmed"]]
    
    conflicting_appointments = session.exec(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.appointment_date == appointment_in.appointment_date,
                Appointment.status.in_(conflict_check_statuses) if conflict_check_statuses else Appointment.status.in_(["scheduled", "confirmed"]),
                or_(
                    # New appointment starts during existing appointment
                    and_(
                        appointment_time >= Appointment.appointment_time,
                        appointment_time < (
                            Appointment.appointment_time +
                            (Appointment.duration_minutes * text("INTERVAL '1 minute'"))
                        )
                    ),
                    # Existing appointment starts during new appointment
                    and_(
                        Appointment.appointment_time >= appointment_time,
                        Appointment.appointment_time < appointment_end_time
                    )
                )
            )
        )
    ).all()
    
    if conflicting_appointments:
        conflict_details = [
            f"{a.appointment_time.strftime('%H:%M')} - {a.patient.full_name}"
            for a in conflicting_appointments
        ]
        raise HTTPException(
            status_code=409,
            detail=f"Appointment conflicts with existing appointments: {', '.join(conflict_details)}"
        )
    
    appointment = Appointment.model_validate(
        appointment_in,
        update={"doctor_id": current_user.id}
    )
    try:
        session.add(appointment)
        session.commit()
        session.refresh(appointment)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="This time slot is no longer available. Another appointment may have been created just now."
        )
    
    # Update patient's last visit date
    patient.last_visit_date = appointment.appointment_date
    session.add(patient)
    session.commit()
    
    appt_response = AppointmentPublic.model_validate(appointment)
    appt_response.patient_name = appointment.patient.full_name if appointment.patient else None
    appt_response.patient_phone = appointment.patient.phone if appointment.patient else None
    return appt_response


@router.put("/{appointment_id}", response_model=AppointmentPublic)
def update_appointment(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: uuid.UUID,
    appointment_in: AppointmentUpdate
) -> Any:
    """
    Update an appointment.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update appointments")
    
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this appointment")
    
    # Validate status if being updated
    if appointment_in.status:
        if not EnumService.validate_value(session, "AppointmentStatus", appointment_in.status, current_user.id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{appointment_in.status}'. Use /enums/doctor/AppointmentStatus to get valid options."
            )
    
    # Validate consultation type if being updated
    if appointment_in.consultation_type:
        if not EnumService.validate_value(session, "ConsultationType", appointment_in.consultation_type, current_user.id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid consultation type '{appointment_in.consultation_type}'. Use /enums/doctor/ConsultationType to get valid options."
            )
    
    # Check for scheduling conflicts if time or date is being changed
    if (appointment_in.appointment_date or appointment_in.appointment_time or 
        appointment_in.duration_minutes):
        
        check_date = appointment_in.appointment_date or appointment.appointment_date
        check_time_raw = appointment_in.appointment_time or appointment.appointment_time
        # Strip timezone info to match TIME WITHOUT TIME ZONE column
        check_time = (
            check_time_raw.replace(tzinfo=None) 
            if hasattr(check_time_raw, 'tzinfo') and check_time_raw.tzinfo else 
            check_time_raw
        )
        check_duration = appointment_in.duration_minutes or appointment.duration_minutes
        
        check_end_time = (
            datetime.combine(date.today(), check_time) + 
            timedelta(minutes=check_duration)
        ).time()
        
        # Get available status values for conflict check
        active_statuses = EnumService.get_doctor_options(session, "AppointmentStatus", current_user.id)
        conflict_check_statuses = [opt.value for opt in active_statuses if opt.value in ["scheduled", "confirmed"]]
        
        conflicting_appointments = session.exec(
            select(Appointment).where(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.appointment_date == check_date,
                    Appointment.id != appointment_id,
                    Appointment.status.in_(conflict_check_statuses) if conflict_check_statuses else Appointment.status.in_(["scheduled", "confirmed"]),
                    or_(
                        and_(
                            check_time >= Appointment.appointment_time,
                            check_time < (
                                Appointment.appointment_time +
                                (Appointment.duration_minutes * text("INTERVAL '1 minute'"))
                            )
                        ),
                        and_(
                            Appointment.appointment_time >= check_time,
                            Appointment.appointment_time < check_end_time
                        )
                    )
                )
            )
        ).all()
        
        if conflicting_appointments:
            conflict_details = [
                f"{a.appointment_time.strftime('%H:%M')} - {a.patient.full_name}"
                for a in conflicting_appointments
            ]
            raise HTTPException(
                status_code=409,
                detail=f"Updated appointment conflicts with existing appointments: "
                      f"{', '.join(conflict_details)}"
            )
    
    update_dict = appointment_in.model_dump(exclude_unset=True)
    appointment.sqlmodel_update(update_dict)
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    
    appt_response = AppointmentPublic.model_validate(appointment)
    appt_response.patient_name = appointment.patient.full_name if appointment.patient else None
    appt_response.patient_phone = appointment.patient.phone if appointment.patient else None
    return appt_response


@router.patch("/{appointment_id}/status")
def update_appointment_status(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: uuid.UUID,
    status: str
) -> AppointmentPublic:
    """
    Update appointment status.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update appointment status")
    
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this appointment")
    
    appointment.status = status
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    
    appt_response = AppointmentPublic.model_validate(appointment)
    appt_response.patient_name = appointment.patient.full_name if appointment.patient else None
    appt_response.patient_phone = appointment.patient.phone if appointment.patient else None
    return appt_response


@router.delete("/{appointment_id}")
def delete_appointment(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: uuid.UUID
) -> Message:
    """
    Delete an appointment.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete appointments")
    
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this appointment")
    
    session.delete(appointment)
    session.commit()
    return Message(message="Appointment deleted successfully")


@router.get("/availability/{check_date}")
def check_availability(
    session: SessionDep,
    current_user: CurrentUser,
    check_date: date
) -> Any:
    """
    Check available time slots for a specific date based on doctor's availability.
    Shows 30-minute intervals within booked appointments.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can check availability")
    
    # Get day of week for this date
    day_name = _get_day_of_week_name(check_date)
    
    # Get doctor's availability slots for this day
    availability_slots = session.exec(
        select(DoctorAvailability).where(
            and_(
                DoctorAvailability.doctor_id == current_user.id,
                DoctorAvailability.day_of_week == day_name,
                DoctorAvailability.is_available == True
            )
        ).order_by(DoctorAvailability.start_time)
    ).all()
    
    if not availability_slots:
        return {
            "date": check_date.isoformat(),
            "day_of_week": day_name,
            "available_slots": [],
            "total_available": 0,
            "message": "Doctor has no availability on this day"
        }
    
    # Get appointments for the day
    appointments = session.exec(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.appointment_date == check_date,
                Appointment.status.in_([
                    "scheduled",
                    "confirmed"
                ])
            )
        ).order_by(Appointment.appointment_time.asc())
    ).all()
    
    # Calculate booked slots
    booked_slots = []
    for appointment in appointments:
        start_time = appointment.appointment_time
        end_time = (
            datetime.combine(date.today(), start_time) + 
            timedelta(minutes=appointment.duration_minutes)
        ).time()
        booked_slots.append({
            "start": start_time,
            "end": end_time,
            "patient": appointment.patient.full_name,
            "status": appointment.status
        })
    
    # Calculate available slots (30-minute intervals)
    available_slots = []
    for slot in availability_slots:
        current_time = datetime.combine(check_date, slot.start_time)
        end_time = datetime.combine(check_date, slot.end_time)
        
        while current_time + timedelta(minutes=30) <= end_time:
            slot_start = current_time.time()
            slot_end = (current_time + timedelta(minutes=30)).time()
            
            # Check if slot is available
            slot_available = True
            for booked in booked_slots:
                if (slot_start < booked["end"] and slot_end > booked["start"]):
                    slot_available = False
                    break
            
            if slot_available:
                available_slots.append({
                    "start": slot_start.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M"),
                    "duration_minutes": 30
                })
            
            current_time += timedelta(minutes=30)
    
    return {
        "date": check_date.isoformat(),
        "day_of_week": day_name,
        "availability_slots": [
            {
                "start": slot.start_time.strftime("%H:%M"),
                "end": slot.end_time.strftime("%H:%M"),
                "is_available": slot.is_available,
                "notes": slot.notes
            }
            for slot in availability_slots
        ],
        "booked_slots": booked_slots,
        "available_slots": available_slots,
        "total_available": len(available_slots)
    }


@router.post("/patient/book", response_model=AppointmentPublic)
def book_appointment_patient(
    *,
    session: SessionDep,
    patient: CurrentPatient,
    doctor_id: uuid.UUID = Query(..., description="Doctor UUID"),
    appointment_date: date = Query(...),
    appointment_time: time = Query(...),
    reason: Optional[str] = Query(None)
) -> Any:
    """
    PROTECTED - Patient books appointment with authenticated patient token
    
    **Authentication Required:** Patient must be logged in with valid token
    
    **Flow:**
    1. Patient calls /login/patient-simple to get token with entity='patient'
    2. Patient uses token to authenticate this request
    3. Appointment is created for authenticated patient
    4. Doctor receives verified appointment
    
    **Benefits:**
    - ✅ Patient identity verified via Patient table
    - ✅ Phone number verified during registration
    - ✅ Prevents spam/fake appointments
    - ✅ Better tracking and communication
    
    **Required fields:** doctor_id, appointment_date, appointment_time
    **Optional fields:** reason
    """
    # Verify patient is active
    if not patient.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your patient account is inactive"
        )
    
    # Verify doctor exists and is active
    from models.users_model import User
    doctor = session.get(User, doctor_id)
    if not doctor or doctor.role != "doctor" or not doctor.is_active:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Verify patient belongs to this doctor
    if patient.doctor_id != doctor_id:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this doctor. Please contact support."
        )
    
    # Validate appointment time is within doctor's availability
    _validate_availability(
        session,
        doctor_id,
        appointment_date,
        appointment_time,
        30  # 30 minutes default
    )
    
    # Check for scheduling conflicts
    appointment_time_clean = (
        appointment_time.replace(tzinfo=None) 
        if appointment_time.tzinfo else 
        appointment_time
    )
    appointment_end_time = (
        datetime.combine(date.today(), appointment_time_clean) + 
        timedelta(minutes=30)
    ).time()
    
    conflicting_appointments = session.exec(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == appointment_date,
                Appointment.status.in_([
                    "scheduled",
                    "confirmed"
                ]),
                or_(
                    and_(
                        appointment_time_clean >= Appointment.appointment_time,
                        appointment_time_clean < (
                            Appointment.appointment_time +
                            (Appointment.duration_minutes * text("INTERVAL '1 minute'"))
                        )
                    ),
                    and_(
                        Appointment.appointment_time >= appointment_time_clean,
                        Appointment.appointment_time < appointment_end_time
                    )
                )
            )
        )
    ).all()
    
    if conflicting_appointments:
        raise HTTPException(
            status_code=409,
            detail="This time slot is no longer available. Please choose another time."
        )
    
    # Create appointment
    appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=patient.id,
        appointment_date=appointment_date,
        appointment_time=appointment_time_clean,
        duration_minutes=30,
        status="scheduled",
        consultation_type="follow_up",
        reason=reason,
    )
    
    try:
        session.add(appointment)
        session.commit()
        session.refresh(appointment)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="This time slot is no longer available. Please choose another time."
        )
    
    # Update patient's last visit date
    patient.last_visit_date = appointment_date
    session.add(patient)
    session.commit()
    
    # Return appointment with patient details using model_validate
    appointment_response = AppointmentPublic.model_validate(appointment)
    appointment_response.patient_name = patient.full_name
    appointment_response.patient_phone = patient.phone
    return appointment_response