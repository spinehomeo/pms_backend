# api/routes/appointments.py
import uuid
from typing import Any, List, Optional
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Path
from sqlmodel import func, select, and_, or_, text

from api.deps import CurrentUser, SessionDep
from models.appointments_model import (
    Appointment, AppointmentCreate, AppointmentUpdate, AppointmentPublic, 
    AppointmentsPublic, AppointmentStatus
)
from models.patients_model import Patient
from models.login_model import Message

router = APIRouter(prefix="/appointments", tags=["appointments"])

# Default doctor working hours (can be moved to settings or Doctor model later)
DOCTOR_DEFAULT_WORKING_HOURS = {
    "start": time(9, 0),
    "end": time(17, 0),
}

@router.get("/", response_model=AppointmentsPublic)
def read_appointments(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    date_filter: Optional[date] = Query(None),
    status: Optional[AppointmentStatus] = Query(None),
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
        .order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc())
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
    
    return AppointmentsPublic(data=appointments, count=count)


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
    
    return AppointmentsPublic(data=appointments, count=len(appointments))


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
    
    statement = (
        select(Appointment)
        .where(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.appointment_date >= today,
                Appointment.appointment_date <= future_date,
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED
                ])
            )
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc())
    )
    
    appointments = session.exec(statement).all()
    
    # Group by date
    appointments_by_date = {}
    for appointment in appointments:
        date_str = appointment.appointment_date.isoformat()
        if date_str not in appointments_by_date:
            appointments_by_date[date_str] = []
        appointments_by_date[date_str].append(appointment)
    
    return {
        "appointments": appointments,
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
    
    return appointment


@router.post("/", response_model=AppointmentPublic)
def create_appointment(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    appointment_in: AppointmentCreate
) -> Any:
    """
    Create new appointment.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create appointments")
    
    # Verify patient belongs to doctor
    patient = session.get(Patient, appointment_in.patient_id)
    if not patient or patient.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Patient not found")
    
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
    
    conflicting_appointments = session.exec(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.appointment_date == appointment_in.appointment_date,
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED
                ]),
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
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    
    # Update patient's last visit date
    patient.last_visit_date = appointment.appointment_date
    session.add(patient)
    session.commit()
    
    return appointment


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
        
        conflicting_appointments = session.exec(
            select(Appointment).where(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.appointment_date == check_date,
                    Appointment.id != appointment_id,
                    Appointment.status.in_([
                        AppointmentStatus.SCHEDULED,
                        AppointmentStatus.CONFIRMED
                    ]),
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
    return appointment


@router.patch("/{appointment_id}/status")
def update_appointment_status(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: uuid.UUID,
    status: AppointmentStatus
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
    return appointment


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
    Check available time slots for a specific date.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can check availability")
    
    # Get appointments for the day
    appointments = session.exec(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.appointment_date == check_date,
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED
                ])
            )
        ).order_by(Appointment.appointment_time.asc())
    ).all()
    
    # Define working hours (use default constant; can be overridden per-doctor later)
    working_hours = [
        DOCTOR_DEFAULT_WORKING_HOURS["start"],
        DOCTOR_DEFAULT_WORKING_HOURS["end"]
    ]
    
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
    current_time = datetime.combine(check_date, working_hours[0])
    end_time = datetime.combine(check_date, working_hours[1])
    
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
        "working_hours": {
            "start": working_hours[0].strftime("%H:%M"),
            "end": working_hours[1].strftime("%H:%M")
        },
        "booked_slots": booked_slots,
        "available_slots": available_slots,
        "total_available": len(available_slots)
    }