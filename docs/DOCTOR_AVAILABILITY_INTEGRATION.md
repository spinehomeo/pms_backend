# How Doctor Availability Integrates with Appointments

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCTOR AVAILABILITY SYSTEM                        │
└─────────────────────────────────────────────────────────────────────┘

                              Doctor
                                │
                    ┌───────────┴───────────┐
                    │                       │
            Sets Availability         Views Schedule
            (doctor_availability Routes)           (doctor_availability Routes)
                    │                       │
            ┌───────▼───────┐      ┌────────▼────────┐
            │ DoctorAvail.  │      │ DoctorAvail.    │
            │ CRUD OPS      │      │ + Appointments  │
            └───────┬───────┘      └────────┬────────┘
                    │                       │
            Create/Update/Delete    View with Patients
            Availability Slots      Booked


┌─────────────────────────────────────────────────────────────────────┐
│                       PATIENT BOOKING FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

    Patient Wants to Book Appointment
                    │
                    ▼
    Check Available Slots
    GET /doctor_availability/availability/check/{day}
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ Query DoctorAvailability Table   │
    │ Filter: day_of_week              │
    │ Filter: is_available = true      │
    │ Filter: time ranges              │
    └──────────────────────────────────┘
                    │
                    ▼
    Calculate 30-min Sub-slots
    for Available Time Slots
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ Query Appointments Table         │
    │ Filter: doctor_id, date, status  │
    │ Exclude Booked Times             │
    └──────────────────────────────────┘
                    │
                    ▼
    Display Available Slots to Patient
    (9:00, 9:30, 10:00, 10:30, ...)
                    │
                    ▼
    Patient Selects Slot
    and Books Appointment
    POST /appointments
                    │
                    ▼
    System Validation:
    1. Check DoctorAvailability
    2. Verify doctor available on date/time
    3. Check Appointments for conflicts
    4. Prevent double-booking
                    │
        ┌───────────┴──────────────┐
        │                          │
    ✓ Valid                    ✗ Conflict
        │                          │
        ▼                          ▼
    Create                    Reject (409)
    Appointment               Tell patient:
    Update Patient            "Slot already
    last_visit_date           booked"
```

---

## Detailed Data Flow

### Step 1: Doctor Sets Up Availability

**doctor_availability Route Creates:**
```python
DoctorAvailability(
    doctor_id = "doc_001",
    day_of_week = "monday",
    start_time = 09:00,
    end_time = 12:00,
    is_available = true,
    max_patients_per_slot = 10
)
```

**Database:**
```sql
INSERT INTO doctor_availability (id, doctor_id, day_of_week, start_time, end_time, is_available, max_patients_per_slot)
VALUES ('slot_001', 'doc_001', 'monday', '09:00', '12:00', true, 10);
```

---

### Step 2: Patient Checks Available Slots

**Patient Query:**
```
GET /api/doctor_availability/availability/check/monday?doctor_id=doc_001
```

**System Query 1: Get Doctor's Availability**
```sql
SELECT * FROM doctor_availability
WHERE doctor_id = 'doc_001'
  AND day_of_week = 'monday'
  AND is_available = true
ORDER BY start_time ASC;

Result: [09:00-12:00, 15:00-18:00]
```

**System Query 2: Get Booked Appointments for Next Monday**
```sql
SELECT * FROM appointment
WHERE doctor_id = 'doc_001'
  AND appointment_date = '2026-01-20' (next Monday)
  AND status IN ('scheduled', 'confirmed')
ORDER BY appointment_time ASC;

Result: 
- 09:00-09:30 (John Doe)
- 10:00-10:30 (Jane Smith)
- 15:30-16:00 (Mike Johnson)
```

**System Calculation:**
```
Available Slots from 09:00-12:00:
- 09:00-09:30: BOOKED by John
- 09:30-10:00: AVAILABLE ✓
- 10:00-10:30: BOOKED by Jane
- 10:30-11:00: AVAILABLE ✓
- 11:00-11:30: AVAILABLE ✓
- 11:30-12:00: AVAILABLE ✓

Available Slots from 15:00-18:00:
- 15:00-15:30: AVAILABLE ✓
- 15:30-16:00: BOOKED by Mike
- 16:00-16:30: AVAILABLE ✓
- 16:30-17:00: AVAILABLE ✓
- 17:00-17:30: AVAILABLE ✓
- 17:30-18:00: AVAILABLE ✓
```

**Response to Patient:**
```json
{
  "day_of_week": "monday",
  "available_slots": [
    {"start": "09:30", "end": "10:00", "duration_minutes": 30},
    {"start": "10:30", "end": "11:00", "duration_minutes": 30},
    {"start": "11:00", "end": "11:30", "duration_minutes": 30},
    {"start": "11:30", "end": "12:00", "duration_minutes": 30},
    {"start": "15:00", "end": "15:30", "duration_minutes": 30},
    {"start": "16:00", "end": "16:30", "duration_minutes": 30},
    {"start": "16:30", "end": "17:00", "duration_minutes": 30},
    {"start": "17:00", "end": "17:30", "duration_minutes": 30},
    {"start": "17:30", "end": "18:00", "duration_minutes": 30}
  ],
  "total_slots": 9,
  "booked_count": 3
}
```

---

### Step 3: Patient Books an Appointment

**Patient Request:**
```json
POST /api/appointments
{
  "patient_id": "pat_123",
  "appointment_date": "2026-01-20",
  "appointment_time": "10:30:00",
  "duration_minutes": 30,
  "reason": "Follow-up checkup",
  "consultation_type": "follow-up"
}
```

**System Validations:**

**Validation 1: Check DoctorAvailability**
```python
# In create_appointment route
doctor_availability = session.exec(
    select(DoctorAvailability).where(
        and_(
            DoctorAvailability.doctor_id == current_user.id,
            DoctorAvailability.day_of_week == get_day_of_week('2026-01-20'),  # monday
            DoctorAvailability.is_available == true
        )
    )
).all()

# Result: Found availability for 09:00-12:00 and 15:00-18:00
# Appointment time 10:30 falls within 09:00-12:00 ✓
```

**Validation 2: Check for Appointment Conflicts**
```python
# Check if appointment overlaps with existing appointments
conflicting = session.exec(
    select(Appointment).where(
        and_(
            Appointment.doctor_id == doc_id,
            Appointment.appointment_date == '2026-01-20',
            Appointment.status.in_(['scheduled', 'confirmed']),
            # Check time overlap
            or_(
                # New appt starts during existing
                and_(
                    10:30 >= Appointment.appointment_time,
                    10:30 < (Appointment.appointment_time + duration)
                ),
                # Existing starts during new appt
                and_(
                    Appointment.appointment_time >= 10:30,
                    Appointment.appointment_time < 11:00
                )
            )
        )
    )
).all()

# Result: No conflicts ✓
```

**Validation 3: Create Appointment**
```sql
INSERT INTO appointment (
    id, patient_id, doctor_id, appointment_date, 
    appointment_time, duration_minutes, status, created_at
)
VALUES (
    'appt_456', 'pat_123', 'doc_001', '2026-01-20',
    '10:30', 30, 'scheduled', NOW()
);

UPDATE patient
SET last_visit_date = '2026-01-20'
WHERE id = 'pat_123';
```

---

### Step 4: Doctor Views Schedule with Patients

**Doctor Query:**
```
GET /api/doctor_availability/schedule/patient-info
```

**System Query 1: Get All Availability Slots**
```sql
SELECT * FROM doctor_availability
WHERE doctor_id = 'doc_001'
ORDER BY day_of_week, start_time;
```

**System Query 2: For Each Slot, Get Booked Appointments**
```python
for availability_slot in availability_slots:
    appointments = session.exec(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == calculated_date,
                Appointment.status.in_(['scheduled', 'confirmed'])
            )
        )
    ).all()
    
    # Filter appointments that fall within this slot's time range
    patients_in_slot = [
        appt for appt in appointments
        if (appt.appointment_time >= slot.start_time 
            and appt.appointment_time < slot.end_time)
    ]
```

**Response:**
```json
{
  "doctor_id": "doc_001",
  "schedule": {
    "monday": [
      {
        "id": "slot_001",
        "start_time": "09:00",
        "end_time": "12:00",
        "is_available": true,
        "booked_count": 3,
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
          },
          {
            "patient_name": "Alice Brown",
            "patient_phone": "+5555555555",
            "appointment_time": "10:30",
            "duration": 30,
            "status": "scheduled"
          }
        ]
      }
    ]
  }
}
```

---

## SQL Integration Points

### Table: doctor_availability
```sql
CREATE TABLE doctor_availability (
    id UUID PRIMARY KEY,
    doctor_id UUID NOT NULL REFERENCES user(id),
    day_of_week ENUM('monday', ..., 'sunday'),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT true,
    max_patients_per_slot INTEGER,
    notes VARCHAR,
    INDEX idx_doctor_day(doctor_id, day_of_week),
    INDEX idx_doctor_availability(doctor_id, day_of_week, is_available)
);
```

### Joins with Other Tables

**DoctorAvailability → User (Doctor)**
```sql
SELECT * FROM doctor_availability da
JOIN user u ON da.doctor_id = u.id
WHERE u.is_doctor = true;
```

**DoctorAvailability → Appointment (Checking Conflicts)**
```sql
SELECT * FROM appointment a
WHERE a.doctor_id IN (
    SELECT doctor_id FROM doctor_availability
    WHERE day_of_week = 'monday'
)
AND a.appointment_date = '2026-01-20'
AND a.status IN ('scheduled', 'confirmed');
```

---

## Performance Optimization

### Indexes Created
```sql
-- Quick lookup by doctor and day
CREATE INDEX idx_doctor_day 
ON doctor_availability(doctor_id, day_of_week);

-- Quick lookup for available slots
CREATE INDEX idx_doctor_availability 
ON doctor_availability(doctor_id, day_of_week, is_available);
```

### Query Performance

**Worst Case:** 100,000 doctors × 7 days = 700,000 rows
- With index: O(log n) = ~20 comparisons
- Without index: O(n) = 350,000 comparisons

### Caching Opportunity (Future)
```python
# Cache doctor availability (rarely changes)
@cache(ttl=3600)  # 1 hour
def get_doctor_availability(doctor_id: uuid.UUID):
    return session.exec(
        select(DoctorAvailability)
        .where(DoctorAvailability.doctor_id == doctor_id)
    ).all()
```

---

## Edge Cases Handled

### Case 1: Doctor Has No Availability Set
**Patient checks slots:**
```
GET /doctor_availability/availability/check/monday?doctor_id=no_availability_doc

Response: 404 - "No available slots for monday"
```

### Case 2: Doctor Disables a Slot
**Before:** 10 available slots
```
PATCH /doctor_availability/availability/{slot_id}/toggle

After:** 5 available slots
```

### Case 3: All Slots Booked
**No availability:**
```json
{
  "available_slots": [],
  "total_slots": 0,
  "booked_count": 6
}
```

### Case 4: Overlapping Availability
**System prevents:**
```
POST /doctor_availability/availability (9-12 and 11-2 overlap)

Response: 409 - "Time slot overlaps with existing slot: 09:00 - 12:00"
```

### Case 5: Past Appointments Still Show
**Historical data:**
```sql
-- System doesn't filter out past appointments
-- Only filters by status (scheduled, confirmed)
-- This allows historical view of past appointments
```

---

## Data Integrity Constraints

### Foreign Keys
```sql
ALTER TABLE doctor_availability
ADD FOREIGN KEY (doctor_id) REFERENCES user(id);
```

### Unique Constraints
No unique constraint on (doctor_id, day_of_week) - allows multiple slots per day ✓

### Check Constraints (Recommended Future Addition)
```sql
ALTER TABLE doctor_availability
ADD CHECK (start_time < end_time);

ALTER TABLE doctor_availability
ADD CHECK (max_patients_per_slot IS NULL OR max_patients_per_slot > 0);
```

---

## API Call Sequence Diagram

```
Patient               Doctor              Backend              Database
   │                   │                    │                    │
   ├─── Check Slots ──────────────────────>│                    │
   │                                        ├─ Query Availability ─>│
   │                                        │<─ Availability Data ──│
   │                                        │                       │
   │                                        ├─ Query Appointments ─>│
   │                                        │<─ Booked Appts ───────│
   │                                        │                       │
   │                                        ├─ Calculate Sub-slots ─│
   │<──── Available Slots ────────────────<┤                    │
   │                                        │                    │
   ├─── Book Appointment (10:30) ────────>│                    │
   │                                        ├─ Validate Availability│
   │                                        ├─ Check Conflicts ────>│
   │                                        │<─ No Conflicts ────────│
   │                                        │                       │
   │                                        ├─ Create Appointment ─>│
   │<──── Appointment Confirmed ────────<┤<─ Success ─────────────│
   │                                        │                       │
                                            │                    │
Doctor                                       ├─ Get Schedule ────>│
   │                                        │<─ All Slots + Appts ──│
   ├────── View Schedule ──────────────────>│                       │
   │<────── Schedule View ──────────────────┤                       │
   │                                        │                    │
```

---

## Summary

The Doctor Availability system integrates seamlessly with appointments:

1. **Doctors** set their availability via doctor_availability endpoints
2. **Patients** check available slots, which considers:
   - Doctor's availability windows
   - Already booked appointments
   - Time calculations (30-min intervals)
3. **Appointment Creation** validates against:
   - Doctor availability table
   - Existing appointments
   - Time conflicts
4. **Doctors** see full schedule with patient details

All operations are optimized with database indexes and validated at multiple levels to maintain data integrity.
