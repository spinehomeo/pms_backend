# Onsite Patient Endpoints - Quick Reference

## 3 Endpoints for Walk-In Patient Management

---

## 1️⃣ **GET `/patients/onsite/search`**
### Search for Existing Patients

**Purpose**: Find patients quickly to prevent duplicate registrations

**Use Case**: 
- Patient walks in → Receptionist searches by phone/name
- Faster than manual lookup

**Parameters**:
| Parameter | Type | Required | Example |
|-----------|------|----------|---------|
| `phone` | string | One of these two | `03001234567` |
| `full_name` | string | ↑ | `Ali Hassan` |

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "full_name": "Ali Hassan",
    "phone": "03001234567",
    "gender": "male",
    "cnic": "42101-1234567-1",
    "is_match_by_phone": true,
    "is_match_by_name": false,
    "match_score": 0.9
  }
]
```

**Key Features**:
- ✅ Exact phone match (score: 0.9)
- ✅ Fuzzy name match (partial text, case-insensitive)
- ✅ Smart scoring (shows match quality)
- ✅ Returns up to 10 matches, sorted by relevance
- ✅ Scoped to current doctor only

**Errors**:
- `400` — Neither phone nor full_name provided
- `401` — Unauthorized (no auth token)

---

## 2️⃣ **POST `/patients/onsite/quick-register`**
### Fast Patient Registration

**Purpose**: Register new walk-in patients in seconds (min 2 fields)

**Use Case**:
- "We don't have this patient" → Receptionist registers quickly
- Doctor completes full details later after consultation

**Required Fields**:
```json
{
  "full_name": "Ahmed Khan",
  "phone": "03109876543"
}
```

**Optional Fields** (all other patient data):
```json
{
  "gender": "male",
  "date_of_birth": "1990-05-15",
  "email": "ahmed@example.com",
  "city": "Karachi",
  "cnic": "42101-9876543-1",
  "medical_history": "...",
  "drug_allergies": "...",
  "notes": "..."
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "full_name": "Ahmed Khan",
  "phone": "03109876543",
  "gender": "male",
  "cnic": "TEMP-A1B2C3D4E5",
  "is_temp_cnic": true,
  "created_date": "2026-03-05",
  "is_active": true
}
```

**Key Features**:
- ⚡ Speed: Only 2 required fields (name + phone)
- 🤖 Auto-generates temp CNIC (e.g., `TEMP-ABC123`) if not provided
- ✅ Doctor can update patient record later
- ✅ Prevents duplicates (checks phone uniqueness)

**Errors**:
- `409` — Patient with this phone already exists
- `400` — Invalid data / missing required fields
- `401` — Unauthorized

---

## 3️⃣ **GET `/patients/onsite/{patient_id}`**
### Retrieve Patient Details

**Purpose**: Get full patient record for review/edit during consultation

**Use Case**:
- Doctor wants to review patient's history
- Update missing fields after consultation
- Verify patient information

**Path Parameter**:
| Parameter | Type | Example |
|-----------|------|---------|
| `patient_id` | UUID | `550e8400-e29b-41d4-a716-446655440000` |

**Response** (200 OK):
```json
{
  "id": "uuid",
  "full_name": "Ahmed Khan",
  "phone": "03109876543",
  "gender": "male",
  "cnic": "TEMP-A1B2C3D4E5",
  "is_temp_cnic": true,
  "date_of_birth": "1990-05-15",
  "email": "ahmed@example.com",
  "city": "Karachi",
  "medical_history": "...",
  "created_date": "2026-03-05",
  "is_active": true
}
```

**Key Features**:
- ✅ Shows full patient profile
- ✅ Shows if CNIC is temporary (`is_temp_cnic`)
- ✅ Scoped to current doctor (can't access other doctors' patients)

**Errors**:
- `404` — Patient not found
- `403` — Not authorized (patient belongs to another doctor)
- `401` — Unauthorized (no auth token)

---

## 🔄 Complete Workflow Example

```
┌─────────────────────────────────────────────────────────────┐
│              WALK-IN PATIENT FLOW                           │
└─────────────────────────────────────────────────────────────┘

1. PATIENT ARRIVES
   ↓
   Receptionist: "What's your phone number?"
   Response: "03001234567"
   
   ↓
2. SEARCH FOR EXISTING PATIENT
   GET /patients/onsite/search?phone=03001234567
   - If FOUND → Use existing patient ID
   - If NOT FOUND → Continue to step 3
   
   ↓
3. QUICK-REGISTER NEW PATIENT (if not found)
   POST /patients/onsite/quick-register
   {
     "full_name": "Ahmed Khan",
     "phone": "03001234567"
   }
   Response: patient_id = "abc123..."
   
   ↓
4. DOCTOR REVIEWS PATIENT
   GET /patients/onsite/abc123...
   - See full patient profile
   - Note: Some fields may be empty (will fill later)
   
   ↓
5. CREATE FULL CONSULTATION
   POST /consultations/onsite
   - Use patient_id from step 3
   - Add appointment, case, prescription, etc.
   
   ✅ DONE!
```

---

## 📊 Data Comparison

| Aspect | Search | Quick-Register | Get Details |
|--------|--------|-----------------|------------|
| **Method** | GET | POST | GET |
| **URL** | `/search` | `/quick-register` | `/{id}` |
| **Purpose** | Find patients | Register new | Retrieve details |
| **Speed** | ⚡ Instant | ⚡ Fast (2 fields) | ⚡ Instant |
| **Required Fields** | phone OR name | full_name + phone | patient_id |
| **Returns** | List (up to 10) | Single patient | Single patient |
| **Status Code** | 200 OK | 201 Created | 200 OK |

---

## 🔐 Authentication

✅ **All 3 endpoints require**: Bearer token (doctor account)

```bash
Authorization: Bearer {your_jwt_token}
```

---

## 🚀 Quick Test Commands

### 1. Search
```bash
curl -X GET "http://localhost:8000/api/v1/patients/onsite/search?phone=03001234567" \
  -H "Authorization: Bearer {token}"
```

### 2. Quick-Register
```bash
curl -X POST "http://localhost:8000/api/v1/patients/onsite/quick-register" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ahmed Khan",
    "phone": "03109876543"
  }'
```

### 3. Get Details
```bash
curl -X GET "http://localhost:8000/api/v1/patients/onsite/{patient_id}" \
  -H "Authorization: Bearer {token}"
```

---

## ⚠️ Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| **409 Conflict** | Phone already exists | Use existing patient's ID or search first |
| **404 Not Found** | Patient ID doesn't exist | Verify patient_id is correct |
| **403 Forbidden** | Patient is from another doctor | Can only access your own patients |
| **400 Bad Request** | Missing required fields | Check payload has all required fields |
| **401 Unauthorized** | No/invalid auth token | Provide valid Bearer token |

---

## 📋 Field Descriptions

### Patient Basic Info
- **full_name**: Patient's full name (e.g., "Ahmed Khan")
- **phone**: Primary phone number (e.g., "03001234567")
- **gender**: male | female | other (defaults to "unknown")
- **cnic**: National ID (auto-generated as TEMP-xxx if not provided)

### Patient Details
- **date_of_birth**: Birth date (ISO format: YYYY-MM-DD)
- **email**: Hospital email
- **city**: Residential city
- **occupation**: Job/profession
- **referred_by**: Who referred the patient

### Medical Info
- **medical_history**: Past medical conditions
- **drug_allergies**: Known allergies
- **family_history**: Family health conditions
- **current_medications**: Current drugs/medicines

### Match Scoring (Search Results)
- **match_score**: 0.0 to 1.0
  - 0.9 = Exact phone match (best)
  - 0.7 = Exact name match
  - 0.4 = Partial name match
- **is_match_by_phone**: true/false
- **is_match_by_name**: true/false

---

## 💡 Tips

1. **Always search first** before registering to avoid duplicates
2. **Temporary CNIC** gets generated automatically if not provided — you can update it later
3. **All fields except name+phone are optional** at registration
4. **Doctor scoping**: You only see/manage your own patients
5. **Phone is unique** per doctor (can't have two patients with same phone)

---

## Next Steps

After registering/finding a patient, create a full onsite consultation:
→ [POST /consultations/onsite](../ONSITE_CONSULTATION_GUIDE.md)
