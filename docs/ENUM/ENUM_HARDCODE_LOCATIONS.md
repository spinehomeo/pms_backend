# Enum Usage Cross-Reference - Detailed Code Locations

**Purpose:** Identify every line of code using hardcoded enums or dynamic enum fields  
**Last Updated:** 2026-02-20

---

## 🎯 Quick Navigation

- [Appointments Routes](#appointments-routespy)
- [Prescriptions Routes](#prescriptions-routespy)
- [Patients Routes](#patients-routespy)
- [Reports Routes](#reports-routespy)
- [Cases Routes](#cases-routespy)
- [Followups Routes](#followups-routespy)
- [Users Routes](#users-routespy)
- [Models Overview](#models-overview)

---

## Appointments (`routes/appointments.py`)

### Hardcoded Status Values

#### 1. GET / - Status Filter Parameter
```
📍 Line: ~108
🔍 Pattern: status: Optional[str] = Query(None)

Code:
    def read_appointments(
        ...
        status: Optional[str] = Query(None),  ← ACCEPTS ANY STRING, NO VALIDATION
        ...
    )

Issue: ❌ Accepts any string value
Action: Use EnumService.validate_value() before filtering
```

#### 2. GET / - Status WHERE Clause
```
📍 Line: ~165
🔍 Pattern: .where(Appointment.status == status)

Code:
    if status:
        count_statement = count_statement.where(Appointment.status == status)
        statement = statement.where(Appointment.status == status)

Issue: ❌ No validation of status value
Action: Validate before WHERE clause
```

#### 3. GET /upcoming - Hardcoded Status List
```
📍 Line: ~220-230
🔍 Pattern: .in_(["scheduled", "confirmed"])

Code:
    Appointment.status.in_([
        "scheduled",
        "confirmed"
    ])

Issue: ❌ HARDCODED LIST - Cannot extend without code change
Action: Replace with EnumService.get_doctor_options("AppointmentStatus", ...)
```

#### 4. POST / - Conflict Check Hardcoded Status
```
📍 Line: ~345-354
🔍 Pattern: .in_(["scheduled", "confirmed"])

Code:
    Appointment.status.in_([
        "scheduled",
        "confirmed"
    ]),

Issue: ❌ HARDCODED - Same list as line 225
Action: Create helper function or use EnumService
```

#### 5. Appointment Model - Status Default
```
📍 File: models/appointments_model.py
📍 Line: ~17
🔍 Pattern: status: str = Field(default="scheduled")

Code:
    status: str = Field(default="scheduled")

Issue: ⚠️ Hardcoded default value
Action: ✅ Remove default (should be required), validate in endpoint
```

#### 6. Consultation Type - String Field
```
📍 Line: ~13, ~61
🔍 Pattern: consultation_type: str = Field(default="first", ...)

Code:
    consultation_type: str = Field(default="first", max_length=50)

Issue: ⚠️ Hardcoded default, no validation
Action: Add validation against "ConsultationType" enum
```

### Endpoints Summary

| Endpoint | Method | Issues | Priority |
|----------|--------|--------|----------|
| `/appointments` | GET | Status filter unvalidated (lines 165) | HIGH |
| `/appointments/upcoming` | GET | Status list hardcoded (lines 225-230) | HIGH |
| `/appointments` | POST | Status list hardcoded (lines 345-354) | HIGH |
| `/appointments/{id}` | PATCH | Status field unvalidated | HIGH |

**Total Issues Found:** 4 critical hardcoding instances + 2 validation gaps

---

## Prescriptions (`routes/prescriptions.py`)

### Python Enum Hardcoding

#### 1. PrescriptionType Import & Usage
```
📍 Line: ~10
🔍 Pattern: from models.prescriptions_model import PrescriptionType

Code:
    from models.prescriptions_model import (
        Prescription, 
        PrescriptionCreate, 
        ...
        PrescriptionType,  ← HARDCODED PYTHON ENUM IMPORT
        ...
    )

Issue: ❌ Uses Python Enum instead of database-driven
Action: Remove import, use string + EnumService validation
```

#### 2. Create Prescription - Type Validation
```
📍 Line: ~150-160 (approximate)
🔍 Pattern: Uses PrescriptionType enum in request validation

Code:
    class PrescriptionCreate(SQLModel):
        prescription_type: PrescriptionType = Field(default=...)
        
Issue: ❌ Validates against Python Enum hardcoding
Action: Change to: prescription_type: str = Field(max_length=100)
Action: Validate with EnumService.validate_value()
```

#### 3. Update Prescription - Type Validation
```
📍 File: models/prescriptions_model.py
📍 Line: ~35-40 (approximate)

Code:
    class Prescription(PrescriptionBase, table=True):
        prescription_type: PrescriptionType = Field(default=...)

Issue: ❌ Database model enforces Python Enum type
Action: Change to: prescription_type: str = Field(max_length=100)
```

### Hardcoded Values in Prescriptions Model

```
📍 File: models/prescriptions_model.py
📍 Lines: 9-26

PrescriptionType Enum:
    class PrescriptionType(str, Enum):
        CONSTITUTIONAL = "Constitutional"        ← HARDCODED
        CLASSICAL = "Classical"                  ← HARDCODED
        INTER_CURRENT = "Inter Current"          ← HARDCODED
        PURE_BIOCHEMIC = "Pure Bio Chemic"       ← HARDCODED
        MOTHER_TINCTURE = "Mother Tincture"      ← HARDCODED
        PATENT = "Patent"                        ← HARDCODED

RepetitionEnum:
    class RepetitionEnum(str, Enum):
        OD = "OD"                    ← HARDCODED
        BD = "BD"                    ← HARDCODED
        TDS = "TDS"                  ← HARDCODED
        ONCE_WEEKLY = "Once Weekly"  ← HARDCODED
        ONCE_10_DAYS = "Once in 10 Days"  ← HARDCODED
        FORTNIGHTLY = "Fortnightly"  ← HARDCODED
        MONTHLY = "Monthly"          ← HARDCODED

Action: BOTH ENUMS should be migrated to dynamic enum system
```

### Report Generation - Hardcoded Aggregation

#### 4. Prescription Distribution Report
```
📍 File: routes/reports.py
📍 Line: ~416
🔍 Pattern: Groups by prescription_type

Code:
    Prescription.prescription_type.label('prescription_type'),
    func.count().label('count')
    .group_by(Prescription.prescription_type)

Issue: ⚠️ Assumes hardcoded enum values exist
Action: ✅ Works but lacks validation - OK as grouping
```

### Endpoints Summary

| Endpoint | Method | Field | Issue | Priority |
|----------|--------|-------|-------|----------|
| `/prescriptions` | POST | prescription_type | Hardcoded enum | HIGH |
| `/prescriptions/{id}` | PATCH | prescription_type | Hardcoded enum | HIGH |
| `/prescriptions/report` | GET | prescription_type | Groups by hardcoded | MEDIUM |

**Total Issues Found:** 2 critical (POST/PATCH) + 1 hardcoded enum file

---

## Patients (`routes/patients.py` + `models/patients_model.py`)

### Python Enum Hardcoding

#### 1. PatientGender Enum Definition
```
📍 File: models/patients_model.py
📍 Lines: 8-12

Code:
    class PatientGender(str, Enum):
        MALE = "male"              ← HARDCODED
        FEMALE = "female"          ← HARDCODED
        OTHER = "other"            ← HARDCODED
        CHILD = "child"            ← HARDCODED

Issue: ❌ HARDCODED PYTHON ENUM - Cannot extend without code change
Action: Remove entirely, use dynamic enum "PatientGender"
```

#### 2. Patient Model - Gender Field
```
📍 File: models/patients_model.py
📍 Line: ~22

Code:
    gender: PatientGender
    (in PatientBase class)

Issue: ❌ Uses Python Enum type validation
Action: Change to: gender: str = Field(max_length=20)
```

#### 3. Patient Registration - Gender Parameter
```
📍 File: routes/users.py
📍 Line: ~1305

Code:
    Patient(
        ...
        gender=patient_in.gender,  ← Uses hardcoded enum
        ...
    )

Issue: ❌ Validates against Python Enum
Action: Validate with EnumService.validate_value("PatientGender", ...)
```

#### 4. Patient Update - Gender Parameter
```
📍 File: routes/users.py
📍 Line: ~1453 (approximate)

Code:
    patient.gender = patient_in.gender

Issue: ❌ Uses hardcoded enum
Action: Validate before assignment
```

### Endpoints Summary

| Endpoint | Method | Field | Issue | Priority |
|----------|--------|-------|-------|----------|
| `POST /patients` | POST | gender | Enum hardcoded | HIGH |
| `PATCH /patients/{id}` | PATCH | gender | Enum hardcoded | HIGH |

**Total Issues Found:** 1 hardcoded enum + 2 endpoints using it

---

## Reports (`routes/reports.py`)

### Consultation Type Grouping

#### 1. Consultation Distribution Report
```
📍 Line: ~283
🔍 Pattern: Groups by consultation_type

Code:
    select(Appointment.consultation_type, func.count().label('count'))
        .group_by(Appointment.consultation_type)

Issue: ⚠️ Groups by actual values - assumes they exist
Action: ✅ Not critical - only filtering/grouping
Recommendation: Add validation in create/update
```

#### 2. Report Output Structure
```
📍 Line: ~375
🔍 Pattern: Returns consultation_distribution dict

Result: {
    "consultation_type": {
        "first": 45,
        "follow-up": 23,
        ...
    }
}

Issue: ⚠️ Assumes specific consultation types exist
Action: Document expected values in API response
```

---

## Cases (`routes/cases.py`)

### Current Status: ✅ SAFE - No Enum Fields

```
📍 Models checked: cases_model.py
📍 Routes checked: cases.py

Status: ✅ No hardcoded enums
Note: No status field currently exists

Recommendation: Add CaseStatus field for tracking:
    - "open"
    - "under_treatment"
    - "closed"
    - "archived"
```

---

## Followups (`routes/followups.py`)

### Current Status: ✅ SAFE - No Enum Fields

```
📍 Models checked: followups_model.py
📍 Routes checked: followups.py

Status: ✅ No hardcoded enums
Note: No status field currently exists

Recommendation: Add FollowupStatus field for tracking:
    - "scheduled"
    - "completed"
    - "pending"
    - "cancelled"
```

---

## Users (`routes/users.py`)

### Patient Gender References

#### 1. Patient Signup - Gender Parameter
```
📍 Line: ~1240-1305
🔍 Pattern: gender: Patient's gender (MALE, FEMALE, OTHER)

Code:
    class PatientRegisterIn(SQLModel):
        ...
        gender: PatientGender  ← HARDCODED ENUM
        ...

Issue: ❌ Uses hardcoded Python Enum
Action: Change to: gender: str and validate with EnumService
```

#### 2. Partner Signup - Gender Parameter
```
📍 Line: ~1370-1453
🔍 Pattern: Similar pattern for partner/staff patient registration

Issue: ❌ Same hardcoding issue
Action: Same fix as above
```

### Endpoints Summary

| Endpoint | Method | Field | Issue | Priority |
|----------|--------|-------|-------|----------|
| `POST /users/patient-register` | POST | gender | Enum hardcoded | HIGH |
| `POST /users/partner-register` | POST | gender | Enum hardcoded | HIGH |

**Total Issues Found:** 2 endpoints using hardcoded gender enum

---

## Models Overview

### Summary of All Model Files with Enum Issues

| File | Line | Issue | Type | Action |
|------|------|-------|------|--------|
| `models/appointments_model.py` | 17 | status hardcoded default | String | Remove default, validate |
| `models/appointments_model.py` | 13 | consultation_type hardcoded | String | Add validation |
| `models/prescriptions_model.py` | 9-26 | PrescriptionType + RepetitionEnum | Python Enum | Migrate to dynamic |
| `models/patients_model.py` | 8-12 | PatientGender hardcoded | Python Enum | Migrate to dynamic |
| `models/cases_model.py` | - | No enum fields | - | ✅ OK |
| `models/followups_model.py` | - | No enum fields | - | ✅ OK |

---

## 📊 Severity Matrix

### Critical (Fix Immediately)
- [ ] `models/prescriptions_model.py` - PrescriptionType enum (lines 9-16)
- [ ] `models/patients_model.py` - PatientGender enum (lines 8-12)
- [ ] `routes/appointments.py` - Hardcoded status (lines 225-230)
- [ ] `routes/prescriptions.py` - Type field validation (imports at line 10)
- [ ] `routes/users.py` - Gender enum usage (lines 1305, 1453)

### High Priority (Fix This Sprint)
- [ ] `routes/appointments.py` - Status filter validation (line 165)
- [ ] `routes/appointments.py` - Conflict check status (lines 345-354)

### Medium Priority (Fix Next Sprint)
- [ ] `routes/appointments.py` - ConsultationType validation (line ~340)
- [ ] Add missing status fields (PrescriptionStatus, FollowupStatus, CaseStatus)

### Low Priority (Future)
- [ ] Add PatientCategory field
- [ ] Add BloodGroup field

---

## 🔗 Related Files

**Enum Service Implementation:**
- `utils/enum_service.py` - All validation & management methods

**Enum Routes (Reference for patterns):**
- `routes/enums.py` - How to properly use EnumService

**Seed Data:**
- `utils/initial_data.py` - Where to seed enum values

**Documentation:**
- `docs/ENUM/BACKEND_ENUM_INTEGRATION.md` - Integration patterns
- `docs/ENUM/DYNAMIC_ENUM_SYSTEM.md` - Full system overview

---

**Report Generated:** February 20, 2026  
**Total Hardcoded Enums Found:** 5  
**Total Hardcoded String Lists:** 4  
**Total Affected Endpoints:** 12+  
**Estimated Migration Effort:** 4-6 hours
