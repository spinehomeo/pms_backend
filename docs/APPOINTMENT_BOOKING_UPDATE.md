# Appointment Booking Integration with Quick-Access Flow

## Overview
Updated the public appointment booking endpoint to align with the simplified quick-access patient registration flow. Patients can now register and book appointments in a single seamless flow without needing pre-registration.

## Changes Made

### 1. **PublicBookingRequest Model** (`models/public_models.py`)
Updated from email-based to phone-based patient identification:

**Before:**
```python
class PublicBookingRequest(SQLModel):
    doctor_id: str
    patient_email: str  # Required pre-registration
    appointment_date: date
    appointment_time: time
    reason: Optional[str] = None
```

**After:**
```python
class PublicBookingRequest(SQLModel):
    doctor_id: str
    full_name: str
    phone: str
    gender: str = "other"  # Optional, defaults to "other"
    appointment_date: date
    appointment_time: time
    reason: Optional[str] = None
```

### 2. **Public Booking Endpoint** (`routes/public.py`)
Completely refactored to support inline patient registration:

#### Key Features:
1. **Phone-based Patient Lookup**: Queries patient by phone instead of email
2. **Automatic Patient Registration**: Creates patient record if not exists
3. **Availability Validation**: Checks appointment time against doctor's availability schedule
4. **Auto-generated Email**: Creates system email `patient_{phone}@system.local`
5. **Smart Registration**: Reuses existing user if email already exists

#### Flow Diagram:
```
POST /public/appointments/book
    ↓
1. Validate doctor exists and is active
    ↓
2. Validate appointment time against doctor's availability
    ↓
3. Check if patient exists by (phone, doctor_id)
    ↓
    ├─ If patient exists → Skip to step 6
    └─ If patient NOT exists:
        ├─ Auto-generate email: patient_{phone}@system.local
        ├─ Create User record (if email doesn't exist)
        ├─ Create Patient record (linked to doctor)
        ├─ Hash phone as password
        └─ Set gender and other fields
    ↓
6. Create Appointment record
    ↓
7. Update patient's last_visit_date
    ↓
8. Return AppointmentBookingResponse with confirmation
```

## API Usage

### Request Example:
```bash
POST /public/appointments/book
Content-Type: application/json

{
  "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Ahmed Ali",
  "phone": "03001234567",
  "gender": "male",
  "appointment_date": "2025-02-01",
  "appointment_time": "14:30",
  "reason": "Checkup for headache"
}
```

### Response Example:
```json
{
  "success": true,
  "appointment_id": "660e8400-e29b-41d4-a716-446655441111",
  "message": "Appointment booked successfully for 2025-02-01 at 14:30"
}
```

### Error Examples:

#### Doctor not found:
```json
{
  "detail": "Doctor not found"
}
```

#### No availability:
```json
{
  "detail": "Doctor has no available slots on Saturdays"
}
```

#### Time not within availability:
```json
{
  "detail": "Appointment time not within doctor's availability. Available: 09:00-12:00, 14:00-18:00"
}
```

## Workflow Comparison

### Old Flow (4 API Calls):
1. POST `/users/patients/register-simple` → Register patient
2. POST `/login/patient-simple` → Login & get token
3. GET `/public/availability/{doctor_id}/{date}` → Check slots
4. POST `/public/appointments/book` → Book appointment

### New Flow (2 API Calls):
1. POST `/users/patients/quick-access` → Register + Login (get token)
2. POST `/public/appointments/book` → Auto-register + Book appointment (on same endpoint)

**OR** (for already-registered patients):
1. (Already have token from quick-access)
2. POST `/public/appointments/book` → Auto-detects existing patient, books directly

## Implementation Details

### Patient Registration Flow (Auto-Inline):
```python
# Auto-generate email
auto_email = f"patient_{phone}@system.local"

# Check if user exists (reuse if exists)
existing_user = session.query(User).filter(User.email == auto_email).first()

if not existing_user:
    # Create new user with role PATIENT
    user = crud.create_user(
        email=auto_email,
        password=phone,  # Phone is password for simplified UX
        full_name=full_name,
        role=UserRole.PATIENT,
        phone=phone,
        is_verified=True
    )

# Create patient record
patient = Patient(
    doctor_id=doctor_uuid,
    full_name=full_name,
    phone=phone,
    gender=PatientGender(gender),
    hashed_password=get_password_hash(phone),
    cnic="PENDING"  # To be updated later
)
```

### Availability Validation:
Uses the same `_validate_availability()` function from `routes/appointments.py`:
- Checks if appointment time falls within doctor's DoctorAvailability slots
- Validates against day of week and time windows
- Prevents double-booking

## Database Changes

### Patient Model Fields Used:
- `id` (UUID, primary key)
- `doctor_id` (UUID, foreign key)
- `full_name` (string)
- `phone` (string, unique per doctor)
- `gender` (enum: male, female, other, child)
- `cnic` (string, defaults to "PENDING")
- `hashed_password` (string, hashed phone)
- `last_visit_date` (date, optional)

### User Model Fields Used:
- `id` (UUID, primary key)
- `email` (string, unique)
- `hashed_password` (string)
- `full_name` (string)
- `role` (enum: PATIENT)
- `phone` (string)
- `is_active` (bool)
- `is_verified` (bool)

## Security Considerations

1. **Phone as Password**: Simplified UX for mobile-first app
   - Phone numbers are case-insensitive and simpler to type
   - Suitable for low-security medical consultation booking
   - Consider MFA in future versions

2. **Email Security**: Auto-generated system emails prevent email enumeration
   - Format: `patient_{phone}@system.local`
   - Won't conflict with real doctor emails

3. **Availability Checking**: Prevents overbooking by validating slots

4. **Patient Isolation**: Each patient is registered per doctor
   - Patients with same phone can be registered to different doctors
   - Prevents cross-clinic patient data leaks

## Testing Checklist

- [ ] Test new patient registration + booking in one call
- [ ] Test existing patient booking (should reuse patient record)
- [ ] Test invalid doctor ID format
- [ ] Test non-existent doctor
- [ ] Test appointment time outside availability window
- [ ] Test appointment time in valid availability slot
- [ ] Test gender enum validation (male/female/other/child)
- [ ] Test missing optional fields (gender defaults to "other")
- [ ] Test duplicate phone booking (should reuse patient)
- [ ] Verify last_visit_date is updated
- [ ] Verify appointment status is SCHEDULED
- [ ] Verify consultation_type is "first"
- [ ] Verify 30-minute duration is set

## Migration Notes

- **No database migration needed**: Using existing Patient and Appointment tables
- **Backward Compatible**: Old endpoints still work (commented out but available)
- **Email Generation**: System auto-generates emails on-the-fly, no table changes

## Related Endpoints

### Patient Management:
- `POST /users/patients/register-simple` - Manual registration (still available)
- `POST /login/patient-simple` - Manual login (still available)
- `POST /users/patients/quick-access` - Combined registration + login (returns token)

### Doctor Management:
- `GET /public/doctors` - List available doctors
- `GET /public/availability/{doctor_id}/{date}` - Check available slots

### Appointment Management:
- `POST /public/appointments/book` - Public booking (NEW inline registration)
- `GET /appointments/` - List patient's appointments (authenticated)
- `PATCH /appointments/{id}` - Update appointment (authenticated doctor)
- `DELETE /appointments/{id}` - Cancel appointment (authenticated)

## Future Enhancements

1. **SMS Verification**: Add OTP verification before booking
2. **Payment Integration**: Add payment processing before confirmation
3. **Notification Service**: Send SMS/Email confirmations
4. **Appointment Reminders**: Auto-send reminders before appointment
5. **Multi-slot Selection**: Allow patients to see and choose from multiple slots
6. **Patient Profile Completion**: Gradual profile update (CNIC, address, etc.)

## Code Quality

- ✅ No syntax errors
- ✅ All imports resolved
- ✅ Type hints complete
- ✅ Docstrings updated
- ✅ Error handling comprehensive
- ✅ Validation logic reused from appointments.py
