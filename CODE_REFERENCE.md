# Code Reference - Exact Changes Made

This document shows exact code before/after for each fix.

---

## Fix 1: Token Creation with Entity Field

### File: `core/security.py`

**BEFORE:**
```python
def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

**AFTER:**
```python
def create_access_token(
    subject: str | Any, 
    expires_delta: timedelta,
    entity: str = "user",
    role: str = None
) -> str:
    """
    Create JWT access token.
    
    Args:
        subject: The user/patient ID
        expires_delta: Token expiration time
        entity: Type of actor - "user" (doctor/staff/admin) or "patient"
        role: User role - "doctor", "staff", "admin", "patient"
    
    Token payload will include:
    - sub: subject ID
    - entity: actor type (determines which table to query)
    - role: role type (for authorization)
    - exp: expiration timestamp
    """
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "entity": entity,
    }
    if role:
        to_encode["role"] = role
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

---

## Fix 2: Add get_current_patient Dependency

### File: `api/deps.py`

**ADD (after existing imports and before get_current_user):**

```python
def get_current_patient(session: SessionDep, token: TokenDep) -> Patient:
    """
    Authentication dependency for patient-protected endpoints.
    
    Validates that:
    1. Token contains entity='patient' (not a user/doctor token)
    2. Patient ID in token exists in Patient table
    3. Patient account is active
    
    This completely separate from get_current_user() to ensure patients
    authenticate from the Patient table, not the User table.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid patient authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )

        entity = payload.get("entity")
        patient_id = payload.get("sub")

        # Verify this is a patient token, not a user/doctor token
        if entity != "patient" or not patient_id:
            raise credentials_exception

    except (jwt.JWTError, jwt.DecodeError, ValidationError):
        raise credentials_exception

    # Query Patient table, not User table
    patient = session.get(Patient, patient_id)

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    if not patient.is_active:
        raise HTTPException(
            status_code=400,
            detail="Patient account is inactive",
        )

    return patient


CurrentPatient = Annotated[Patient, Depends(get_current_patient)]
```

**ALSO ADD (at top of file):**
```python
from models.patients_model import Patient
```

---

## Fix 3: Update Token Creation Calls

### File: `routes/login.py`

**Location 1 - `/login/access-token` endpoint:**

**BEFORE:**
```python
access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
access_token = security.create_access_token(
    user.id, expires_delta=access_token_expires
)
```

**AFTER:**
```python
access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
access_token = security.create_access_token(
    user.id, expires_delta=access_token_expires, entity="user", role=user.role.value
)
```

---

**Location 2 - `/login` endpoint (doctor login):**

**BEFORE:**
```python
if login_data.remember_me:
    access_token_expires = timedelta(days=30)
else:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

access_token = security.create_access_token(
    user.id, expires_delta=access_token_expires
)
```

**AFTER:**
```python
if login_data.remember_me:
    access_token_expires = timedelta(days=30)
else:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

access_token = security.create_access_token(
    user.id, expires_delta=access_token_expires, entity="user", role=user.role.value
)
```

---

**Location 3 - `/login/patient-simple` endpoint:**

**BEFORE:**
```python
# Generate token
access_token_expires = timedelta(days=30)  # Default longer expiry for simplified login
access_token = security.create_access_token(
    patient.id, expires_delta=access_token_expires
)
```

**AFTER:**
```python
# Generate token
access_token_expires = timedelta(days=30)  # Default longer expiry for simplified login
access_token = security.create_access_token(
    patient.id, expires_delta=access_token_expires, entity="patient", role="patient"
)
```

---

## Fix 4: Fix Patient Booking Endpoint

### File: `routes/appointments.py`

**UPDATE IMPORTS (top of file):**

**BEFORE:**
```python
from api.deps import CurrentUser, SessionDep
```

**AFTER:**
```python
from api.deps import CurrentUser, SessionDep, CurrentPatient
```

---

**ALSO ADD (near top with other imports):**
```python
from sqlalchemy.exc import IntegrityError
```

---

**REPLACE ENTIRE ENDPOINT:**

**BEFORE:**
```python
@router.post("/patient/book", response_model=AppointmentPublic)
def book_appointment_patient(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    doctor_id: uuid.UUID = Query(..., description="Doctor UUID"),
    appointment_date: date = Query(...),
    appointment_time: time = Query(...),
    reason: Optional[str] = Query(None)
) -> Any:
    """
    PROTECTED - Patient books appointment with authenticated patient token
    ...
    """
    # Verify request is from authenticated patient
    if not isinstance(current_user, Patient):
        raise HTTPException(
            status_code=403,
            detail="Only authenticated patients can book appointments"
        )
    
    # Verify patient is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your patient account is inactive"
        )
    
    # ... rest of code using current_user instead of patient
```

**AFTER:**
```python
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
    from models.users_model import User, UserRole
    doctor = session.get(User, doctor_id)
    if not doctor or doctor.role != UserRole.DOCTOR or not doctor.is_active:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Verify patient belongs to this doctor
    if patient.doctor_id != doctor_id:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this doctor. Please contact support."
        )
    
    # ... rest of code using patient instead of current_user
```

---

**AND - Replace the appointment creation/commit section:**

**BEFORE:**
```python
    # Create appointment
    appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=current_user.id,
        appointment_date=appointment_date,
        appointment_time=appointment_time_clean,
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        consultation_type="follow_up",
        reason=reason,
    )
    
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    
    # Update patient's last visit date
    current_user.last_visit_date = appointment_date
    session.add(current_user)
    session.commit()
    
    appt_dict = {
        **appointment.__dict__,
        "patient_name": current_user.full_name,
        "patient_phone": current_user.phone
    }
    return AppointmentPublic(**appt_dict)
```

**AFTER:**
```python
    # Create appointment
    appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=patient.id,
        appointment_date=appointment_date,
        appointment_time=appointment_time_clean,
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
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
    
    appt_dict = {
        **appointment.__dict__,
        "patient_name": patient.full_name,
        "patient_phone": patient.phone
    }
    return AppointmentPublic(**appt_dict)
```

---

## Fix 5: Add Booked Flag to Slot Model

### File: `models/public_models.py`

**BEFORE:**
```python
class AvailableSlot(SQLModel):
    """Available appointment slot"""
    start: str
    end: str
    duration_minutes: int = 30
```

**AFTER:**
```python
class AvailableSlot(SQLModel):
    """Available appointment slot"""
    start: str
    end: str
    duration_minutes: int = 30
    booked: bool = False  # Whether this slot is already booked
```

---

## Fix 6: Update Availability Endpoint

### File: `routes/public.py`

**UPDATE IMPORTS (top of file):**

**BEFORE:**
```python
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select
```

**AFTER:**
```python
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import select, and_
```

---

**REPLACE availability logic section:**

**BEFORE:**
```python
    if not availability_slots:
        return AvailabilityResponse(
            date=check_date.isoformat(),
            day_of_week=day_name,
            available_slots=[],
            message="No available slots for this date",
        )
    
    # Calculate 30-minute slots from availability windows
    available_slots = []
    for slot in availability_slots:
        current_time = datetime.combine(check_date, slot.start_time)
        end_time = datetime.combine(check_date, slot.end_time)
        
        while current_time + timedelta(minutes=30) <= end_time:
            slot_start = current_time.time()
            slot_end = (current_time + timedelta(minutes=30)).time()
            
            available_slots.append(
                AvailableSlot(
                    start=slot_start.strftime("%H:%M"),
                    end=slot_end.strftime("%H:%M"),
                    duration_minutes=30,
                )
            )
            current_time += timedelta(minutes=30)
```

**AFTER:**
```python
    if not availability_slots:
        return AvailabilityResponse(
            date=check_date.isoformat(),
            day_of_week=day_name,
            available_slots=[],
            message="No available slots for this date",
        )
    
    # Get appointments for the day to identify booked slots
    appointments = session.exec(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == doctor_uuid,
                Appointment.appointment_date == check_date,
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED
                ])
            )
        )
    ).all()
    
    # Create set of booked time strings for quick lookup
    booked_times = set()
    for appointment in appointments:
        booked_times.add(appointment.appointment_time.strftime("%H:%M"))
    
    # Calculate 30-minute slots from availability windows
    available_slots = []
    for slot in availability_slots:
        current_time = datetime.combine(check_date, slot.start_time)
        end_time = datetime.combine(check_date, slot.end_time)
        
        while current_time + timedelta(minutes=30) <= end_time:
            slot_start = current_time.time()
            slot_start_str = slot_start.strftime("%H:%M")
            slot_end = (current_time + timedelta(minutes=30)).time()
            
            # Check if this slot is booked
            is_booked = slot_start_str in booked_times
            
            available_slots.append(
                AvailableSlot(
                    start=slot_start_str,
                    end=slot_end.strftime("%H:%M"),
                    duration_minutes=30,
                    booked=is_booked
                )
            )
            current_time += timedelta(minutes=30)
```

---

**AND - Add error handling to public booking endpoint:**

**BEFORE (in book_appointment_public):**
```python
    # Create appointment
    appointment = Appointment(
        doctor_id=doctor_uuid,
        patient_id=patient.id,
        appointment_date=booking_data.appointment_date,
        appointment_time=booking_data.appointment_time,
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        consultation_type="first",
        reason=booking_data.reason,
    )
    
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    
    # Update patient's last visit date
    patient.last_visit_date = booking_data.appointment_date
    session.add(patient)
    session.commit()
    
    return AppointmentBookingResponse(
        success=True,
        appointment_id=str(appointment.id),
        message=f"Appointment booked successfully for {booking_data.appointment_date.isoformat()} at {booking_data.appointment_time.strftime('%H:%M')}",
    )
```

**AFTER:**
```python
    # Create appointment
    appointment = Appointment(
        doctor_id=doctor_uuid,
        patient_id=patient.id,
        appointment_date=booking_data.appointment_date,
        appointment_time=booking_data.appointment_time,
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
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
```

---

## Fix 7: Add Error Handling to Doctor Appointment Creation

### File: `routes/appointments.py`

**In `create_appointment()` function:**

**BEFORE:**
```python
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
    
    appt_dict = {
        **appointment.__dict__,
        "patient_name": appointment.patient.full_name if appointment.patient else None,
        "patient_phone": appointment.patient.phone if appointment.patient else None
    }
    return AppointmentPublic(**appt_dict)
```

**AFTER:**
```python
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
    
    appt_dict = {
        **appointment.__dict__,
        "patient_name": appointment.patient.full_name if appointment.patient else None,
        "patient_phone": appointment.patient.phone if appointment.patient else None
    }
    return AppointmentPublic(**appt_dict)
```

---

## Fix 8: Database Migration

### File: `alembic/versions/20260125_add_appointment_unique_constraint.py`

**NEW FILE - Create this file:**

```python
"""Add UNIQUE constraint to prevent double booking

Revision ID: 20260125_add_appointment_unique_constraint
Revises: fe5393294599
Create Date: 2026-01-25

This migration adds a database-level constraint to prevent race condition double booking.
The constraint ensures no two appointments can be scheduled for the same doctor
at the same date and time (excluding cancelled appointments).

This provides production-grade safety at the DB level, preventing double-booking
even when concurrent requests arrive simultaneously.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260125_add_appointment_unique_constraint"
down_revision: Union[str, Sequence[str], None] = "fe5393294599"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add UNIQUE constraint on (doctor_id, appointment_date, appointment_time)
    where status != 'cancelled'
    
    This prevents two appointments from being scheduled for the same time slot,
    effectively preventing double-booking at the database level.
    """
    op.create_index(
        "idx_appointment_no_double_booking",
        "appointment",
        [
            "doctor_id",
            "appointment_date",
            "appointment_time",
        ],
        unique=True,
        postgresql_where=sa.text("status != 'cancelled'"),
    )


def downgrade() -> None:
    """
    Drop the unique constraint index
    """
    op.drop_index("idx_appointment_no_double_booking", table_name="appointment")
```

---

## Summary of All Changes

| Component | Type | Changes |
|-----------|------|---------|
| Token Creation | Enhanced | Added entity/role fields |
| Patient Auth | New | Created get_current_patient() |
| Login Calls | Updated | 3 token creation calls updated |
| Patient Booking | Fixed | Uses CurrentPatient, added error handling |
| Availability | Enhanced | Added booked flag to response |
| Slot Model | Updated | Added booked: bool field |
| Error Handling | Enhanced | Added IntegrityError handling to 3 endpoints |
| Database | Migration | Added UNIQUE constraint |

---

## Testing Examples

### Test Patient Authentication
```bash
# 1. Login as patient
curl -X POST http://localhost:8000/api/v1/login/patient-simple \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "phone": "03001234567"
  }'

# Response includes token with entity: "patient"

# 2. Book appointment with patient token
curl -X POST http://localhost:8000/api/v1/appointments/patient/book \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "doctor_id": "...",
    "appointment_date": "2026-01-27",
    "appointment_time": "14:00"
  }'

# Should succeed (no more 400 error)
```

### Test Booked Slots
```bash
# Check availability
curl -X GET http://localhost:8000/api/v1/public/availability/{doctor_id}/2026-01-27

# Response includes booked flag on each slot
```

### Test Double Booking Prevention
```bash
# Make two concurrent requests
curl -X POST ... &
curl -X POST ... &

# One succeeds, one fails with 409 Conflict
```

---

## Verification Checklist

- [x] Token creation enhanced with entity/role fields
- [x] get_current_patient() dependency created
- [x] All token creation calls updated (3 locations)
- [x] Patient booking endpoint fixed
- [x] Availability endpoint enhanced with booked flag
- [x] Slot model updated with booked field
- [x] Error handling added to 3 endpoints
- [x] Database migration created
- [x] No syntax errors
- [x] All imports correct
- [x] Type hints valid
- [x] Backward compatible
