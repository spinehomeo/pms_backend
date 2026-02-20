# Dynamic Enum System - Backend Integration Guide

## Quick Start for Backend Developers

### The Problem Solved

**Before:**
```python
# Hardcoded Python Enum - requires code change + deployment for new values
class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"

# If you need to add "RESCHEDULED", you must:
# 1. Edit this file
# 2. Run migration (if DB column changed type)
# 3. Redeploy entire backend
# 4. Redeploy frontend to handle new value
```

**After:**
```python
# Dynamic - admin adds values via API, zero code changes
# Database stores string values, validated at runtime

# 1. Admin submits: POST /enums/admin/AppointmentStatus
#    { "value": "rescheduled", "label": "Rescheduled" }
# 2. It's immediately available everywhere
# 3. Frontend loads it next time the page refreshes
# 4. Done!
```

---

## Using EnumService in Your Routes

### 1. Simple Validation (Most Common)

```python
from utils.enum_service import EnumService
from api.deps import CurrentUser, SessionDep
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/appointments")
def create_appointment(
    payload: AppointmentCreate,
    session: SessionDep,
    current_user: CurrentUser
):
    """Create appointment with enum validation"""
    
    # Validate status against doctor's filtered options
    is_valid = EnumService.validate_value(
        session=session,
        enum_type_key="AppointmentStatus",
        value=payload.status,
        doctor_id=current_user.id  # Filter by doctor
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: '{payload.status}'"
        )
    
    # Now safe to save - status is a valid string
    appointment = Appointment(
        status=payload.status,  # String, not Python Enum
        doctor_id=current_user.id,
        patient_id=payload.patient_id,
        # ... other fields
    )
    
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment
```

### 2. Get Available Options for Dropdown

```python
@router.get("/appointments/statuses")
def get_appointment_statuses(
    session: SessionDep,
    current_user: CurrentUser
):
    """Return options for dropdown in frontend"""
    
    options = EnumService.get_doctor_options(
        session=session,
        enum_type_key="AppointmentStatus",
        doctor_id=current_user.id
    )
    
    return {
        "enum_type": "AppointmentStatus",
        "options": [
            {"id": opt.id, "value": opt.value, "label": opt.label}
            for opt in options
        ]
    }
```

### 3. Get All Global Options (Admin Only)

```python
@router.get("/admin/appointment-statuses", dependencies=[Depends(get_current_active_superuser)])
def get_all_statuses(session: SessionDep):
    """Admin view - see all options including inactive ones"""
    
    all_options = EnumService.get_global_options(
        session=session,
        enum_type_key="AppointmentStatus",
        active_only=False  # Show inactive too
    )
    
    return all_options
```

### 4. Validate & Display Error with Available Options

```python
@router.post("/prescriptions")
def create_prescription(
    payload: PrescriptionCreate,
    session: SessionDep,
    current_user: CurrentUser
):
    """Create prescription with detailed error messages"""
    
    # Validate prescription type
    if not EnumService.validate_value(
        session,
        "PrescriptionType",
        payload.type,
        doctor_id=current_user.id
    ):
        # Get available options for error message
        available = EnumService.get_doctor_options(
            session, "PrescriptionType", current_user.id
        )
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Invalid prescription type: {payload.type}",
                "available_options": [opt.value for opt in available]
            }
        )
    
    # Validate repetition
    if not EnumService.validate_value(
        session,
        "RepetitionEnum",
        payload.repetition
    ):
        raise HTTPException(400, detail="Invalid repetition frequency")
    
    # Create prescription
    prescription = Prescription(
        type=payload.type,
        repetition=payload.repetition,
        doctor_id=current_user.id,
        # ... other fields
    )
    
    session.add(prescription)
    session.commit()
    return prescription
```

---

## Updating Existing Routes

### Example: AppointmentStatus

**Before:**
```python
from enum import Enum

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class AppointmentCreate(SQLModel):
    status: AppointmentStatus = Field(default=AppointmentStatus.SCHEDULED)
                                     # ^^ Uses Python Enum

@router.post("/appointments")
def create_appointment(payload: AppointmentCreate, ...):
    # Works with Enum, but can't add new values without code change
    appointment = Appointment(status=payload.status, ...)
```

**After:**
```python
# DELETE the Python Enum class completely
# Python Enum no longer needed!

class AppointmentCreate(SQLModel):
    status: str  # Just a string
                 # ^^ Validated via DB, not Python type system

@router.post("/appointments")
def create_appointment(payload: AppointmentCreate, ...):
    # Validate against database enum
    if not EnumService.validate_value(session, "AppointmentStatus", payload.status):
        raise HTTPException(400, "Invalid status")
    
    appointment = Appointment(status=payload.status, ...)
```

---

## All 10 Core Enum Types

These are already seeded. Use them immediately:

### 1. AppointmentStatus
```python
# For appointments
if not EnumService.validate_value(session, "AppointmentStatus", status):
    raise HTTPException(400, "Invalid status")

# Available values (seeded):
# - "Pending", "Confirmed", "Cancelled", "Completed", "No Show"
```

### 2. PrescriptionType
```python
# For prescriptions
if not EnumService.validate_value(session, "PrescriptionType", type):
    raise HTTPException(400, "Invalid prescription type")

# Available values:
# - "Constitutional", "Classical", "Intercurrent", 
#   "Bio Chemic", "Mother Tincture", "Patent"
```

### 3. RepetitionEnum
```python
# For prescription dosage frequency
if not EnumService.validate_value(session, "RepetitionEnum", frequency):
    raise HTTPException(400, "Invalid frequency")

# Available values:
# - "Once Daily", "Twice Daily", "Three Times Daily",
#   "Four Times Daily", "As Needed", "Weekly"
```

### 4. DayOfWeek
```python
# For doctor availability scheduling
if not EnumService.validate_value(session, "DayOfWeek", day):
    raise HTTPException(400, "Invalid day")

# Available values:
# - "Monday", "Tuesday", "Wednesday", "Thursday",
#   "Friday", "Saturday", "Sunday"
```

### 5. ExceptionType
```python
# For doctor availability exceptions
if not EnumService.validate_value(session, "ExceptionType", type):
    raise HTTPException(400, "Invalid exception type")

# Available values:
# - "Holiday", "Emergency", "Personal Leave"
```

### 6. FormEnum
```python
# For medicine form
if not EnumService.validate_value(session, "FormEnum", form):
    raise HTTPException(400, "Invalid form")

# Available values:
# - "Tablet", "Syrup", "Capsule", "Injection", "Drops", "Globules", "Powder"
```

### 7. ScaleEnum
```python
# For medicine potency scale
if not EnumService.validate_value(session, "ScaleEnum", scale):
    raise HTTPException(400, "Invalid scale")

# Available values:
# - "Low", "Medium", "High"
```

### 8. ManufacturerEnum
```python
# For medicine manufacturer
if not EnumService.validate_value(session, "ManufacturerEnum", mfr):
    raise HTTPException(400, "Invalid manufacturer")

# Available values:
# - "Manufacturer A", "Manufacturer B", "Local"
```

### 9. PatientGender
```python
# For patient demographics
if not EnumService.validate_value(session, "PatientGender", gender):
    raise HTTPException(400, "Invalid gender")

# Available values:
# - "Male", "Female", "Other"
```

### 10. UserRole
```python
# For user roles
if not EnumService.validate_value(session, "UserRole", role):
    raise HTTPException(400, "Invalid role")

# Available values:
# - "admin", "doctor", "staff"
```

---

## FastAPI Dependency for DRY Validation

If you're validating the same enum in multiple endpoints, create a dependency:

```python
# api/deps.py - add this

from fastapi import Query, Depends

def validate_enum_value(
    enum_type: str,
    doctor_id: Optional[UUID] = None
):
    """
    Factory dependency for enum validation.
    Use in multiple endpoints without repeating validation code.
    """
    def _validate(
        value: str = Query(...),
        session: SessionDep = Depends(),
    ) -> str:
        from utils.enum_service import EnumService
        
        is_valid = EnumService.validate_value(
            session, enum_type, value, doctor_id
        )
        
        if not is_valid:
            raise HTTPException(400, f"Invalid {enum_type}: {value}")
        
        return value
    
    return _validate
```

Usage:
```python
# In your route
@router.post("/appointments")
def create_appointment(
    status: str = Depends(validate_enum_value("AppointmentStatus")),
    session: SessionDep = Depends(),
    current_user: CurrentUser = Depends()
):
    """status is already validated"""
    appointment = Appointment(status=status, ...)
```

---

## Database Constraints

The system enforces data integrity:

```sql
-- Unique enum type keys
UNIQUE INDEX idx_enum_type_key ON enum_types(key)

-- Unique option per enum type (can't have duplicate "Confirmed" in AppointmentStatus)
UNIQUE INDEX idx_enum_option_unique 
  ON enum_options(enum_type_id, value)

-- Unique doctor preference per option (only one toggle per doctor/option pair)
UNIQUE INDEX idx_doctor_enum_pref_doctor_option
  ON doctor_enum_preferences(doctor_id, enum_option_id)
```

---

## Handling Migrations

### Auto-generate from models:
```bash
alembic revision --autogenerate -m "add_dynamic_enum_tables"
alembic upgrade head
```

### Manual seed:
```bash
python -m utils.initial_data
```

This creates enum types + all 10 core options.

---

## Querying Enums Directly (Advanced)

If you need custom queries:

```python
from sqlmodel import select
from models.enum_option_model import EnumOption

# Get all options for a type
options = session.exec(
    select(EnumOption)
    .where(EnumOption.enum_type == "AppointmentStatus")
    .where(EnumOption.is_active == True)
    .order_by(EnumOption.sort_order)
).all()

# Get specific option by value
option = session.exec(
    select(EnumOption)
    .where(
        EnumOption.enum_type == "PrescriptionType",
        EnumOption.value == "Constitutional"
    )
).first()

# Get disabled options for a doctor
from models.enum_option_model import DoctorEnumPreference

disabled = session.exec(
    select(EnumOption)
    .join(DoctorEnumPreference)
    .where(
        DoctorEnumPreference.doctor_id == doctor_id,
        DoctorEnumPreference.is_enabled == False
    )
).all()
```

---

## Error Handling Patterns

### Pattern 1: Simple Check
```python
if not EnumService.validate_value(session, "AppointmentStatus", status):
    raise HTTPException(400, f"Invalid status: {status}")
```

### Pattern 2: With Available Options
```python
is_valid = EnumService.validate_value(session, "AppointmentStatus", status)
if not is_valid:
    available = [opt.value for opt in EnumService.get_global_options(session, "AppointmentStatus")]
    raise HTTPException(400, detail={
        "error": f"Invalid status",
        "provided": status,
        "allowed": available
    })
```

### Pattern 3: Doctor-specific
```python
is_valid = EnumService.validate_value(
    session, "AppointmentStatus", status, doctor_id=current_user.id
)
if not is_valid:
    raise HTTPException(400, f"Status not enabled for your clinic")
```

---

## Testing

### Unit Test Example
```python
from utils.enum_service import EnumService

def test_validate_appointment_status(session):
    # Should be valid
    assert EnumService.validate_value(
        session, "AppointmentStatus", "Confirmed"
    ) == True
    
    # Should be invalid
    assert EnumService.validate_value(
        session, "AppointmentStatus", "InvalidStatus"
    ) == False
```

### Integration Test Example
```python
def test_create_appointment_with_validation(client, session):
    # Valid status
    response = client.post("/appointments", json={
        "status": "Confirmed",
        "patient_id": "...",
    })
    assert response.status_code == 201
    
    # Invalid status
    response = client.post("/appointments", json={
        "status": "BadStatus",
        "patient_id": "...",
    })
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]
```

---

## Performance Considerations

### Query Optimization

The service uses efficient queries:

```python
# This is fast - filters on indexed columns
disabled_ids = session.exec(
    select(DoctorEnumPreference.enum_option_id)
    .where(DoctorEnumPreference.doctor_id == doctor_id)
    .where(DoctorEnumPreference.is_enabled == False)
).all()

# Then NOT IN clause is efficient with moderate number of disabled options
query.where(EnumOption.id.notin_(disabled_ids))
```

### Caching (Frontend)
```typescript
// Cache for 30 seconds - options don't change frequently
const { data } = useQuery({
  queryKey: ['enum', enumTypeKey, doctorId],
  queryFn: () => api.get(`/enums/doctor/${enumTypeKey}`),
  staleTime: 30_000,  // 30 seconds
})
```

---

## Rollout Strategy

### Phase 1: Infrastructure (Done)
✅ Database tables created
✅ EnumService implemented
✅ API routes ready
✅ Seed data loaded

### Phase 2: Migrate One Enum (Start Here)
1. Pick: AppointmentStatus
2. Remove Python Enum from code
3. Change `AppointmentCreate.status` from `AppointmentStatus` to `str`
4. Add validation: `EnumService.validate_value(...)`
5. Test in Swagger
6. Update frontend to use dynamic dropdown
7. Deploy

### Phase 3: Rollout Others
- RepetitionEnum (prescriptions)
- PrescriptionType (prescriptions)
- DayOfWeek (availability)
- ExceptionType (availability)
- etc.

### Phase 4: Doctor Preferences
- Unlock preference UI
- Doctors can customize dropdowns
- No code changes needed

---

## Troubleshooting

### "Enum type not found"
```
Error: Enum type 'BadKey' not found
```
**Fix:** Verify the enum_type_key
```python
# Check what types exist
types = EnumService.get_all_enum_types(session)
print([t.key for t in types])
```

### "Option doesn't exist"
```
Error: Option 'InvalidValue' not found for AppointmentStatus
```
**Fix:** Check valid values
```python
options = EnumService.get_doctor_options(session, "AppointmentStatus", doctor_id)
print([opt.value for opt in options])
```

### "Doctor has disabled this option"
If doctor toggled off an option and it's not available, it's working as expected. Either:
- Let doctor re-enable it, or
- Admin disables the global toggle instead

---

Next Steps:
1. Run `alembic upgrade head`
2. Run `python -m utils.initial_data`
3. Pick one enum type and migrate it
4. Test in Swagger at `/docs`
5. Frontend implementation follows the guide in `DYNAMIC_ENUM_SYSTEM.md`
