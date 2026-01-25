# api/routes/patients.py
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import func, select

from api.deps import CurrentUser, SessionDep
from models.patients_model import (
    Patient, PatientCreate, PatientUpdate, PatientPublic, PatientsPublic,
    PatientGender,  # Add this import
)
from models.appointments_model import Appointment
from models.cases_model import PatientCase
from models.login_model import Message

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/", response_model=PatientsPublic)
def read_patients(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    payment_status: Optional[bool] = Query(None),  # NEW: Filter by payment status
    gender: Optional[PatientGender] = Query(None),  # NEW: Filter by gender
) -> Any:
    """
    Retrieve patients with optional search.
    """
    # Only doctors can access patients
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access patients")
    
    # Base query for current doctor's patients
    count_statement = (
        select(func.count())
        .select_from(Patient)
        .where(Patient.doctor_id == current_user.id)
    )
    
    statement = (
        select(Patient)
        .where(Patient.doctor_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    
    # Add search filter if provided
    if search:
        search_filter = f"%{search}%"
        count_statement = count_statement.where(
            Patient.full_name.ilike(search_filter) |
            Patient.phone.ilike(search_filter) |
            Patient.email.ilike(search_filter) |
            Patient.cnic.ilike(search_filter) |  # NEW: Search by CNIC
            Patient.city.ilike(search_filter)    # NEW: Search by city
        )
        statement = statement.where(
            Patient.full_name.ilike(search_filter) |
            Patient.phone.ilike(search_filter) |
            Patient.email.ilike(search_filter) |
            Patient.cnic.ilike(search_filter) |  # NEW: Search by CNIC
            Patient.city.ilike(search_filter)    # NEW: Search by city
        )
    
    # NEW: Filter by payment status
    if payment_status is not None:
        count_statement = count_statement.where(Patient.payment_status == payment_status)
        statement = statement.where(Patient.payment_status == payment_status)
    
    # NEW: Filter by gender
    if gender:
        count_statement = count_statement.where(Patient.gender == gender)
        statement = statement.where(Patient.gender == gender)
    
    count = session.exec(count_statement).one()
    patients = session.exec(statement).all()
    
    return PatientsPublic(data=patients, count=count)


@router.get("/{patient_id}", response_model=PatientPublic)
def read_patient(
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID
) -> Any:
    """
    Get patient by ID.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access patients")
    
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Ensure doctor can only access their own patients
    if patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this patient")
    
    return patient


@router.post("/", response_model=PatientPublic)
def create_patient(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    patient_in: PatientCreate
) -> Any:
    """
    Create new patient.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create patients")
    
    # Check if patient with same email already exists for this doctor
    if patient_in.email:
        existing_email = session.exec(
            select(Patient).where(
                Patient.doctor_id == current_user.id,
                Patient.email == patient_in.email
            )
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Patient with this email already exists"
            )
    
    # NEW: Check if patient with same CNIC already exists for this doctor
    existing_cnic = session.exec(
        select(Patient).where(
            Patient.doctor_id == current_user.id,
            Patient.cnic == patient_in.cnic
        )
    ).first()
    if existing_cnic:
        raise HTTPException(
            status_code=400,
            detail="Patient with this CNIC already exists"
        )
    
    patient = Patient.model_validate(
        patient_in,
        update={"doctor_id": current_user.id}
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.put("/{patient_id}", response_model=PatientPublic)
def update_patient(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID,
    patient_in: PatientUpdate
) -> Any:
    """
    Update a patient.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can update patients")
    
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this patient")
    
    # Check email uniqueness if being updated
    if patient_in.email and patient_in.email != patient.email:
        existing_email = session.exec(
            select(Patient).where(
                Patient.doctor_id == current_user.id,
                Patient.email == patient_in.email,
                Patient.id != patient_id
            )
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Another patient with this email already exists"
            )
    
    # NEW: Check CNIC uniqueness if being updated
    if patient_in.cnic and patient_in.cnic != patient.cnic:
        existing_cnic = session.exec(
            select(Patient).where(
                Patient.doctor_id == current_user.id,
                Patient.cnic == patient_in.cnic,
                Patient.id != patient_id
            )
        ).first()
        if existing_cnic:
            raise HTTPException(
                status_code=400,
                detail="Another patient with this CNIC already exists"
            )
    
    update_dict = patient_in.model_dump(exclude_unset=True)
    patient.sqlmodel_update(update_dict)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.delete("/{patient_id}")
def delete_patient(
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID
) -> Message:
    """
    Delete a patient.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can delete patients")
    
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this patient")
    
    # Cascade delete will handle related cases, appointments, etc.
    session.delete(patient)
    session.commit()
    return Message(message="Patient deleted successfully")


@router.get("/{patient_id}/stats")
def get_patient_stats(
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID
) -> Any:
    """
    Get statistics for a patient.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access patient stats")
    
    patient = session.get(Patient, patient_id)
    if not patient or patient.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Count cases
    cases_count = session.exec(
        select(func.count())
        .select_from(PatientCase)
        .where(PatientCase.patient_id == patient_id)
    ).one()
    
    # Count appointments
    appointments_count = session.exec(
        select(func.count())
        .select_from(Appointment)
        .where(Appointment.patient_id == patient_id)
    ).one()
    
    # Get last visit date
    last_appointment = session.exec(
        select(Appointment.appointment_date)
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.appointment_date.desc())
    ).first()
    
    return {
        "patient_id": patient_id,
        "total_cases": cases_count,
        "total_appointments": appointments_count,
        "last_visit_date": last_appointment,
        "age": patient.age,
        "payment_status": patient.payment_status,  # NEW: Include payment status in stats
        "gender": patient.gender,                  # NEW: Include gender in stats
        "city": patient.city                       # NEW: Include city in stats
    }


# ============================================================================
# PROTECTED PATIENT ENDPOINTS - For authenticated patients only
# ============================================================================

from datetime import date
from sqlalchemy.exc import IntegrityError
from sqlmodel import and_
from core.security import get_password_hash, verify_password
from models.appointments_model import AppointmentStatus, AppointmentPublic


@router.get("/me", response_model=PatientPublic)
def get_patient_profile(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get authenticated patient's profile information
    
    **Authentication Required:** Patient token from /users/patients/quick-access or /login/patient
    
    **Returns:** Complete patient profile including:
    - Personal info (name, phone, email, gender, age)
    - Doctor info (assigned doctor)
    - Medical info (allergies, medical history, medications)
    - Account status
    
    **Use case:** Patient views their profile on dashboard
    """
    # Verify this is a patient record
    if not isinstance(current_user, Patient):
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for patients only"
        )
    
    # Verify patient is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your patient account is inactive"
        )
    
    return current_user


@router.patch("/me/update", response_model=PatientPublic)
def update_patient_profile(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    patient_update: PatientUpdate
) -> Any:
    """
    Update authenticated patient's profile information
    
    **Authentication Required:** Patient token from /users/patients/quick-access or /login/patient
    
    **updatable Fields:**
    - full_name
    - cnic
    - email
    - phone_secondary
    - date_of_birth
    - residential_address
    - postal_address
    - city
    - occupation
    - medical_history
    - drug_allergies
    - family_history
    - current_medications
    - notes
    
    **Protected Fields (Cannot Update):**
    - phone (primary phone - contact support)
    - doctor_id (contact doctor)
    - gender (contact support)
    
    **Use case:** Patient updates profile info like address, medical history, CNIC
    """
    # Verify this is a patient record
    if not isinstance(current_user, Patient):
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for patients only"
        )
    
    # Verify patient is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your patient account is inactive"
        )
    
    # Prevent updating protected fields
    update_dict = patient_update.model_dump(exclude_unset=True)
    
    protected_fields = ["phone", "doctor_id", "gender"]
    if any(field in update_dict for field in protected_fields):
        raise HTTPException(
            status_code=403,
            detail="Cannot update protected fields (phone, doctor_id, gender). Contact support for changes."
        )
    
    # Validate CNIC uniqueness if being updated
    if "cnic" in update_dict and update_dict["cnic"] != current_user.cnic:
        existing_cnic = session.exec(
            select(Patient).where(
                Patient.cnic == update_dict["cnic"],
                Patient.id != current_user.id
            )
        ).first()
        if existing_cnic:
            raise HTTPException(
                status_code=400,
                detail="This CNIC is already registered in the system. Please use a different CNIC."
            )
    
    # Update patient record
    current_user.sqlmodel_update(update_dict)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user


@router.patch("/me/password")
def update_patient_password(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    current_password: str = Query(..., description="Current password (phone number)"),
    new_password: str = Query(..., min_length=6, description="New password")
) -> Message:
    """
    Update patient's password
    
    **Authentication Required:** Patient token
    
    **Security Check:**
    - Current password must match (defaults to phone number)
    - New password must be at least 6 characters
    - New password cannot be same as current
    
    **Use case:** Patient changes their login password
    """
    # Verify this is a patient record
    if not isinstance(current_user, Patient):
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for patients only"
        )
    
    # Verify current password
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )
    
    # Prevent same password
    if current_password == new_password:
        raise HTTPException(
            status_code=400,
            detail="New password cannot be the same as current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(new_password)
    session.add(current_user)
    session.commit()
    
    return Message(message="Password updated successfully")


@router.get("/me/appointments", response_model=list[AppointmentPublic])
def get_patient_appointments(
    session: SessionDep,
    current_user: CurrentUser,
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    from_date: Optional[date] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="To date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    skip: int = Query(0, ge=0, description="Skip count")
) -> Any:
    """
    Get authenticated patient's appointments
    
    **Authentication Required:** Patient token
    
    **Filter Options:**
    - status: SCHEDULED, CONFIRMED, COMPLETED, CANCELLED, NO_SHOW
    - from_date: Appointments on or after this date
    - to_date: Appointments on or before this date
    
    **Returns:** List of patient's appointments with doctor info
    
    **Sorting:** By date (ascending - upcoming first)
    
    **Use case:** Patient sees their appointment history and upcoming bookings
    
    **Example Queries:**
    - `/patients/me/appointments` - All appointments
    - `/patients/me/appointments?status=SCHEDULED` - Upcoming appointments
    - `/patients/me/appointments?from_date=2026-01-25&to_date=2026-02-25` - This month
    """
    # Verify this is a patient record
    if not isinstance(current_user, Patient):
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for patients only"
        )
    
    # Verify patient is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your patient account is inactive"
        )
    
    # Build query
    query = select(Appointment).where(
        Appointment.patient_id == current_user.id
    ).order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc())
    
    # Apply filters
    filters = []
    
    if status:
        filters.append(Appointment.status == status)
    
    if from_date:
        filters.append(Appointment.appointment_date >= from_date)
    
    if to_date:
        filters.append(Appointment.appointment_date <= to_date)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get appointments with limit and skip
    appointments = session.exec(query.offset(skip).limit(limit)).all()
    
    if not appointments:
        return []
    
    # Format response with doctor info
    response_appointments = []
    for appt in appointments:
        appt_dict = {
            **appt.__dict__,
            "patient_name": current_user.full_name,
            "patient_phone": current_user.phone
        }
        response_appointments.append(AppointmentPublic(**appt_dict))
    
    return response_appointments


@router.get("/me/appointments/upcoming")
def get_upcoming_patient_appointments(
    session: SessionDep,
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Days ahead to check")
) -> Any:
    """
    Get patient's upcoming appointments
    
    **Authentication Required:** Patient token
    
    **Returns:** Appointments scheduled for next N days (default 30 days)
    
    **Status Filter:** Only SCHEDULED and CONFIRMED appointments
    
    **Use case:** Patient sees next 30 days of appointments on dashboard
    
    **Example:**
    - `/patients/me/appointments/upcoming` - Next 30 days
    - `/patients/me/appointments/upcoming?days=7` - Next 7 days
    """
    # Verify this is a patient record
    if not isinstance(current_user, Patient):
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for patients only"
        )
    
    # Verify patient is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your patient account is inactive"
        )
    
    today = date.today()
    # Simple date calculation
    try:
        future_date = today.replace(day=today.day + days)
    except ValueError:
        # Handle month overflow
        from datetime import timedelta
        future_date = today + timedelta(days=days)
    
    # Get upcoming appointments
    appointments = session.exec(
        select(Appointment)
        .where(
            and_(
                Appointment.patient_id == current_user.id,
                Appointment.appointment_date >= today,
                Appointment.appointment_date <= future_date,
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED
                ])
            )
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc())
    ).all()
    
    if not appointments:
        return {
            "message": "No upcoming appointments",
            "appointments": [],
            "from_date": today.isoformat(),
            "to_date": future_date.isoformat()
        }
    
    # Format response
    response_appointments = []
    for appt in appointments:
        appt_dict = {
            **appt.__dict__,
            "patient_name": current_user.full_name,
            "patient_phone": current_user.phone
        }
        response_appointments.append(AppointmentPublic(**appt_dict))
    
    return {
        "total": len(response_appointments),
        "appointments": response_appointments,
        "from_date": today.isoformat(),
        "to_date": future_date.isoformat(),
        "days_ahead": days
    }


@router.get("/me/appointments/{appointment_id}", response_model=AppointmentPublic)
def get_patient_appointment_detail(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: uuid.UUID
) -> Any:
    """
    Get detail of a specific appointment
    
    **Authentication Required:** Patient token
    
    **Returns:** Complete appointment details including:
    - Date, time, duration
    - Doctor info
    - Reason, status
    - Consultation type
    
    **Use case:** Patient views appointment details before attending
    """
    # Verify this is a patient record
    if not isinstance(current_user, Patient):
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for patients only"
        )
    
    # Get appointment
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Verify patient owns this appointment
    if appointment.patient_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this appointment"
        )
    
    appt_dict = {
        **appointment.__dict__,
        "patient_name": current_user.full_name,
        "patient_phone": current_user.phone
    }
    return AppointmentPublic(**appt_dict)


@router.post("/me/appointments/{appointment_id}/cancel")
def cancel_patient_appointment(
    session: SessionDep,
    current_user: CurrentUser,
    appointment_id: uuid.UUID,
    reason: Optional[str] = Query(None, description="Reason for cancellation")
) -> Message:
    """
    Cancel patient's appointment
    
    **Authentication Required:** Patient token
    
    **Requirements:**
    - Appointment must be SCHEDULED or CONFIRMED status
    - Only patient can cancel their own appointment
    
    **Use case:** Patient cancels appointment online
    """
    # Verify this is a patient record
    if not isinstance(current_user, Patient):
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for patients only"
        )
    
    # Get appointment
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Verify patient owns this appointment
    if appointment.patient_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to cancel this appointment"
        )
    
    # Check if appointment can be cancelled
    if appointment.status not in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel appointment with status: {appointment.status}"
        )
    
    # Cancel appointment
    appointment.status = AppointmentStatus.CANCELLED
    if reason:
        appointment.notes = f"Cancelled by patient: {reason}"
    
    session.add(appointment)
    session.commit()
    
    return Message(message=f"Appointment cancelled successfully")