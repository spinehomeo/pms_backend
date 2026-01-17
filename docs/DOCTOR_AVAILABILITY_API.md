# Doctor Availability / doctor_availability API Documentation

## Overview
This API allows doctors to dynamically set their appointment availability for each day of the week. Doctors can have multiple time slots per day (e.g., 9-12 AM and 3-5 PM) and patients can check available slots before booking appointments.

## Base URL
```
/api/doctor_availability
```

---

## Endpoints

### 1. CREATE OPERATIONS

#### Create Single Availability Slot
```
POST /doctor_availability/availability
```

**Request:**
```json
{
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "is_available": true,
  "max_patients_per_slot": 10,
  "notes": "Morning clinic"
}
```

**Response:** `201 Created`
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

**Features:**
- Creates a single availability slot for a specific day
- Validates no time overlaps on the same day
- Supports multiple slots per day (e.g., morning and evening clinics)

---

#### Create Multiple Availability Slots (Bulk)
```
POST /doctor_availability/availability/bulk
```

**Request:**
```json
{
  "availability_slots": [
    {
      "day_of_week": "monday",
      "start_time": "09:00:00",
      "end_time": "12:00:00",
      "is_available": true,
      "max_patients_per_slot": 10
    },
    {
      "day_of_week": "monday",
      "start_time": "15:00:00",
      "end_time": "18:00:00",
      "is_available": true,
      "max_patients_per_slot": 8
    },
    {
      "day_of_week": "tuesday",
      "start_time": "09:00:00",
      "end_time": "17:00:00",
      "is_available": true,
      "max_patients_per_slot": 15
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "data": [
    { "id": "uuid", "day_of_week": "monday", ... },
    { "id": "uuid", "day_of_week": "monday", ... },
    { "id": "uuid", "day_of_week": "tuesday", ... }
  ],
  "count": 3
}
```

**Features:**
- Set up entire weekly schedule at once
- Useful for initial doctor_availability or bulk changes
- All slots validated before creation

---

### 2. READ OPERATIONS

#### Get All Availability Slots
```
GET /doctor_availability/availability
```

**Query Parameters:**
- `day` (optional): Filter by day of week (monday, tuesday, etc.)
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Max results (default: 100, max: 1000)

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "doctor_id": "uuid",
      "day_of_week": "monday",
      "start_time": "09:00:00",
      "end_time": "12:00:00",
      "is_available": true,
      "max_patients_per_slot": 10,
      "notes": null
    }
  ],
  "count": 1
}
```

---

#### Get Specific Availability Slot
```
GET /doctor_availability/availability/{slot_id}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "doctor_id": "uuid",
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "is_available": true,
  "max_patients_per_slot": 10,
  "notes": null
}
```

---

#### Get Weekly Schedule
```
GET /doctor_availability/schedule
```

**Response:** `200 OK`
```json
{
  "doctor_id": "uuid",
  "schedule": {
    "monday": [
      {
        "id": "uuid",
        "start_time": "09:00",
        "end_time": "12:00",
        "is_available": true,
        "max_patients_per_slot": 10,
        "notes": "Morning clinic"
      },
      {
        "id": "uuid",
        "start_time": "15:00",
        "end_time": "18:00",
        "is_available": true,
        "max_patients_per_slot": 8,
        "notes": "Evening clinic"
      }
    ],
    "tuesday": [
      {
        "id": "uuid",
        "start_time": "09:00",
        "end_time": "17:00",
        "is_available": true,
        "max_patients_per_slot": 15,
        "notes": null
      }
    ]
  }
}
```

**Features:**
- Get complete weekly schedule organized by day
- Shows all availability slots for the doctor
- Easy to display in calendar UI

---

#### Get Weekly Schedule with Patient Information
```
GET /doctor_availability/schedule/patient-info
```

**Response:** `200 OK`
```json
{
  "doctor_id": "uuid",
  "schedule": {
    "monday": [
      {
        "id": "uuid",
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
            "appointment_time": "09:30",
            "duration": 30,
            "status": "scheduled"
          }
        ],
        "notes": "Morning clinic"
      }
    ]
  }
}
```

**Features:**
- Shows which patients are booked in each slot
- Patient name, phone, and appointment details included
- Helps doctor see their schedule with patient context

---

### 3. UPDATE OPERATIONS

#### Update Availability Slot
```
PUT /doctor_availability/availability/{slot_id}
```

**Request (partial update):**
```json
{
  "start_time": "09:30:00",
  "end_time": "12:30:00",
  "max_patients_per_slot": 12,
  "notes": "Morning clinic - extended"
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "doctor_id": "uuid",
  "day_of_week": "monday",
  "start_time": "09:30:00",
  "end_time": "12:30:00",
  "is_available": true,
  "max_patients_per_slot": 12,
  "notes": "Morning clinic - extended"
}
```

**Features:**
- Partial updates supported
- Validates against overlapping slots
- Prevents invalid time ranges

---

#### Toggle Availability Status
```
PATCH /doctor_availability/availability/{slot_id}/toggle
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "doctor_id": "uuid",
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "is_available": false,  // Toggled from true to false
  "max_patients_per_slot": 10,
  "notes": null
}
```

**Features:**
- Quick enable/disable of slots without deleting
- Useful for temporary closures (sick leave, emergency, etc.)

---

### 4. DELETE OPERATIONS

#### Delete Specific Availability Slot
```
DELETE /doctor_availability/availability/{slot_id}
```

**Response:** `200 OK`
```json
{
  "message": "Availability slot deleted successfully"
}
```

---

#### Delete All Slots (Optional Filter by Day)
```
DELETE /doctor_availability/availability
```

**Query Parameters:**
- `day` (optional): Delete only slots for a specific day

**Response:** `200 OK`
```json
{
  "message": "Deleted 3 availability slot(s) successfully"
}
```

**Features:**
- Delete all slots at once
- Or delete only slots for a specific day
- Useful for schedule cleanup

---

### 5. PATIENT-FACING AVAILABILITY CHECK

#### Check Available Slots for a Specific Day
```
GET /doctor_availability/availability/check/{day_name}
```

**Query Parameters:**
- `doctor_id` (optional): Check availability for a specific doctor

**Path Parameters:**
- `day_name`: Day of week (monday, tuesday, wednesday, thursday, friday, saturday, sunday)

**Response:** `200 OK`
```json
{
  "day_of_week": "monday",
  "available_slots": [
    {
      "start": "09:00",
      "end": "09:30",
      "duration_minutes": 30
    },
    {
      "start": "10:00",
      "end": "10:30",
      "duration_minutes": 30
    },
    {
      "start": "15:00",
      "end": "15:30",
      "duration_minutes": 30
    }
  ],
  "total_slots": 3,
  "booked_count": 5
}
```

**Features:**
- Patients can check available slots before booking
- Shows 30-minute intervals
- Accounts for already booked appointments
- Considers multiple time slots per day

---

## Data Model

### DoctorAvailability Table
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | UUID | Yes | Primary key |
| `doctor_id` | UUID | Yes | Foreign key to `user.id` |
| `day_of_week` | Enum | Yes | Monday-Sunday |
| `start_time` | TIME | Yes | e.g., 09:00 |
| `end_time` | TIME | Yes | Must be > start_time |
| `is_available` | Boolean | No | Default: true |
| `max_patients_per_slot` | Integer | No | For capacity management |
| `notes` | String | No | Additional notes |

### Indexes
- `idx_doctor_day`: (doctor_id, day_of_week)
- `idx_doctor_availability`: (doctor_id, day_of_week, is_available)

---

## Integration with Patients

### How Patients Use This:

1. **View Available Slots**
   - Patient calls `GET /doctor_availability/availability/check/{day_name}?doctor_id={doctor_id}`
   - Gets list of available 30-minute slots

2. **Book Appointment**
   - Patient creates appointment via `POST /appointments`
   - System checks doctor's availability against this table
   - System validates appointment fits within available slots
   - System validates no time conflicts with existing appointments

3. **View Doctor Schedule**
   - Patient can see doctor's working hours (optional read-only view)
   - Helps patient plan when to call/visit

---

## Usage Examples

### Example 1: Setting Up a Complete Weekly Schedule

```bash
# Create availability for a whole week at once
curl -X POST http://localhost:8000/api/doctor_availability/availability/bulk \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "availability_slots": [
      {"day_of_week": "monday", "start_time": "09:00", "end_time": "12:00", "max_patients_per_slot": 10},
      {"day_of_week": "monday", "start_time": "14:00", "end_time": "18:00", "max_patients_per_slot": 8},
      {"day_of_week": "tuesday", "start_time": "09:00", "end_time": "17:00", "max_patients_per_slot": 15},
      {"day_of_week": "wednesday", "start_time": "09:00", "end_time": "12:00", "max_patients_per_slot": 10},
      {"day_of_week": "thursday", "start_time": "14:00", "end_time": "18:00", "max_patients_per_slot": 8},
      {"day_of_week": "friday", "start_time": "09:00", "end_time": "17:00", "max_patients_per_slot": 15},
      {"day_of_week": "saturday", "start_time": "10:00", "end_time": "14:00", "max_patients_per_slot": 5}
    ]
  }'
```

### Example 2: Disabling a Slot Temporarily

```bash
curl -X PATCH http://localhost:8000/api/doctor_availability/availability/{slot_id}/toggle \
  -H "Authorization: Bearer {token}"
```

### Example 3: Patient Checking Available Slots

```bash
curl -X GET http://localhost:8000/api/doctor_availability/availability/check/monday?doctor_id={doctor_id}
```

---

## Error Handling

| Status | Error | Cause |
|--------|-------|-------|
| 400 | Start time must be before end time | Invalid time range |
| 403 | Only doctors can create availability | Non-doctor user |
| 404 | Availability slot not found | Invalid slot ID |
| 409 | Time slot overlaps with existing slot | Conflicting times on same day |

---

## Validation Rules

1. **Time Validation**: start_time must be < end_time
2. **Overlap Prevention**: No two slots can overlap on the same day
3. **Doctor Authorization**: Doctors can only modify their own slots
4. **Day of Week**: Must be valid enum value (monday-sunday)

---

## Implementation Notes

- **Multiple Slots per Day**: Doctor can have different time slots on the same day (e.g., morning and evening clinics)
- **Appointment Integration**: When creating appointments, system automatically checks this availability table
- **Patient Correlation**: Booked appointments are cross-checked with available slots
- **Capacity Management**: `max_patients_per_slot` can be used to limit concurrent appointments
- **Soft Disable**: Use toggle endpoint to temporarily disable slots without deleting them
