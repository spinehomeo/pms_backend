# Doctor Availability - Real-World Usage Examples

## Scenario 1: New Doctor Setting Up Weekly Schedule

### Doctor wants to set their availability for the entire week:
- Monday: 9 AM - 12 PM (10 patients max), 3 PM - 6 PM (8 patients max)
- Tuesday: 9 AM - 5 PM (15 patients max)
- Wednesday: OFF (no availability)
- Thursday: 3 PM - 6 PM (8 patients max)
- Friday: 9 AM - 5 PM (15 patients max)
- Saturday: 10 AM - 2 PM (5 patients max, walk-in clinic)
- Sunday: OFF

### API Call:
```bash
curl -X POST http://localhost:8000/api/doctor_availability/availability/bulk \
  -H "Authorization: Bearer doctor_token" \
  -H "Content-Type: application/json" \
  -d '{
    "availability_slots": [
      {
        "day_of_week": "monday",
        "start_time": "09:00:00",
        "end_time": "12:00:00",
        "is_available": true,
        "max_patients_per_slot": 10,
        "notes": "Morning clinic"
      },
      {
        "day_of_week": "monday",
        "start_time": "15:00:00",
        "end_time": "18:00:00",
        "is_available": true,
        "max_patients_per_slot": 8,
        "notes": "Evening clinic"
      },
      {
        "day_of_week": "tuesday",
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "is_available": true,
        "max_patients_per_slot": 15,
        "notes": "Full day clinic"
      },
      {
        "day_of_week": "thursday",
        "start_time": "15:00:00",
        "end_time": "18:00:00",
        "is_available": true,
        "max_patients_per_slot": 8,
        "notes": "Evening clinic only"
      },
      {
        "day_of_week": "friday",
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "is_available": true,
        "max_patients_per_slot": 15,
        "notes": "Full day clinic"
      },
      {
        "day_of_week": "saturday",
        "start_time": "10:00:00",
        "end_time": "14:00:00",
        "is_available": true,
        "max_patients_per_slot": 5,
        "notes": "Walk-in clinic"
      }
    ]
  }'
```

### Response:
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
      "day_of_week": "monday",
      "start_time": "09:00:00",
      "end_time": "12:00:00",
      "is_available": true,
      "max_patients_per_slot": 10,
      "notes": "Morning clinic"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
      "day_of_week": "monday",
      "start_time": "15:00:00",
      "end_time": "18:00:00",
      "is_available": true,
      "max_patients_per_slot": 8,
      "notes": "Evening clinic"
    }
  ],
  "count": 6
}
```

---

## Scenario 2: Patient Checking Available Slots

### Patient wants to book an appointment on Monday:

```bash
curl -X GET "http://localhost:8000/api/doctor_availability/availability/check/monday?doctor_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer patient_token"
```

### Response (Monday has two time slots available):
```json
{
  "day_of_week": "monday",
  "available_slots": [
    {"start": "09:00", "end": "09:30", "duration_minutes": 30},
    {"start": "09:30", "end": "10:00", "duration_minutes": 30},
    {"start": "10:00", "end": "10:30", "duration_minutes": 30},
    {"start": "10:30", "end": "11:00", "duration_minutes": 30},
    {"start": "11:00", "end": "11:30", "duration_minutes": 30},
    {"start": "11:30", "end": "12:00", "duration_minutes": 30},
    {"start": "15:00", "end": "15:30", "duration_minutes": 30},
    {"start": "15:30", "end": "16:00", "duration_minutes": 30},
    {"start": "16:00", "end": "16:30", "duration_minutes": 30},
    {"start": "16:30", "end": "17:00", "duration_minutes": 30},
    {"start": "17:00", "end": "17:30", "duration_minutes": 30},
    {"start": "17:30", "end": "18:00", "duration_minutes": 30}
  ],
  "total_slots": 12,
  "booked_count": 0
}
```

### Patient books at 10:00 AM Monday:

```bash
curl -X POST http://localhost:8000/api/appointments \
  -H "Authorization: Bearer patient_token" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "550e8400-e29b-41d4-a716-446655440099",
    "appointment_date": "2026-01-20",
    "appointment_time": "10:00:00",
    "duration_minutes": 30,
    "reason": "Regular checkup",
    "consultation_type": "follow-up"
  }'
```

### Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440100",
  "patient_id": "550e8400-e29b-41d4-a716-446655440099",
  "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
  "appointment_date": "2026-01-20",
  "appointment_time": "10:00:00",
  "duration_minutes": 30,
  "status": "scheduled",
  "reason": "Regular checkup",
  "consultation_type": "follow-up",
  "created_at": "2026-01-17T10:30:00"
}
```

### Now check available slots again - one slot is booked:

```bash
curl -X GET "http://localhost:8000/api/doctor_availability/availability/check/monday?doctor_id=550e8400-e29b-41d4-a716-446655440000"
```

### Response (one slot now booked):
```json
{
  "day_of_week": "monday",
  "available_slots": [
    {"start": "09:00", "end": "09:30", "duration_minutes": 30},
    {"start": "09:30", "end": "10:00", "duration_minutes": 30},
    {"start": "10:30", "end": "11:00", "duration_minutes": 30},
    {"start": "11:00", "end": "11:30", "duration_minutes": 30},
    {"start": "11:30", "end": "12:00", "duration_minutes": 30},
    {"start": "15:00", "end": "15:30", "duration_minutes": 30},
    {"start": "15:30", "end": "16:00", "duration_minutes": 30},
    {"start": "16:00", "end": "16:30", "duration_minutes": 30},
    {"start": "16:30", "end": "17:00", "duration_minutes": 30},
    {"start": "17:00", "end": "17:30", "duration_minutes": 30},
    {"start": "17:30", "end": "18:00", "duration_minutes": 30}
  ],
  "total_slots": 11,
  "booked_count": 1
}
```

---

## Scenario 3: Doctor Views Weekly Schedule with Booked Patients

### Doctor wants to see their full schedule with patient appointments:

```bash
curl -X GET http://localhost:8000/api/doctor_availability/schedule/patient-info \
  -H "Authorization: Bearer doctor_token"
```

### Response:
```json
{
  "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
  "schedule": {
    "monday": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "start_time": "09:00",
        "end_time": "12:00",
        "is_available": true,
        "max_patients_per_slot": 10,
        "booked_count": 2,
        "patients_booked": [
          {
            "patient_name": "John Doe",
            "patient_phone": "+1234567890",
            "appointment_time": "09:00",
            "duration": 30,
            "status": "confirmed"
          },
          {
            "patient_name": "Jane Smith",
            "patient_phone": "+0987654321",
            "appointment_time": "10:00",
            "duration": 30,
            "status": "scheduled"
          }
        ],
        "notes": "Morning clinic"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "start_time": "15:00",
        "end_time": "18:00",
        "is_available": true,
        "max_patients_per_slot": 8,
        "booked_count": 1,
        "patients_booked": [
          {
            "patient_name": "Mike Johnson",
            "patient_phone": "+1111111111",
            "appointment_time": "15:30",
            "duration": 30,
            "status": "confirmed"
          }
        ],
        "notes": "Evening clinic"
      }
    ],
    "tuesday": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "start_time": "09:00",
        "end_time": "17:00",
        "is_available": true,
        "max_patients_per_slot": 15,
        "booked_count": 4,
        "patients_booked": [
          {
            "patient_name": "Sarah Davis",
            "patient_phone": "+2222222222",
            "appointment_time": "10:00",
            "duration": 30,
            "status": "confirmed"
          },
          {
            "patient_name": "Tom Wilson",
            "patient_phone": "+3333333333",
            "appointment_time": "11:00",
            "duration": 30,
            "status": "scheduled"
          }
        ],
        "notes": "Full day clinic"
      }
    ]
  }
}
```

---

## Scenario 4: Doctor Temporarily Disables Afternoon Clinic

### Doctor is sick and wants to disable Thursday afternoon clinic:

```bash
curl -X PATCH http://localhost:8000/api/doctor_availability/availability/550e8400-e29b-41d4-a716-446655440005/toggle \
  -H "Authorization: Bearer doctor_token"
```

### Response (slot now disabled but not deleted):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440005",
  "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
  "day_of_week": "thursday",
  "start_time": "15:00:00",
  "end_time": "18:00:00",
  "is_available": false,
  "max_patients_per_slot": 8,
  "notes": "Evening clinic only"
}
```

### Patient checks Thursday availability - no slots:

```bash
curl -X GET "http://localhost:8000/api/doctor_availability/availability/check/thursday?doctor_id=550e8400-e29b-41d4-a716-446655440000"
```

### Response (404 - no available slots):
```json
{
  "detail": "No available slots for thursday"
}
```

---

## Scenario 5: Doctor Updates Clinic Hours

### Doctor wants to extend morning clinic by 30 minutes:

```bash
curl -X PUT http://localhost:8000/api/doctor_availability/availability/550e8400-e29b-41d4-a716-446655440001 \
  -H "Authorization: Bearer doctor_token" \
  -H "Content-Type: application/json" \
  -d '{
    "end_time": "12:30:00",
    "max_patients_per_slot": 12,
    "notes": "Morning clinic - extended"
  }'
```

### Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "12:30:00",
  "is_available": true,
  "max_patients_per_slot": 12,
  "notes": "Morning clinic - extended"
}
```

---

## Scenario 6: Doctor Re-enables Disabled Slot

### Doctor feels better and wants to re-enable Thursday clinic:

```bash
curl -X PATCH http://localhost:8000/api/doctor_availability/availability/550e8400-e29b-41d4-a716-446655440005/toggle \
  -H "Authorization: Bearer doctor_token"
```

### Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440005",
  "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
  "day_of_week": "thursday",
  "start_time": "15:00:00",
  "end_time": "18:00:00",
  "is_available": true,
  "max_patients_per_slot": 8,
  "notes": "Evening clinic only"
}
```

---

## Scenario 7: Prevent Double-Booking

### Doctor tries to create overlapping slot:

```bash
curl -X POST http://localhost:8000/api/doctor_availability/availability \
  -H "Authorization: Bearer doctor_token" \
  -H "Content-Type: application/json" \
  -d '{
    "day_of_week": "monday",
    "start_time": "11:00:00",
    "end_time": "13:00:00",
    "max_patients_per_slot": 5
  }'
```

### Response (409 Conflict):
```json
{
  "detail": "Time slot overlaps with existing slot: 09:00 - 12:30"
}
```

---

## Scenario 8: Delete Entire Weekend

### Doctor decides to work Monday-Friday only and deletes Saturday:

```bash
curl -X DELETE "http://localhost:8000/api/doctor_availability/availability?day=saturday" \
  -H "Authorization: Bearer doctor_token"
```

### Response:
```json
{
  "message": "Deleted 1 availability slot(s) successfully"
}
```

### Or delete ALL availability slots:

```bash
curl -X DELETE http://localhost:8000/api/doctor_availability/availability \
  -H "Authorization: Bearer doctor_token"
```

### Response:
```json
{
  "message": "Deleted 6 availability slot(s) successfully"
}
```

---

## Scenario 9: View Single Slot Details

### Get details of a specific availability slot:

```bash
curl -X GET http://localhost:8000/api/doctor_availability/availability/550e8400-e29b-41d4-a716-446655440001 \
  -H "Authorization: Bearer doctor_token"
```

### Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "12:30:00",
  "is_available": true,
  "max_patients_per_slot": 12,
  "notes": "Morning clinic - extended"
}
```

---

## Scenario 10: List All Availability (with pagination)

### Get doctor's all availability slots with filtering:

```bash
curl -X GET "http://localhost:8000/api/doctor_availability/availability?skip=0&limit=10" \
  -H "Authorization: Bearer doctor_token"
```

### Filter by specific day:

```bash
curl -X GET "http://localhost:8000/api/doctor_availability/availability?day=monday&skip=0&limit=10" \
  -H "Authorization: Bearer doctor_token"
```

### Response:
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
      "day_of_week": "monday",
      "start_time": "09:00:00",
      "end_time": "12:30:00",
      "is_available": true,
      "max_patients_per_slot": 12,
      "notes": "Morning clinic - extended"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "doctor_id": "550e8400-e29b-41d4-a716-446655440000",
      "day_of_week": "monday",
      "start_time": "15:00:00",
      "end_time": "18:00:00",
      "is_available": true,
      "max_patients_per_slot": 8,
      "notes": "Evening clinic"
    }
  ],
  "count": 2
}
```

---

## Key Implementation Features

✅ **Multiple Time Slots Per Day**: Doctor can have morning and evening clinics
✅ **Automatic Overlap Detection**: System prevents scheduling conflicts
✅ **Patient Integration**: Checks availability when booking appointments
✅ **Soft Disable**: Use toggle instead of delete for temporary closures
✅ **Capacity Management**: Control max patients per slot
✅ **Full Auditability**: View all booked patients in each slot
✅ **Easy Pagination**: List and filter availability slots
✅ **Doctor-Only**: All doctor operations protected
✅ **Patient-Friendly**: Patients can easily check available slots

---

## Database Relationships

```
User (Doctor)
    ├── availability_slots (1-to-many) → DoctorAvailability
    └── appointments (1-to-many) → Appointment

Patient
    └── appointments (1-to-many) → Appointment

Appointment
    ├── doctor_id → User
    └── patient_id → Patient
```

When creating an appointment, the system:
1. Checks `DoctorAvailability` for slot availability
2. Validates doctor is available on that day/time
3. Prevents double-booking via appointment conflicts check
4. Updates patient's `last_visit_date`
