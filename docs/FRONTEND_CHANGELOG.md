# Backend Changes - Frontend Developer Guide

## Overview
Backend has been updated with doctor availability scheduling system and enhanced patient management.

---

## 1. Doctor Availability Management

**Base URL:** `/api/doctor_availability/`

### Endpoints

#### Create Availability
```
POST /
Body: {
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "is_available": true,
  "max_patients_per_slot": 10,
  "notes": "Morning clinic"
}
Response: DoctorAvailabilityPublic
```

#### Create Multiple Slots (Bulk)
```
POST /bulk
Body: {
  "availability_slots": [
    {"day_of_week": "monday", "start_time": "09:00:00", "end_time": "12:00:00"},
    {"day_of_week": "monday", "start_time": "14:00:00", "end_time": "17:00:00"}
  ]
}
```

#### Get All Slots
```
GET /?day=monday&skip=0&limit=100
```

#### Get Weekly Schedule
```
GET /schedule
Returns: Doctor's complete weekly schedule organized by day
```

#### Get Schedule with Patient Info
```
GET /schedule/patient-info
Shows which patients are booked in each slot
```

#### Update Slot
```
PUT /{slot_id}
Body: Partial update fields
```

#### Toggle Slot Status
```
PATCH /{slot_id}/toggle
Enable/disable slot without deleting
```

#### Delete Slot
```
DELETE /{slot_id}
DELETE / (delete all, optional: ?day=monday)
```

#### Check Available Slots (Patient-facing)
```
GET /check/{day_name}
Query: ?doctor_id={uuid}
Returns: Available 30-minute slots for a specific day
```

---

## 2. Patient Model Changes

### New Fields Added
- `cnic` (String, required, unique) - National ID card
- `phone` (String, required) - Was optional, now required
- `phone_secondary` (String, optional)
- `residential_address` (String, optional) - Replaces `address`
- `postal_address` (String, optional)
- `city` (String, optional)
- `payment_status` (Boolean) - Track if paid/unpaid
- `current_medications` (String, optional)
- `is_active` (Boolean) - Soft delete flag

### Enhanced Endpoints

#### GET /patients/
**New Query Filters:**
- `?search=` - Now searches: name, phone, email, cnic, city
- `?payment_status=true/false` - Filter by payment status
- `?gender=male/female/other/child` - Filter by gender

#### POST /patients/
**New Validations:**
- `cnic` required and unique per doctor
- `phone` required

#### GET /patients/{id}/stats
**Enhanced Response:**
```json
{
  "patient_id": "...",
  "total_cases": 5,
  "total_appointments": 12,
  "last_visit_date": "2026-01-17",
  "age": 35,
  "payment_status": true,
  "gender": "male",
  "city": "Karachi"
}
```

---

## 3. Integration: Appointments + Availability

When creating an appointment:
1. System checks doctor's `doctor_availability` slots
2. Validates appointment fits within available time
3. Prevents overlapping bookings
4. Updates patient's `last_visit_date`

---

## 4. Days of Week Format

**Valid values (case-insensitive):**
- `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`

---

## 5. Example Workflow

### Doctor Setup
1. POST `/doctor_availability/bulk` - Set weekly schedule
2. GET `/doctor_availability/schedule` - View complete schedule

### Patient Booking
1. GET `/doctor_availability/check/monday?doctor_id={id}` - See available slots
2. POST `/appointments/` - Book appointment in available slot

### Doctor View
1. GET `/doctor_availability/schedule/patient-info` - See who's booked

### Payment Tracking
1. Filter patients: GET `/patients/?payment_status=false` - Unpaid patients
2. Update patient: PUT `/patients/{id}` with `payment_status: true`

---

## 6. Error Codes

| Code | Meaning |
|------|---------|
| 400 | Invalid request (e.g., start_time >= end_time) |
| 403 | Unauthorized (non-doctor trying to access) |
| 404 | Resource not found |
| 409 | Time slot conflicts/overlaps |

---

## 7. Time Format

All times in `HH:MM:SS` format (24-hour):
- `09:00:00` = 9 AM
- `17:30:00` = 5:30 PM

---

## Migration Status

Migrations applied:
- `20260117_doctor_availability` - Doctor availability table
- `20260117_patient_schema` - Patient field updates

Run: `uv run alembic upgrade heads`
