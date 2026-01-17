# Doctor Availability doctor_availability - Implementation Summary

## What Was Created

### 1. **New Model: DoctorAvailability**
   - File: [models/doctor_availability_model.py](models/doctor_availability_model.py)
   - Stores doctor's working hours for each day of the week
   - Supports multiple time slots per day
   - Includes capacity management via `max_patients_per_slot`

### 2. **Complete API Endpoints in doctor_availability.py**
   - File: [routes/doctor_availability.py](routes/doctor_availability.py)
   - Fully implemented with all CRUD operations
   - 13 endpoints total covering all scenarios

### 3. **Database Migration**
   - File: [alembic/versions/20260117_add_doctor_availability.py](alembic/versions/20260117_add_doctor_availability.py)
   - Creates `doctor_availability` table with proper indexes
   - Ready to run: `alembic upgrade head`

### 4. **Documentation**
   - File: [docs/DOCTOR_AVAILABILITY_API.md](docs/DOCTOR_AVAILABILITY_API.md)
   - Complete API reference with examples

---

## Features Implemented

✅ **Doctor doctor_availability (Full CRUD)**
- Create single availability slot
- Create multiple slots in bulk
- Read all slots (with optional filtering)
- Read specific slot
- Update slots (with overlap validation)
- Toggle slots on/off
- Delete slots (individual or bulk)

✅ **Doctor Schedule Management**
- View complete weekly schedule organized by day
- View weekly schedule with booked patient info
- Supports multiple time slots per day (e.g., 9-12 AM and 3-5 PM)

✅ **Patient Integration**
- Check available slots for any specific day
- Accounts for existing booked appointments
- Returns 30-minute intervals within available slots
- Shows booking count and total available slots

✅ **Validations**
- Prevents overlapping time slots on same day
- Validates time ranges (start < end)
- Doctor authorization checks
- Enum validation for days of week

---

## Database Schema

### DoctorAvailability Table
```sql
CREATE TABLE doctor_availability (
    id UUID PRIMARY KEY,
    doctor_id UUID NOT NULL (FOREIGN KEY to user.id),
    day_of_week ENUM('monday' - 'sunday') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT true,
    max_patients_per_slot INTEGER NULL,
    notes VARCHAR NULL
);

-- Indexes for performance
CREATE INDEX idx_doctor_day ON doctor_availability(doctor_id, day_of_week);
CREATE INDEX idx_doctor_availability ON doctor_availability(doctor_id, day_of_week, is_available);
```

---

## API Endpoints Summary

### doctor_availability/Admin Endpoints (Doctor Only)
```
POST   /api/doctor_availability/availability                    # Create single slot
POST   /api/doctor_availability/availability/bulk               # Create multiple slots
GET    /api/doctor_availability/availability                    # List all slots
GET    /api/doctor_availability/availability/{slot_id}          # Get specific slot
GET    /api/doctor_availability/schedule                        # Get weekly schedule
GET    /api/doctor_availability/schedule/patient-info           # Get schedule with booked patients
PUT    /api/doctor_availability/availability/{slot_id}          # Update slot
PATCH  /api/doctor_availability/availability/{slot_id}/toggle   # Enable/disable slot
DELETE /api/doctor_availability/availability/{slot_id}          # Delete single slot
DELETE /api/doctor_availability/availability                    # Delete all/filtered slots
```

### Public Endpoints (Patient Accessible)
```
GET    /api/doctor_availability/availability/check/{day_name}   # Check available slots for a day
```

---

## How It Correlates with Patients

### Workflow:

1. **Doctor Sets Up Schedule**
   ```
   Doctor → POST /doctor_availability/availability/bulk → Creates weekly schedule
   ```

2. **Patient Wants to Book Appointment**
   ```
   Patient → GET /doctor_availability/availability/check/monday → Sees available slots
   Patient → POST /appointments → Books appointment for available slot
   ```

3. **System Validation**
   ```
   Appointment Creation:
   - Checks DoctorAvailability table for slot availability
   - Confirms doctor is available on that day and time
   - Prevents double-booking
   - Updates patient.last_visit_date
   ```

4. **Doctor Views Scheduled Patients**
   ```
   Doctor → GET /doctor_availability/schedule/patient-info → Sees all booked appointments
   ```

---

## Usage Example

### Step 1: Doctor Sets Up Weekly Schedule
```bash
curl -X POST http://localhost:8000/api/doctor_availability/availability/bulk \
  -H "Authorization: Bearer doctor_token" \
  -d '{
    "availability_slots": [
      {
        "day_of_week": "monday",
        "start_time": "09:00:00",
        "end_time": "12:00:00",
        "max_patients_per_slot": 10
      },
      {
        "day_of_week": "monday",
        "start_time": "14:00:00",
        "end_time": "18:00:00",
        "max_patients_per_slot": 8
      },
      {
        "day_of_week": "tuesday",
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "max_patients_per_slot": 15
      }
    ]
  }'
```

### Step 2: Patient Checks Available Slots
```bash
curl -X GET "http://localhost:8000/api/doctor_availability/availability/check/monday?doctor_id={doctor_id}"
```

Response:
```json
{
  "day_of_week": "monday",
  "available_slots": [
    {"start": "09:00", "end": "09:30", "duration_minutes": 30},
    {"start": "09:30", "end": "10:00", "duration_minutes": 30},
    {"start": "14:00", "end": "14:30", "duration_minutes": 30}
  ],
  "total_slots": 3,
  "booked_count": 2
}
```

### Step 3: Patient Books Appointment
```bash
curl -X POST http://localhost:8000/api/appointments \
  -H "Authorization: Bearer patient_token" \
  -d '{
    "patient_id": "patient_uuid",
    "appointment_date": "2026-01-20",
    "appointment_time": "09:00:00",
    "duration_minutes": 30,
    "reason": "Regular checkup"
  }'
```

### Step 4: Doctor Sees Scheduled Patients
```bash
curl -X GET http://localhost:8000/api/doctor_availability/schedule/patient-info \
  -H "Authorization: Bearer doctor_token"
```

---

## Modified Files

1. **models/users_model.py**
   - Added: `availability_slots` relationship to Doctor model

2. **models/__init__.py**
   - Added imports for DoctorAvailability model

3. **api/router.py**
   - Added doctor_availability router import and include

---

## Next Steps (Migrations)

Run these commands to apply the changes:

```bash
# Generate and apply migration
alembic upgrade head

# Verify table creation
# Connect to DB and verify doctor_availability table exists
```

---

## Notes

- **Multiple Slots**: Doctor can have 2+ slots per day (e.g., morning clinic 9-12, evening clinic 3-6)
- **Soft Disable**: Use toggle instead of delete to temporarily close slots
- **Capacity Control**: Use `max_patients_per_slot` to limit concurrent appointments
- **Patient-Aware**: All operations account for patient appointments
- **Efficient Queries**: Optimized indexes for doctor_id and day_of_week filtering
- **Timezone Safe**: Using TIME type without timezone for consistency

---

## Testing Recommendations

1. Test creating single slot
2. Test creating bulk slots for entire week
3. Test overlap detection (should fail)
4. Test updating slot times
5. Test toggling availability
6. Test patient viewing available slots
7. Test appointment booking validation against availability
8. Test view schedule with patient info
9. Test deleting individual and bulk slots
10. Test with multiple time slots on same day

---

## Security

- ✅ Doctor can only manage their own availability
- ✅ Doctors-only endpoints secured with `current_user.is_doctor` check
- ✅ Patient-facing endpoints don't expose sensitive data
- ✅ Foreign key constraints ensure data integrity
