# api/routes/patients.py
"""
Patient Management Endpoints

Organized by Authentication Type:
- DOCTOR/ADMIN ENDPOINTS: Lines 1-300   (Use OAuth2 - CurrentUser)
- PATIENT ENDPOINTS:      Lines 300+    (Use Bearer JWT - CurrentPatient)
"""
import uuid
from typing import Any, List, Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import func, select, and_
from sqlalchemy.exc import IntegrityError

from api.deps import (
    CurrentUser,
    SessionDep,
    get_current_user,
    get_current_patient,
    CurrentPatient,
    require_doctor_role,
)
from core.security import get_password_hash, verify_password
from models.patients_model import (
    Patient, PatientCreate, PatientUpdate, PatientPublic, PatientsPublic,
)
from models.appointments_model import Appointment, AppointmentPublic
from models.cases_model import PatientCase
from models.login_model import Message
from utils.enum_service import EnumService

# Create two routers with separate tags
doctor_router = APIRouter(
    prefix="/patients",
    tags=["🧑‍⚕️ Doctor / Staff / Admin"]
)

patient_router = APIRouter(
    prefix="/patients",
    tags=["🧍 Patient"]
)

# Note: We'll include both routers in the main api_router to serve from same prefix
router = APIRouter()


# ============================================================================
# DOCTOR/ADMIN ENDPOINTS - For doctors/staff/admins managing patients
# Authentication: OAuth2 (Doctor/Staff/Admin User Token)
# ============================================================================

@doctor_router.get(
    "/",
    response_model=PatientsPublic,
    summary="List all patients",
    description="""
🔐 **Authentication Required:** DoctorOAuth2

This endpoint is accessible to doctors and staff only.

**Functionality:**
- List all patients assigned to the current doctor
- Search by name, phone, email, CNIC, or city
- Filter by payment status or gender
- Pagination support

**Response:** List of patient records with count

**Use case:** Doctor views patient list in dashboard
    """,
)
def read_patients(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    payment_status: Optional[bool] = Query(None),
    gender: Optional[str] = Query(None),
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
        .order_by(Patient.created_date.desc())
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
        # Validate gender against dynamic enum
        if not EnumService.validate_value(session, "PatientGender", gender, current_user.id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid gender '{gender}'. Use /enums/doctor/PatientGender to get valid options."
            )
        count_statement = count_statement.where(Patient.gender == gender)
        statement = statement.where(Patient.gender == gender)
    
    count = session.exec(count_statement).one()
    patients = session.exec(statement).all()
    
    return PatientsPublic(data=patients, count=count)


@doctor_router.get(
    "/{patient_id}",
    response_model=PatientPublic,
    summary="Get patient by ID",
    description="""
🔐 **Authentication Required:** DoctorOAuth2

This endpoint is accessible to doctors only.

**Functionality:**
- Retrieve detailed information for a specific patient
- Only doctors can access their own patients
- Returns complete patient profile

**Use case:** Doctor views detailed patient profile
    """,
)
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


@doctor_router.post(
    "/",
    response_model=PatientPublic,
    summary="Create new patient",
    description="""
🔐 **Authentication Required:** DoctorOAuth2

This endpoint is accessible to doctors only.

**Functionality:**
- Create a new patient record
- Auto-assigns patient to current doctor
- Validates unique email and CNIC per doctor
- Initializes patient account

**Required Fields:**
- full_name
- phone
- date_of_birth
- gender
- cnic

**Use case:** Doctor creates new patient profile
    """,
)
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


@doctor_router.put(
    "/{patient_id}",
    response_model=PatientPublic,
    summary="Update patient",
    description="""
🔐 **Authentication Required:** DoctorOAuth2

This endpoint is accessible to doctors only.

**Functionality:**
- Update patient information
- Only doctors can update their own patients
- Validates unique CNIC and email
- Supports partial updates

**Use case:** Doctor updates patient details
    """,
)
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


@doctor_router.delete(
    "/{patient_id}",
    summary="Delete patient",
    description="""
🔐 **Authentication Required:** DoctorOAuth2

This endpoint is accessible to doctors only.

**Functionality:**
- Delete a patient record permanently
- Only doctors can delete their own patients
- Cascading delete removes related data (appointments, cases, etc.)

⚠️ **Warning:** This action cannot be undone

**Use case:** Doctor removes a patient from system
    """,
)
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


@doctor_router.get(
    "/{patient_id}/stats",
    summary="Get patient statistics",
    description="""
🔐 **Authentication Required:** DoctorOAuth2

This endpoint is accessible to doctors only.

**Functionality:**
- Get statistics about a patient
- Includes: case count, appointment count, medical history summary
- Only doctors can view their own patients' stats

**Use case:** Doctor views patient analytics dashboard
    """,
)
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
# PATIENT ENDPOINTS - For authenticated patients accessing their own data
# Authentication: Bearer JWT (Patient Token)
# ============================================================================

from datetime import timedelta

@patient_router.get(
    "/me",
    response_model=PatientPublic,
    summary="Get patient profile",
    description="""
🔐 **Authentication Required:** PatientBearer

This endpoint is accessible to authenticated patients only.

**Functionality:**
- Retrieve your own patient profile
- Returns complete profile including personal, medical, and doctor info
- Auto-populated with current patient's data

**Returns:** Patient profile object

**Use case:** Patient views their profile on dashboard
    """,
)
def get_patient_profile(
    session: SessionDep,
    current_user: CurrentPatient
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
    # current_user is already a validated Patient object
    return current_user


@patient_router.patch(
    "/me/update",
    response_model=PatientPublic,
    summary="Update your profile",
    description="""
🔐 **Authentication Required:** PatientBearer

This endpoint is accessible to authenticated patients only.

**Functionality:**
- Update your own patient profile
- Supports selective field updates
- Protects critical fields (phone, doctor, gender)

**Updatable Fields:**
- full_name, cnic, email, phone_secondary
- date_of_birth, residential_address, postal_address
- city, occupation, medical_history
- drug_allergies, family_history, current_medications, notes

**Protected Fields:** phone, doctor_id, gender (contact support)

**Use case:** Patient updates profile information
    """,
)
def update_patient_profile(
    *,
    session: SessionDep,
    current_user: CurrentPatient,
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


@patient_router.patch(
    "/me/password",
    summary="Update your password",
    description="""
🔐 **Authentication Required:** PatientBearer

This endpoint is accessible to authenticated patients only.

**Functionality:**
- Change your login password securely
- Current password must match existing password
- New password minimum 6 characters

**Security:**
- Uses bcrypt hashing (Argon2)
- Current password required for verification
- Cannot reuse current password

**Use case:** Patient changes their login password
    """,
)
def update_patient_password(
    *,
    session: SessionDep,
    current_user: CurrentPatient,
    current_password: str = Query(..., description="Current password (phone number initially)"),
    new_password: str = Query(..., min_length=6, description="New password (min 6 chars)")
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


@patient_router.get(
    "/me/appointments",
    response_model=list[AppointmentPublic],
    summary="Get your appointments",
    description="""
🔐 **Authentication Required:** PatientBearer

This endpoint is accessible to authenticated patients only.

**Functionality:**
- List all your appointments (past and future)
- Filter by status (pending, confirmed, completed, cancelled)
- Sorted by date

**Status Options:**
- pending: Awaiting confirmation
- confirmed: Confirmed appointment
- completed: Appointment completed
- cancelled: Appointment cancelled

**Use case:** Patient views all their appointments
    """,
)
def get_patient_appointments(
    session: SessionDep,
    current_user: CurrentPatient,
    status: Optional[str] = Query(None, description="Filter by status"),
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


@patient_router.get(
    "/me/appointments/upcoming",
    summary="Get upcoming appointments",
    description="""
🔐 **Authentication Required:** PatientBearer

This endpoint is accessible to authenticated patients only.

**Functionality:**
- Get your upcoming appointments
- Filter for next N days (default 30)
- Only scheduled and confirmed appointments
- Sorted by date

**Query Parameters:**
- days: Number of days ahead to check (1-365, default 30)

**Use case:** Patient sees upcoming appointments on dashboard
    """,
)
def get_upcoming_patient_appointments(
    session: SessionDep,
    current_user: CurrentPatient,
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
                    "scheduled",
                    "confirmed"
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


@patient_router.get(
    "/me/appointments/{appointment_id}",
    response_model=AppointmentPublic,
    summary="Get appointment details",
    description="""
🔐 **Authentication Required:** PatientBearer

This endpoint is accessible to authenticated patients only.

**Functionality:**
- Get details of a specific appointment
- Only your own appointments visible
- Returns full appointment information

**Use case:** Patient views appointment details
    """,
)
def get_patient_appointment_detail(
    session: SessionDep,
    current_user: CurrentPatient,
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


@patient_router.post(
    "/me/appointments/{appointment_id}/cancel",
    summary="Cancel appointment",
    description="""
🔐 **Authentication Required:** PatientBearer

This endpoint is accessible to authenticated patients only.

**Functionality:**
- Cancel one of your appointments
- Only your own appointments can be cancelled
- Appointment status changed to "cancelled"

**Restrictions:**
- Cannot cancel appointments that are already completed or cancelled
- Doctor may need to approve cancellation (based on clinic policy)

**Use case:** Patient cancels an appointment
    """,
)
def cancel_patient_appointment(
    session: SessionDep,
    current_user: CurrentPatient,
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
    if appointment.status not in ["scheduled", "confirmed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel appointment with status: {appointment.status}"
        )
    
    # Cancel appointment
    appointment.status = "cancelled"
    if reason:
        appointment.notes = f"Cancelled by patient: {reason}"
    
    session.add(appointment)
    session.commit()
    
    return Message(message=f"Appointment cancelled successfully")


# ============================================================================
# EXPORT ROUTERS
# ============================================================================
# Include both doctor and patient routers so they serve from /patients prefix
# IMPORTANT: Include patient_router FIRST so patient endpoints have priority
# when path names overlap (e.g., /patients/me for both doctor and patient)
router.include_router(patient_router)
router.include_router(doctor_router)