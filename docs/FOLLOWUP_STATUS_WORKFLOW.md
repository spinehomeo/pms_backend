# Follow-Up Status Workflow Guide

## Overview
Follow-ups are treated as **next appointments** in the PMS system. They follow a status lifecycle similar to appointments, tracking the progression from initial scheduling through payment confirmation to case closure.

---

## Status Categories

### 1. **Scheduled** (Initial State)
- **When set:** Automatically when a follow-up is created
- **Meaning:** Follow-up has been scheduled but payment is not yet confirmed
- **Typical duration:** Until payment is confirmed or the appointment date arrives
- **Transitions to:** `Confirmed` (payment received), `Cancelled` (doctor cancels)

### 2. **Confirmed** (Post-Payment)
- **When set:** When payment for the follow-up has been confirmed
- **Meaning:** Patient has paid for the follow-up appointment and it's locked in
- **Typical duration:** Until follow-up is completed or case is closed
- **Transitions to:** `Completed` (follow-up conducted), `Case Closed` (case ends), `Patient Left` (patient drops out)
- **API Endpoint:** `POST /followups/{followup_id}/confirm-payment`

### 3. **Completed** (Service Rendered)
- **When set:** After the follow-up appointment is conducted
- **Meaning:** The follow-up interaction is finished; doctor has documented findings
- **Typical duration:** Final state for a successful follow-up
- **Transitions to:** No further transitions (terminal state)

### 4. **Case Closed** (Treatment Complete)
- **When set:** When the case/treatment is concluded via a follow-up
- **Meaning:** Patient's treatment plan is complete; no further appointments needed
- **Typical duration:** Final state for completed case
- **Related updates:** Associated case status automatically updated to `closed`
- **API Endpoint:** `POST /followups/{followup_id}/close-case`

### 5. **Patient Left** (Patient Dropout)
- **When set:** When patient doesn't respond or is unwilling to continue treatment
- **Meaning:** Patient has discontinued treatment; follow-up will not proceed
- **Typical duration:** Final state for discontinued treatment
- **Transitions to:** No further transitions (terminal state)

### 6. **Cancelled** (Not Proceeding)
- **When set:** If the follow-up is cancelled before payment confirmation
- **Meaning:** The scheduled follow-up will not proceed
- **Typical duration:** Final state for cancelled follow-up
- **Transitions to:** No further transitions (terminal state)

---

## Status Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Follow-Up Lifecycle                       │
└─────────────────────────────────────────────────────────────┘

  CREATE FOLLOW-UP
        │
        ▼
    ┌─────────────┐
    │ SCHEDULED   │  ◄─── Initial state (payment pending)
    └─────┬─────┬─┘
          │     │
       [Payment Confirmed]  [Doctor Cancels]
          │     │
          ▼     ▼
    ┌──────────┐ ┌──────────────┐
    │CONFIRMED │ │  CANCELLED   │  (Terminal)
    └─┬──────┬─┘ └──────────────┘
      │      │
   [Patient Drops Out]  [Follow-up Done]  [Case Ends]
      │      │      │
      ▼      ▼      ▼
  ┌────────────┐ ┌──────────┐ ┌──────────────┐
  │PATIENT_LEFT│ │COMPLETED │ │ CASE_CLOSED  │  (Terminal)
  └────────────┘ └──────────┘ └──────────────┘
     (Terminal)    (Terminal)
```

---

## Database Fields

### Follow-Up Model Updates

**File:** [models/followups_model.py](../models/followups_model.py)

#### New Fields
- **`payment_confirmed`** (Boolean)
  - Default: `False`
  - Set to `True` when `POST /followups/{id}/confirm-payment` is called
  
- **`payment_confirmed_date`** (DateTime, optional)
  - Default: `None`
  - Populated with current timestamp when payment is confirmed
  - Used for audit trail and reporting

#### Existing Field (Enhanced)
- **`status`** (String)
  - Default: `"scheduled"`
  - Valid values: `scheduled`, `confirmed`, `completed`, `case_closed`, `cancelled`
  - From enum: `FollowupStatus`

---

## API Endpoints

### 1. Create Follow-Up
**Endpoint:** `POST /followups/`

```python
class FollowUpCreate(SQLModel):
    case_id: uuid.UUID
    prescription_id: uuid.UUID
    # ... other fields
    status: Optional[str] = Field(default="scheduled")  # Always starts as 'scheduled'
    payment_confirmed: Optional[bool] = Field(default=False)
    # ... form fields (subjective_improvement, objective_findings, etc.)
```

**Default behavior:** New follow-ups are created with:
- `status = "scheduled"`
- `payment_confirmed = False`
- `payment_confirmed_date = None`

---

### 2. Confirm Follow-Up Payment
**Endpoint:** `POST /followups/{followup_id}/confirm-payment`

**Purpose:** Mark a follow-up as confirmed after payment is received

**Request:** No body required

**Response:** Updated `FollowUpPublic` with:
- `status = "confirmed"`
- `payment_confirmed = True`
- `payment_confirmed_date = <datetime.now()>`

**Validation:**
- User must be a doctor
- Follow-up must exist and belong to the doctor
- `confirmed` status must be enabled in doctor's preferences

**Error codes:**
- `403`: Not authorized (user is not a doctor)
- `404`: Follow-up not found
- `400`: Status not available for doctor's account

```bash
# Example curl request
curl -X POST "http://localhost:8000/followups/{followup_id}/confirm-payment" \
  -H "Authorization: Bearer <token>"
```

---

### 3. Close Case from Follow-Up
**Endpoint:** `POST /followups/{followup_id}/close-case`

**Purpose:** Mark follow-up as case closed and close associated patient case

**Request:** No body required

**Response:** Updated `FollowUpPublic` with:
- `status = "case_closed"`
- Associated `PatientCase.status = "closed"`

**Side Effects:**
- Updates the associated case status to `closed`
- Marks the follow-up as the final interaction

**Validation:**
- User must be a doctor
- Follow-up must exist and belong to the doctor
- Both `case_closed` and `closed` statuses must be enabled
- Associated case will be updated automatically

**Error codes:**
- `403`: Not authorized (user is not a doctor)
- `404`: Follow-up not found
- `400`: Status not available for doctor's account

```bash
# Example curl request
curl -X POST "http://localhost:8000/followups/{followup_id}/close-case" \
  -H "Authorization: Bearer <token>"
```

---

### 4. Update Follow-Up Status
**Endpoint:** `PUT /followups/{followup_id}`

**Purpose:** Manually update follow-up details including status

**Request:**
```python
class FollowUpUpdate(SQLModel):
    # ... optional form fields
    status: Optional[str] = Field(None)  # Can set to any enum value
    payment_confirmed: Optional[bool] = None
```

**Response:** Updated `FollowUpPublic`

**Validation:**
- User must be a doctor
- Follow-up must exist and belong to the doctor
- Status value must be valid in `FollowupStatus` enum

```bash
# Example: Manually mark as completed
curl -X PUT "http://localhost:8000/followups/{followup_id}" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

---

## Enum Configuration

### FollowupStatus Enum (System)
**File:** [scripts/seed_enums.py](../scripts/seed_enums.py)

Seeded enum options:
```python
"FollowupStatus": [
    ("scheduled", "Scheduled"),
    ("confirmed", "Payment Confirmed"),
    ("completed", "Completed"),
    ("case_closed", "Case Closed"),
    ("patient_left", "Patient Left"),
    ("cancelled", "Cancelled"),
]
```

All statuses are system-level and apply to all doctors.
Doctors can enable/disable options via admin preferences if needed.

---

## Typical Workflow Scenarios

### Scenario 1: Standard Follow-Up (Payment → Completion)
```
1. Doctor creates follow-up
   → status = "scheduled", payment_confirmed = False
   
2. Patient makes payment
   → Doctor calls POST /followups/{id}/confirm-payment
   → status = "confirmed", payment_confirmed = True, payment_confirmed_date = timestamp
   
3. Follow-up appointment is conducted, doctor documents findings
   → Doctor calls PUT /followups/{id} with status="completed"
   → status = "completed"
```

### Scenario 2: Follow-Up Ending Case
```
1. Doctor creates follow-up
   → status = "scheduled", payment_confirmed = False
   
2. Patient makes payment
   → Doctor calls POST /followups/{id}/confirm-payment
   → status = "confirmed", payment_confirmed = True
   
3. Follow-up appointment conducted, case is concluded
   → Doctor calls POST /followups/{id}/close-case
   → status = "case_closed"
   → Associated PatientCase.status = "closed"
```

### Scenario 3: Patient Drops Out
```
1. Doctor creates follow-up
   → status = "scheduled", payment_confirmed = False
   
2. Patient makes payment
   → Doctor calls POST /followups/{id}/confirm-payment
   → status = "confirmed", payment_confirmed = True
   
3. Patient doesn't respond or is unwilling to continue
   → Doctor calls PUT /followups/{id} with status="patient_left"
   → status = "patient_left"
   → (No further transitions, treatment discontinued)
```

### Scenario 4: Cancelled Follow-Up
```
1. Doctor creates follow-up
   → status = "scheduled", payment_confirmed = False
   
2. Patient doesn't proceed or schedule changes
   → Doctor calls PUT /followups/{id} with status="cancelled"
   → status = "cancelled"
   → (No further transitions)
```

---

## Frontend Integration Points

### 1. Follow-Up List View
Display follow-ups with status badges:
- **Scheduled**: Yellow/Orange badge - "Payment Pending"
- **Confirmed**: Green badge - "Payment Confirmed"
- **Completed**: Blue badge - "Completed"
- **Case Closed**: Gray badge - "Case Closed"
- **Patient Left**: Red badge - "Patient Dropped Out"
- **Cancelled**: Dark Red badge - "Cancelled"

### 2. Follow-Up Action Buttons
Conditionally show based on current status:
- **Scheduled**: Show "Confirm Payment" button → calls `POST /confirm-payment`
- **Confirmed**: Show "Mark Complete" button + "Close Case" button + "Patient Left" button
- **Completed/Case Closed/Patient Left/Cancelled**: Show "View Details" only

### 3. Case View Integration
- When case status is `closed`, information comes from follow-ups
- Show final follow-up with `case_closed` status
- Highlight the closing follow-up record

### 4. Payment Workflow Integration
- Can integrate with finance module to track payment
- `payment_confirmed_date` provides audit trail
- Can generate payment reports by status

---

## Migration Notes

### For Existing Databases
A migration has been created to add two new fields to the `follow_up` table:

**File:** [alembic/versions/20260305_add_followup_payment_confirmation.py](../alembic/versions/20260305_add_followup_payment_confirmation.py)

**Changes:**
- Adds `payment_confirmed` (Boolean, default=False)
- Adds `payment_confirmed_date` (DateTime, nullable)

**How to apply:**
```bash
uv run alembic upgrade head
```

Existing follow-ups will be:
- Migrated with `payment_confirmed = False` (default)
- `payment_confirmed_date = NULL` (no payment date yet)
- `status` field unchanged (whatever it was)

---

## Validation & Error Handling

### Status Validation
All status changes are validated against the `FollowupStatus` enum:
- Doctor must have the status enabled in their preferences
- Invalid statuses return `400 Bad Request`

### Payment Confirmation Rules
- Can only confirm payment once (idempotent - calling twice is safe)
- Sets timestamp automatically - no manual timestamp needed
- User must be the doctor who created the follow-up

### Case Closure Rules
- Can close case from any follow-up, not just the last one
- Automatically updates associated case to `closed` status
- Both statuses must be available to the doctor

---

## Reporting & Metrics

### Recommended Queries

**Pending Payment Follow-Ups:**
```sql
SELECT * FROM follow_up 
WHERE doctor_id = :doctor_id 
AND status = 'scheduled' 
AND payment_confirmed = False;
```

**Revenue Tracking (Confirmed Payments):**
```sql
SELECT COUNT(*), DATE(payment_confirmed_date) 
FROM follow_up 
WHERE doctor_id = :doctor_id 
AND status = 'confirmed'
GROUP BY DATE(payment_confirmed_date);
```

**Completed Cases:**
```sql
SELECT COUNT(*) FROM follow_up 
WHERE doctor_id = :doctor_id 
AND status = 'case_closed';
```

**Patient Dropouts:**
```sql
SELECT COUNT(*) FROM follow_up 
WHERE doctor_id = :doctor_id 
AND status = 'patient_left';
```

---

## Related Documentation
- [Follow-Up Schedule Data Flow](follow_up_schedule_data_flow.md) - Prescription integration
- [Appointment Status Lifecycle](../routes/appointments.py#L550) - Similar pattern for appointments
- [Case Status Management](cases_model.py) - Case entity lifecycle
