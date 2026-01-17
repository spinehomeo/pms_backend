# Doctor Availability - Quick Reference Guide

## What Was Built?

A complete **Doctor Availability Management System** that allows doctors to:
- Set their working hours for each day of the week
- Support multiple time slots per day (e.g., 9AM-12PM and 3PM-6PM)
- Manage capacity per slot
- Toggle availability on/off
- View booked patients in their schedule
- Automatically integrate with appointment booking system

---

## Files Created/Modified

### New Files:
1. **models/doctor_availability_model.py** - Data model for availability
2. **routes/doctor_availability.py** - All API endpoints (13 endpoints)
3. **alembic/versions/20260117_add_doctor_availability.py** - Database migration

### Modified Files:
1. **models/users_model.py** - Added availability_slots relationship
2. **models/__init__.py** - Added model imports
3. **api/router.py** - Added doctor_availability router

### Documentation:
1. **docs/DOCTOR_AVAILABILITY_API.md** - Complete API reference
2. **docs/DOCTOR_AVAILABILITY_IMPLEMENTATION.md** - Implementation details
3. **docs/DOCTOR_AVAILABILITY_EXAMPLES.md** - Real-world usage examples

---

## Database Schema

```sql
CREATE TABLE doctor_availability (
    id UUID PRIMARY KEY,
    doctor_id UUID NOT NULL (FOREIGN KEY to user.id),
    day_of_week ENUM (monday-sunday),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT true,
    max_patients_per_slot INTEGER,
    notes VARCHAR
);

Indexes:
- idx_doctor_day(doctor_id, day_of_week)
- idx_doctor_availability(doctor_id, day_of_week, is_available)
```

---

## API Endpoints Summary

### Doctor doctor_availability (requires `current_user.is_doctor`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/doctor_availability/availability` | Create single slot |
| POST | `/api/doctor_availability/availability/bulk` | Create multiple slots |
| GET | `/api/doctor_availability/availability` | List all slots |
| GET | `/api/doctor_availability/availability/{slot_id}` | Get specific slot |
| GET | `/api/doctor_availability/schedule` | View weekly schedule |
| GET | `/api/doctor_availability/schedule/patient-info` | View schedule with booked patients |
| PUT | `/api/doctor_availability/availability/{slot_id}` | Update slot |
| PATCH | `/api/doctor_availability/availability/{slot_id}/toggle` | Enable/disable slot |
| DELETE | `/api/doctor_availability/availability/{slot_id}` | Delete single slot |
| DELETE | `/api/doctor_availability/availability` | Delete all/filtered slots |

### Patient Access (public)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/doctor_availability/availability/check/{day_name}` | Check available slots |

---

## Quick Start - Doctor Setting Up Schedule

### 1. Create availability for the week:
```bash
POST /api/doctor_availability/availability/bulk
Body:
{
  "availability_slots": [
    {"day_of_week": "monday", "start_time": "09:00", "end_time": "12:00", "max_patients_per_slot": 10},
    {"day_of_week": "monday", "start_time": "15:00", "end_time": "18:00", "max_patients_per_slot": 8},
    {"day_of_week": "tuesday", "start_time": "09:00", "end_time": "17:00", "max_patients_per_slot": 15}
  ]
}
```

### 2. View schedule:
```bash
GET /api/doctor_availability/schedule
```

### 3. View schedule with patients:
```bash
GET /api/doctor_availability/schedule/patient-info
```

### 4. Temporarily disable a slot:
```bash
PATCH /api/doctor_availability/availability/{slot_id}/toggle
```

### 5. Update slot details:
```bash
PUT /api/doctor_availability/availability/{slot_id}
Body: {"max_patients_per_slot": 12, "notes": "Extended clinic"}
```

---

## Patient Workflow

### 1. Check available slots:
```bash
GET /api/doctor_availability/availability/check/monday?doctor_id={doctor_id}

Response:
{
  "available_slots": [
    {"start": "09:00", "end": "09:30", "duration_minutes": 30},
    {"start": "09:30", "end": "10:00", "duration_minutes": 30},
    ...
  ],
  "total_slots": 10,
  "booked_count": 2
}
```

### 2. Book appointment:
```bash
POST /api/appointments
Body:
{
  "patient_id": "...",
  "appointment_date": "2026-01-20",
  "appointment_time": "09:00:00",
  "duration_minutes": 30,
  "reason": "Checkup"
}
```

System automatically:
- Checks availability against DoctorAvailability table
- Prevents double-booking
- Updates patient's last_visit_date

---

## Key Features

✅ **Multiple Slots Per Day**
- Morning clinic: 9 AM - 12 PM
- Evening clinic: 3 PM - 6 PM
- Both on the same day with no conflicts

✅ **Overlap Prevention**
- System prevents creating overlapping time slots
- Validates time ranges (start < end)

✅ **Soft Disable**
- Toggle availability without deleting
- Useful for temporary closures (sick, emergency, etc.)

✅ **Capacity Control**
- `max_patients_per_slot` limits concurrent appointments
- Optional field, defaults to no limit

✅ **Patient Integration**
- Booked appointments automatically excluded from available slots
- Shows 30-minute intervals within availability windows
- Displays booking counts

✅ **Schedule Visibility**
- Doctor sees full weekly schedule
- Doctor sees which patients booked in each slot
- Patient sees available slots before booking

✅ **Authorization**
- Doctors can only manage their own availability
- Patients see only non-sensitive availability data

---

## Validation Rules

| Rule | Behavior |
|------|----------|
| `start_time >= end_time` | Rejected with 400 error |
| Overlapping slots on same day | Rejected with 409 error |
| Non-doctor user accessing doctor endpoints | Rejected with 403 error |
| Invalid day of week | Rejected with 400 error |
| Doctor updating another doctor's slot | Rejected with 403 error |

---

## Enum Values

### DayOfWeek
- monday
- tuesday
- wednesday
- thursday
- friday
- saturday
- sunday

---

## Response Models

### DoctorAvailabilityPublic (single slot)
```json
{
  "id": "uuid",
  "doctor_id": "uuid",
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "is_available": true,
  "max_patients_per_slot": 10,
  "notes": "Morning clinic"
}
```

### DoctorAvailabilitiesPublic (list)
```json
{
  "data": [...],
  "count": 5
}
```

### DoctorScheduleResponse (weekly view)
```json
{
  "doctor_id": "uuid",
  "schedule": {
    "monday": [...],
    "tuesday": [...]
  }
}
```

### AvailableSlotCheck (patient view)
```json
{
  "day_of_week": "monday",
  "available_slots": [...],
  "total_slots": 10,
  "booked_count": 2
}
```

---

## Error Responses

| Status | Message |
|--------|---------|
| 400 | Start time must be before end time |
| 403 | Only doctors can create availability slots |
| 403 | Not authorized to access this slot |
| 404 | Availability slot not found |
| 404 | No available slots for {day_name} |
| 409 | Time slot overlaps with existing slot |

---

## Migration

After pulling these changes, run:

```bash
# Apply migration to create table
alembic upgrade head

# Verify table creation
psql -d your_db -c "SELECT * FROM doctor_availability;"
```

---

## Testing Checklist

- [ ] Doctor creates single slot
- [ ] Doctor creates multiple slots (bulk)
- [ ] Doctor tries to create overlapping slots (should fail)
- [ ] Doctor views all slots
- [ ] Doctor views weekly schedule
- [ ] Doctor views schedule with patient info
- [ ] Doctor updates slot time
- [ ] Doctor updates slot capacity
- [ ] Doctor toggles availability on/off
- [ ] Doctor deletes single slot
- [ ] Doctor deletes all slots
- [ ] Patient checks available slots
- [ ] Patient sees booked slots excluded
- [ ] Appointment creation validates availability
- [ ] Non-doctor cannot create availability
- [ ] Doctor cannot access another doctor's slots
- [ ] Verify database indexes are created
- [ ] Verify migration runs without errors

---

## Related Files to Review

1. [appointments.py](routes/appointments.py) - Uses availability for validation
2. [appointments_model.py](models/appointments_model.py) - Appointment schema
3. [patients_model.py](models/patients_model.py) - Patient model
4. [users_model.py](models/users_model.py) - Doctor/User model

---

## Notes

- All timestamps use `TIME` type without timezone
- Appointment durations in minutes (default 30)
- System calculates 30-minute intervals for available slots
- Doctor availability is weekly, repeating pattern
- Specific unavailable dates would need separate "blackout dates" table (future enhancement)
- Capacity limits are per time slot, not per day
- Multiple doctors can have different schedules (independent records)

---

## Support & Troubleshooting

**Issue**: Overlap error when creating valid slots
- Ensure times don't overlap
- Check existing slots: `GET /api/doctor_availability/availability?day=monday`

**Issue**: Patient can't see available slots
- Verify doctor created availability for that day
- Check `is_available` is true
- Verify no conflicting appointments

**Issue**: Migration fails
- Check doctor_availability table doesn't exist
- Verify dayofweek enum isn't already defined
- Check database permissions

**Issue**: Doctor can't create availability
- Verify user has `is_doctor=true`
- Verify authentication token is valid
- Check error details in response

---

## Next Steps (Future Enhancements)

1. Add "Blackout Dates" for specific unavailable dates
2. Add recurring holidays
3. Add buffer time between appointments
4. Add patient cancellation policies
5. Add appointment reminders
6. Add auto-confirm based on appointment type
7. Add availability templates for quick doctor_availability
8. Add availability import/export
9. Add availability analytics/reporting
10. Add timezone support per doctor
