# Follow-Up Schedule Data Flow

## Overview
The `follow_up_schedule` object is collected as part of the **Prescription Creation Request** and is used to atomically create a scheduled follow-up alongside the prescription.

---

## Request Structure

### Source: POST `/prescriptions/` API Endpoint
**File:** [routes/prescriptions.py](../routes/prescriptions.py#L264)

```json
{
  "prescription_type": "string",
  "dosage": "string",
  "prescription_duration": "string",
  "duration_days": 1,
  "instructions": "string",
  "follow_up_advice": "string",
  "dietary_restrictions": "string",
  "avoidance": "string",
  "notes": "string",
  "case_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "medicines": [],
  "status": "open",
  "follow_up_schedule": {
    "follow_up_date": "2026-02-23",
    "interval_days": 7,
    "auto_calculate": false,
    "notes": "string"
  }
}
```

---

## Field Collection & Processing

### 1. **follow_up_date** 
- **Type:** Optional date string (ISO 8601 format)
- **Collected from:** Doctor's explicit date selection in the frontend
- **Validation:** Must be today or a future date ([Line 311](../routes/prescriptions.py#L311))
- **Priority:** Highest — if provided, used as the follow-up date
- **Processing:** If provided, this value is directly used in the FollowUp record

### 2. **interval_days**
- **Type:** Optional integer (minimum 7 days)
- **Collected from:** Doctor's explicit interval override (optional)
- **Default behavior:** 
  - If provided: Used as-is
  - If omitted: Calculated automatically from target follow-up date minus last follow-up date (or prescription date if no prior follow-up)
  - **Code:** [Lines 382-389](../routes/prescriptions.py#L382)

### 3. **auto_calculate**
- **Type:** Boolean (default: false)
- **Collected from:** Frontend toggle/flag
- **Purpose:** Instructs backend to derive the follow-up date automatically
- **Logic:**
  - If `auto_calculate=true` AND `duration_days` is set on prescription
  - Follow-up date = prescription_date + duration_days
  - **Helper function:** `_resolve_followup_date()` [Lines 223-241](../routes/prescriptions.py#L223)

### 4. **notes**
- **Type:** Optional string
- **Collected from:** Doctor's follow-up advice/plan text
- **Storage:** Stored as the `plan` field in the FollowUp record ([Line 395](../routes/prescriptions.py#L395))
- **Note:** This replaces the top-level `follow_up_advice` for scheduled follow-ups

---

## Processing Flow

### Decision Tree for Follow-Up Date Resolution

```
┌─ follow_up_schedule provided?
│  YES → proceed
│  NO  → skip follow-up creation (existing behavior)
│
└─ Resolve follow-up date (priority order):
   1. follow_up_date explicitly set?
      YES → use follow_up_date
   2. auto_calculate=true AND duration_days set?
      YES → use prescription_date + duration_days
   3. Fallback
      → use prescription_date + 30 days
```

**Code location:** [_resolve_followup_date() function](../routes/prescriptions.py#L223)

### Interval Days Calculation

```
if schedule.interval_days is provided:
    → use schedule.interval_days (explicit override)

else:
    last_followup = query for last follow-up on this case
    if last_followup exists:
        interval = (fu_date - last_followup.follow_up_date).days
    else:
        interval = (fu_date - prescription.prescription_date).days
    
    interval = max(interval, 7)  # minimum 7 days
```

**Code location:** [Lines 382-389](../routes/prescriptions.py#L382)

---

## Database Storage

### Created FollowUp Record

When `follow_up_schedule` is provided, a new **FollowUp** record is created with:

| Field | Source | Value |
|-------|--------|-------|
| `id` | Auto-generated | UUID |
| `case_id` | From prescription | Same as prescription.case_id |
| `prescription_id` | From prescription | ID of created prescription |
| `doctor_id` | Current user | ID of prescribing doctor |
| `follow_up_date` | Resolved from schedule | Result of date resolution logic |
| `interval_days` | From schedule | Explicit or calculated |
| `status` | Hardcoded | "scheduled" |
| `plan` | schedule.notes | Doctor's follow-up plan |

**Database models:**
- [FollowUp model](../models/followups_model.py)
- [Prescription model](../models/prescriptions_model.py#L23)

---

## Request Models

### FollowUpSchedule (API Input)
**File:** [models/prescriptions_model.py](../models/prescriptions_model.py#L108)

```python
class FollowUpSchedule(SQLModel):
    """
    Optional follow-up scheduling block embedded in PrescriptionCreate.
    
    Priority order for determining the follow-up date:
      1. follow_up_date  — explicit date chosen by the doctor (highest priority)
      2. auto_calculate=True — backend derives date as: prescription_date + duration_days
      3. Neither set   — backend falls back to prescription_date + 30 days
    
    notes: replaces the top-level follow_up_advice field for scheduled follow-ups.
    """
    follow_up_date: Optional[date] = None
    interval_days: Optional[int] = Field(default=None, ge=7)
    auto_calculate: bool = False
    notes: Optional[str] = None
```

### PrescriptionCreate (API Input)
**File:** [models/prescriptions_model.py](../models/prescriptions_model.py#L155)

```python
class PrescriptionCreate(PrescriptionBase):
    """API INPUT MODEL for creating prescriptions"""
    case_id: uuid.UUID
    medicines: List[PrescriptionMedicineCreate] = []
    status: Optional[str] = Field(default="open", max_length=50)
    
    # NEW: optional inline follow-up scheduling; omit to skip auto-creation
    follow_up_schedule: Optional[FollowUpSchedule] = None
```

---

## Transaction Guarantee

The follow-up is created **atomically** within the same transaction as the prescription:
- **Both commit together** if validation passes
- **Both roll back together** if any error occurs
- **No orphaned follow-ups** can exist without a prescription

**Code location:** [Lines 376-396, 410](../routes/prescriptions.py#L376)

---

## Validation Checklist

✅ follow_up_date must be today or future date  
✅ interval_days must be ≥ 7 if provided  
✅ case_id must exist and belong to the doctor  
✅ prescription_date is auto-set to today  
✅ duration_days must be ≥ 1 for auto-calculate mode  

---

## Example Usage

### Example 1: Explicit Date + Custom Interval
```json
{
  "prescription_type": "Homeopathy",
  "dosage": "30C",
  "prescription_duration": "30 days",
  "duration_days": 30,
  "case_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "medicines": [],
  "follow_up_schedule": {
    "follow_up_date": "2026-03-10",
    "interval_days": 14,
    "notes": "Check response to treatment"
  }
}
```
**Result:** Follow-up scheduled for exact date 2026-03-10 with 14-day interval

### Example 2: Auto-Calculate Date
```json
{
  "prescription_type": "Allopathy",
  "dosage": "500mg",
  "prescription_duration": "7 days",
  "duration_days": 7,
  "case_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "medicines": [],
  "follow_up_schedule": {
    "auto_calculate": true,
    "notes": "Review after course completion"
  }
}
```
**Result:** Follow-up automatically scheduled for 7 days from today

### Example 3: No Follow-Up
```json
{
  "prescription_type": "Preventive",
  "dosage": "As needed",
  "prescription_duration": "Ongoing",
  "case_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "medicines": []
}
```
**Result:** Prescription created with NO follow-up (omit `follow_up_schedule` entirely)

---

## API Endpoint

**POST** `/prescriptions/`

**Authentication:** Required (Doctor role)  
**Request body:** `PrescriptionCreate`  
**Response:** `PrescriptionCreateResponse` includes created follow-up details

**Implementation:** [create_prescription() function](../routes/prescriptions.py#L264)
