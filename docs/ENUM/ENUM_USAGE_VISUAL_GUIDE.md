# Enum Types Usage Reference - Visual Guide

**Purpose:** Show which enum types should be used in which endpoints  
**Format:** Visual reference with relationships and dependencies

---

## 🗂️ Enum Type Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│               ENUM TYPES (10 TOTAL)                         │
└─────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────┐
  │  📋 DOCUMENT/PROCESS ENUMS (Status & Type Fields)        │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │  AppointmentStatus ──→ Appointment.status                │
  │    Values: scheduled, confirmed, completed, cancelled    │
  │    Used in: appointments.py (4+ endpoints)               │
  │    Status: ❌ Hardcoded - NEEDS MIGRATION                │
  │                                                           │
  │  PrescriptionStatus ──→ Prescription.status (NEW)        │
  │    Values: open, completed, cancelled                    │
  │    Used in: prescriptions.py (would add status field)    │
  │    Status: ⚠️ Not yet implemented                        │
  │                                                           │
  │  FollowupStatus ──→ FollowUp.status (NEW)               │
  │    Values: scheduled, completed, pending, cancelled      │
  │    Used in: followups.py (would add status field)        │
  │    Status: ⚠️ Not yet implemented                        │
  │                                                           │
  │  CaseStatus ──→ PatientCase.status (NEW)                │
  │    Values: open, active, closed, archived               │
  │    Used in: cases.py (would add status field)           │
  │    Status: ⚠️ Not yet implemented                        │
  │                                                           │
  └──────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────┐
  │  👤 PERSON/DEMOGRAPHIC ENUMS                             │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │  PatientGender ──→ Patient.gender                        │
  │    Values: male, female, other, child                    │
  │    Used in: patients.py, users.py (2+ endpoints)         │
  │    Status: ❌ Hardcoded Python Enum - NEEDS MIGRATION   │
  │                                                           │
  │  BloodGroup ──→ Patient.blood_group (NEW)               │
  │    Values: A+, A-, B+, B-, O+, O-, AB+, AB-             │
  │    Used in: patients.py (informational only)            │
  │    Status: ⚠️ Not yet implemented                        │
  │                                                           │
  │  PatientCategory ──→ Patient.category (NEW)             │
  │    Values: regular, VIP, corporate, charity              │
  │    Used in: patients.py (reporting/filtering)           │
  │    Status: ⚠️ Not yet implemented                        │
  │                                                           │
  └──────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────┐
  │  🏥 APPOINTMENT/VISIT CLASSIFICATION ENUMS              │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │  ConsultationType ──→ Appointment.consultation_type      │
  │    Values: first, follow-up, emergency, review           │
  │    Used in: appointments.py (3+ endpoints)               │
  │    Status: ⚠️ Hardcoded default - NEEDS VALIDATION      │
  │                                                           │
  └──────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────┐
  │  💊 PRESCRIPTION CLASSIFICATION ENUMS (Python Enums)    │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │  PrescriptionType ──→ Prescription.prescription_type     │
  │    Values:                                               │
  │      - Constitutional                                    │
  │      - Classical                                         │
  │      - Inter Current                                     │
  │      - Pure Bio Chemic                                   │
  │      - Mother Tincture                                   │
  │      - Patent                                            │
  │    Used in: prescriptions.py (2+ endpoints)              │
  │    Status: ❌ Hardcoded Python Enum - NEEDS MIGRATION  │
  │                                                           │
  │  RepetitionInterval ──→ PrescriptionMedicine.frequency  │
  │    Values:                                               │
  │      - OD (once daily)                                   │
  │      - BD (twice daily)                                  │
  │      - TDS (thrice daily)                                │
  │      - Once Weekly                                       │
  │      - Once in 10 Days                                   │
  │      - Fortnightly                                       │
  │      - Monthly                                           │
  │    Used in: prescriptions.py, medicines.py               │
  │    Status: ❌ Hardcoded Python Enum - NEEDS MIGRATION  │
  │                                                           │
  └──────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow: How Enums Should Work

### Current Flow (❌ Broken)

```
┌──────────────────┐
│  Hardcoded       │
│  Python Enum     │
│  (e.g., Gender)  │
└────────────────┬─┘
                 │
                 ▼
         ❌ Request validation
         ❌ Fails if not in Enum
         ❌ No admin override
         ❌ Code change required
                 │
                 ▼
        ┌─────────────────┐
        │  Model Field    │
        │  (e.g., Gender) │
        └─────────────────┘
```

### Intended Flow (✅ Dynamic)

```
┌──────────────────────┐
│  Database            │
│  enum_types table    │
│  (e.g., PatientGender) │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  EnumService Methods │
│  validate_value()    │
│  get_doctor_options()│
└───────────┬──────────┘
            │
            ▼
    ✅ API validation
    ✅ Doctor preferences honored
    ✅ Admin control
    ✅ Zero downtime changes
            │
            ▼
┌──────────────────────┐
│  Endpoint Handler    │
│  (e.g., POST /patient)│
└───────────┬──────────┘
            │
            ▼
┌──────────────────────┐
│  Model Field         │
│  gender: str = ...   │
└──────────────────────┘
```

---

## 🔗 Endpoint-to-Enum Mapping

### Appointments Endpoints

```
POST /appointments/
    ├─ Input: appointment_in (AppointmentCreate)
    │  ├─ status: str (Default: "scheduled")
    │  │  └─ Should validate: AppointmentStatus ❌
    │  └─ consultation_type: str (Default: "first")
    │     └─ Should validate: ConsultationType ❌
    │
    └─ Action:
       1. Validate status against AppointmentStatus enum
       2. Validate consultation_type against ConsultationType enum
       3. Save to database

GET /appointments/?status=confirmed
    ├─ Input: status (Query parameter)
    │  └─ Should validate: AppointmentStatus ❌
    └─ Action:
       1. Validate status value exists
       2. Filter by status

PATCH /appointments/{id}
    ├─ Input: appointment_update (AppointmentUpdate)
    │  └─ status: Optional[str]
    │     └─ Should validate: AppointmentStatus ❌
    └─ Action:
       1. Validate status if provided
       2. Update record
```

### Prescriptions Endpoints

```
POST /prescriptions/
    ├─ Input: prescription_in (PrescriptionCreate)
    │  ├─ prescription_type: PrescriptionType ❌
    │  │  └─ Should be: str, validated with EnumService
    │  └─ (medicines have frequency/repetition) ❌
    │     └─ Should validate: RepetitionInterval
    └─ Action:
       1. Validate prescription_type
       2. Validate repetition intervals
       3. Save to database

PATCH /prescriptions/{id}
    ├─ Input: prescription_update
    │  └─ prescription_type: Optional[PrescriptionType] ❌
    │     └─ Should validate: PrescriptionType
    └─ Action:
       1. Validate if provided
       2. Update record

GET /prescriptions/report
    └─ Groups by prescription_type
       (Result automatically correct if validation enforced)
```

### Patients Endpoints

```
POST /users/patient-register
    ├─ Input: patient_in (PatientRegisterIn)
    │  └─ gender: PatientGender ❌
    │     └─ Should be: str, validated with EnumService
    └─ Action:
       1. Validate gender
       2. Create patient

PATCH /users/patients/{id}
    ├─ Input: patient_update
    │  └─ gender: Optional[PatientGender] ❌
    │     └─ Should be: Optional[str], validated
    └─ Action:
       1. Validate if provided
       2. Update record
```

---

## 🛠️ Migration Path for Each Enum Type

### Pattern 1: Appointment Status

#### Current Implementation
```python
# ❌ Hardcoded string values
def read_appointments(..., status: Optional[str] = Query(None)):
    if status:
        statement.where(Appointment.status == status)  # No validation

# Hardcoded in another place
.where(Appointment.status.in_(["scheduled", "confirmed"]))
```

#### Target Implementation
```python
# ✅ Dynamic enum validation
def read_appointments(..., status: Optional[str] = Query(None)):
    if status:
        # Validate status exists in database
        is_valid = EnumService.validate_value(
            session, "AppointmentStatus", status, current_user.id
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        statement.where(Appointment.status == status)

# Get available statuses for doctor (respects their preferences)
def get_appointment_statuses(session: SessionDep, current_user: CurrentUser):
    options = EnumService.get_doctor_options(
        session, "AppointmentStatus", current_user.id
    )
    return {"statuses": options}
```

---

### Pattern 2: PatientGender

#### Current Implementation
```python
# ❌ Python Enum hardcoded
class PatientGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    CHILD = "child"

class PatientCreate(SQLModel):
    gender: PatientGender  # Enforces enum

# Usage
patient = Patient(gender=PatientGender.MALE)  # Must use enum
```

#### Target Implementation
```python
# ✅ Dynamic enum, stored as string
class PatientCreate(SQLModel):
    gender: str  # Accept any string

def create_patient(...):
    # Validate gender against database enum
    is_valid = EnumService.validate_value(
        session, "PatientGender", payload.gender, doctor_id
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid gender")
    
    # Save with validated string value
    patient = Patient(
        gender=payload.gender,  # String value
        ...
    )
```

---

### Pattern 3: PrescriptionType

#### Current Implementation
```python
# ❌ Python Enum hardcoded in model
class PrescriptionType(str, Enum):
    CONSTITUTIONAL = "Constitutional"
    CLASSICAL = "Classical"
    INTER_CURRENT = "Inter Current"
    PURE_BIOCHEMIC = "Pure Bio Chemic"
    MOTHER_TINCTURE = "Mother Tincture"
    PATENT = "Patent"

# Database model enforces this
class Prescription(PrescriptionBase, table=True):
    prescription_type: PrescriptionType

# API input model enforces this
class PrescriptionCreate(SQLModel):
    prescription_type: PrescriptionType
```

#### Target Implementation
```python
# ✅ Remove Python Enum completely

# Database model stores as string
class Prescription(PrescriptionBase, table=True):
    prescription_type: str = Field(max_length=100)

# API input accepts string
class PrescriptionCreate(SQLModel):
    prescription_type: str

# Endpoint validates
def create_prescription(..., payload: PrescriptionCreate):
    # Validate type exists in database
    is_valid = EnumService.validate_value(
        session, "PrescriptionType", payload.prescription_type, doctor_id
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid type")
    
    prescription = Prescription(
        prescription_type=payload.prescription_type,
        ...
    )
```

---

## 📊 Implementation Checklist Template

### For Each Enum Type

```
Enum Type: [NAME]
Current Location(s): [FILE + LINES]
Target Endpoints: [LIST]
Difficulty: [EASY/MEDIUM/HARD]

Step 1: Remove Python Enum
  - [ ] Delete class definition in models/
  - [ ] Remove from imports
  - [ ] Run: grep -r "ClassName" . --include="*.py" to find usages

Step 2: Update Model Fields
  - [ ] Change field type from Enum to str
  - [ ] Add max_length constraint
  - [ ] Update docstring

Step 3: Update API Schemas
  - [ ] Update request models (Create, Update classes)
  - [ ] Update response models
  - [ ] Add validation examples in docstrings

Step 4: Update Endpoints
  - [ ] Add EnumService.validate_value() calls
  - [ ] Catch validation errors and return 400
  - [ ] Update Query/Path parameter descriptions

Step 5: Seed Initial Values
  - [ ] Add to seed_enums() in utils/initial_data.py
  - [ ] Test seed with: python -m utils.initial_data

Step 6: Test & Verify
  - [ ] Test creation with valid value
  - [ ] Test creation with invalid value (should fail)
  - [ ] Test getting filtered options for doctor
  - [ ] Test doctor preference toggle
  - [ ] Run existing tests (should pass)
```

---

## 📈 Enum Type Priority Matrix

### Timeline for Implementation

```
NOW (Critical Path - Week 1)
├─ 1. Migrate PatientGender (High impact, low effort)
│  └─ impacts: 2 endpoints, ~2 hours
│
├─ 2. Migrate AppointmentStatus (High impact, medium effort)
│  └─ impacts: 4+ endpoints, ~4 hours
│
└─ 3. Migrate PrescriptionType (High impact, medium effort)
   └─ impacts: 2 endpoints, ~3 hours

SOON (Important - Week 2-3)
├─ 4. Add ConsultationType validation (High impact, low effort)
│  └─ impacts: 3 endpoints, ~2 hours
│
├─ 5. Migrate RepetitionInterval (Medium impact, medium effort)
│  └─ impacts: medicines.py, ~2 hours
│
└─ 6. Add PrescriptionStatus field (Medium impact, medium effort)
   └─ new field, ~3 hours

LATER (Enhancement - Week 4+)
├─ 7. Add FollowupStatus field (~2 hours)
├─ 8. Add CaseStatus field (~2 hours)
├─ 9. Add PatientCategory field (~1 hour)
└─ 10. Add BloodGroup field (~1 hour)
```

**Total Effort:** ~20 hours for full migration

---

## 🔍 Testing Strategy

### Unit Tests (By Endpoint)

```
Test Enum Validation:
  ✓ Valid value accepted
  ✓ Invalid value rejected with 400
  ✓ Different doctors see different options
  ✓ Disabled options hidden from doctor

Test Filtering:
  ✓ Filter by valid enum value works
  ✓ Filter by invalid enum value returns empty
  ✓ Multiple filters work together

Test Doctor Preferences:
  ✓ Doctor can disable option
  ✓ Disabled option hidden in GET
  ✓ Can toggle back on
  ✓ Staff sees doctor's filtered options
```

### Integration Tests

```
Test Combined Flow:
  1. Admin creates PatientGender enum with values
  2. Doctor registers with valid gender
  3. Doctor disables one gender option
  4. Staff queries and sees limited options
  5. Staff cannot create patient with disabled gender
```

---

## 📚 Related Documentation

- `docs/ENUM/DYNAMIC_ENUM_SYSTEM.md` - Full system guide
- `docs/ENUM/BACKEND_ENUM_INTEGRATION.md` - Integration patterns
- `routes/enums.py` - Example implementation
- `utils/enum_service.py` - All available methods

---

**Created:** February 20, 2026  
**Last Updated:** February 20, 2026
