"""
Public API Routes - endpoints accessible without authentication
"""
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import select, and_

from api.deps import SessionDep
from models.users_model import User
from models.doctor_availability_model import DoctorAvailability
from models.doctor_availability_exception_model import DoctorAvailabilityException
from models.patients_model import Patient
from models.appointments_model import Appointment
from models.public_models import (
    AvailabilityResponse,
    AvailableSlot,
    DoctorPublicInfo,
    AppointmentBookingResponse,
    PublicBookingRequest,
)
from utils.availability_service import get_available_slots_for_day

router = APIRouter(prefix="/public", tags=["🌍 Public"])


@router.get("/doctors", response_model=list[DoctorPublicInfo])
def list_doctors_public(
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> Any:
    """
    List all active doctors (public endpoint).
    
    Returns minimal doctor information including name, specialization, clinic, and fees.
    """
    statement = (
        select(User)
        .where((User.role == "doctor") & (User.is_active == True))
        .offset(skip)
        .limit(limit)
    )
    doctors = session.exec(statement).all()
    
    return [
        DoctorPublicInfo(
            id=str(doctor.id),
            full_name=doctor.full_name,
            specialization=doctor.specialization,
            clinic_name=doctor.clinic_name,
            consultation_fee=doctor.consultation_fee,
        )
        for doctor in doctors
    ]


@router.get("/doctors/{doctor_id}")
def get_doctor_public(
    session: SessionDep,
    doctor_id: str,
) -> Any:
    """
    Get public information about a specific doctor.
    """
    try:
        doctor_uuid = uuid.UUID(doctor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid doctor ID format")
    
    doctor = session.get(User, doctor_uuid)
    if not doctor or doctor.role != "doctor" or not doctor.is_active:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    return DoctorPublicInfo(
        id=str(doctor.id),
        full_name=doctor.full_name,
        specialization=doctor.specialization,
        clinic_name=doctor.clinic_name,
        consultation_fee=doctor.consultation_fee,
    )


@router.get("/availability/{doctor_id}/{check_date}", response_model=AvailabilityResponse)
def check_availability_public(
    session: SessionDep,
    doctor_id: str,
    check_date: date,
) -> Any:
    """
    Check doctor availability for a specific date (public endpoint).
    
    Returns available 30-minute slots for the selected date.
    """
    try:
        doctor_uuid = uuid.UUID(doctor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid doctor ID format")
    
    # Verify doctor exists and is active
    doctor = session.get(User, doctor_uuid)
    if not doctor or doctor.role != "doctor" or not doctor.is_active:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Explicitly check for date-specific exceptions first (safeguard for deployments)
    exception = session.exec(
        select(DoctorAvailabilityException).where(
            and_(
                DoctorAvailabilityException.doctor_id == doctor_uuid,
                DoctorAvailabilityException.exception_date == check_date,
                DoctorAvailabilityException.is_active == True
            )
        )
    ).first()

    if exception and exception.exception_type in ["unavailable", "holiday"]:
        # Doctor explicitly unavailable whole day
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_name = day_names[check_date.weekday()]
        return AvailabilityResponse(
            date=check_date.isoformat(),
            day_of_week=day_name,
            available_slots=[],
            message="Doctor is unavailable on this date",
        )

    # Build available 30-minute slots while respecting exceptions
    slots = get_available_slots_for_day(session, doctor_uuid, check_date, slot_duration=30)

    # Get appointments for the day to identify booked slots
    appointments = session.exec(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == doctor_uuid,
                Appointment.appointment_date == check_date,
                Appointment.status.in_(["scheduled", "confirmed"])
            )
        )
    ).all()

    # Create set of booked time strings for quick lookup
    booked_times = set()
    for appointment in appointments:
        booked_times.add(appointment.appointment_time.strftime("%H:%M"))

    # Convert slots returned by service into API response slots
    available_slots = []
    for s in slots:
        start_time = s.get('start_time')
        end_time = s.get('end_time')
        if not start_time or not end_time:
            continue
        start_str = start_time.strftime("%H:%M")
        end_str = end_time.strftime("%H:%M")
        is_booked = start_str in booked_times
        available_slots.append(
            AvailableSlot(
                start=start_str,
                end=end_str,
                duration_minutes=30,
                booked=is_booked
            )
        )

    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_name = day_names[check_date.weekday()]
    if not available_slots:
        return AvailabilityResponse(
            date=check_date.isoformat(),
            day_of_week=day_name,
            available_slots=[],
            message="No available slots for this date",
        )
    
    return AvailabilityResponse(
        date=check_date.isoformat(),
        day_of_week=day_name,
        available_slots=available_slots,
        doctor=DoctorPublicInfo(
            id=str(doctor.id),
            full_name=doctor.full_name,
            specialization=doctor.specialization,
            clinic_name=doctor.clinic_name,
            consultation_fee=doctor.consultation_fee,
        ),
    )


@router.post("/appointments/book-public", response_model=AppointmentBookingResponse)
def book_appointment_public(
    session: SessionDep,
    booking_data: PublicBookingRequest,
) -> Any:
    """
    PUBLIC appointment booking - for unregistered patients ONLY
    
    ⚠️ **THIS ENDPOINT IS FOR PUBLIC USE ONLY**
    
    **Flow:**
    1. Unregistered patient provides name + phone + gender + doctor_id
    2. System auto-registers patient if not exists
    3. Creates appointment record
    4. Returns appointment confirmation
    
    **Better approach:** Use `/users/patients/quick-access` endpoint instead!
    - Provides immediate access token
    - More secure registration flow
    - Then use authenticated `/appointments/book` to book
    
    **Required fields:** doctor_id, full_name, phone, appointment_date, appointment_time
    **Optional fields:** gender, reason
    """
    # Validate and parse doctor ID
    try:
        doctor_uuid = uuid.UUID(booking_data.doctor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid doctor ID format")
    
    # Verify doctor exists and is active
    doctor = session.get(User, doctor_uuid)
    if not doctor or doctor.role != "doctor" or not doctor.is_active:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Validate appointment time against doctor's availability
    from routes.appointments import _validate_availability
    try:
        _validate_availability(
            session=session,
            doctor_id=doctor_uuid,
            appointment_date=booking_data.appointment_date,
            appointment_time=booking_data.appointment_time,
            duration_minutes=30
        )
    except HTTPException:
        raise
    
    # Check if patient with this phone already exists for this doctor
    patient = session.exec(
        select(Patient).where(
            Patient.doctor_id == doctor_uuid,
            Patient.phone == booking_data.phone,
        )
    ).first()
    
    # If patient doesn't exist, create them (auto-registration)
    if not patient:
        # Create patient record directly (no User table entry)
        from core.security import get_password_hash
        from utils.enum_service import EnumService
        import time
        
        # Use valid gender or default to "other"
        gender = booking_data.gender if booking_data.gender else "other"
        
        # Validate gender
        if not EnumService.validate_value(session, "PatientGender", gender, doctor_uuid):
            # If validation fails, use default "other"
            gender = "other"
        
        # Generate unique CNIC (max 15 chars per database constraint)
        phone_suffix = booking_data.phone[-4:] if len(booking_data.phone) >= 4 else booking_data.phone
        random_suffix = uuid.uuid4().hex[:10]
        unique_cnic = f"P{phone_suffix}{random_suffix}"
        
        patient = Patient(
            doctor_id=doctor_uuid,
            full_name=booking_data.full_name,
            phone=booking_data.phone,
            cnic=unique_cnic,
            gender=gender,
            hashed_password=get_password_hash(booking_data.phone),
        )
        session.add(patient)
        try:
            session.commit()
            session.refresh(patient)
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Error creating patient: {str(e)}")
    
    # Create appointment
    appointment = Appointment(
        doctor_id=doctor_uuid,
        patient_id=patient.id,
        appointment_date=booking_data.appointment_date,
        appointment_time=booking_data.appointment_time,
        duration_minutes=30,
        status="scheduled",
        consultation_type="first",
        reason=booking_data.reason,
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
    patient.last_visit_date = booking_data.appointment_date
    session.add(patient)
    session.commit()
    
    return AppointmentBookingResponse(
        success=True,
        appointment_id=str(appointment.id),
        message=f"Appointment booked successfully for {booking_data.appointment_date.isoformat()} at {booking_data.appointment_time.strftime('%H:%M')}",
    )
