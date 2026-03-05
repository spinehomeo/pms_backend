# Onsite Patient Endpoints - Visual Brief

**3 Simple Endpoints for Walk-In Patient Management**

---

## 🔍 Endpoint 1: Search Patient

```
GET /api/v1/patients/onsite/search?phone=03001234567
```

### Visual Flow
```
┌─────────────────────────────┐
│   RECEPTIONIST SEARCHES     │
│   "Do we have this patient?"│
└──────────────┬──────────────┘
               │ (phone or name)
               ↓
       ┌───────────────────┐
       │  SEARCH DATABASE  │
       │  (exact match)    │
       │  (fuzzy match)    │
       └───────────┬───────┘
                   │
          ┌────────┴────────┐
          │ FOUND? OR NOT?  │
          ↓                 ↓
      ✅ FOUND         ❌ NOT FOUND
     Return results    Return []
     (up to 10)
```

### Key Points
- **Speed**: ⚡ Instant lookup
- **Input**: Phone (exact) OR Name (fuzzy)
- **Output**: List of matches with scores
- **Example Score**: 0.9 = exact phone match, 0.7 = exact name match

### Example API Call
```bash
# Find by phone
curl -X GET "http://localhost:8000/api/v1/patients/onsite/search?phone=03001234567" \
  -H "Authorization: Bearer {token}"

# Or find by name
curl -X GET "http://localhost:8000/api/v1/patients/onsite/search?full_name=Ali" \
  -H "Authorization: Bearer {token}"

# Or both (results will be combined)
curl -X GET "http://localhost:8000/api/v1/patients/onsite/search?phone=03001234567&full_name=Ali" \
  -H "Authorization: Bearer {token}"
```

### Example Response (200 OK)
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "full_name": "Ali Hassan",
    "phone": "03001234567",
    "gender": "male",
    "cnic": "42101-1234567-1",
    "is_match_by_phone": true,
    "is_match_by_name": false,
    "match_score": 0.9
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "full_name": "Ali Khan",
    "phone": "03109876543",
    "gender": "male",
    "cnic": "42101-9876543-1",
    "is_match_by_phone": false,
    "is_match_by_name": true,
    "match_score": 0.4
  }
]
```

### Status Codes
- **200** — OK, found matches (or empty list)
- **400** — Bad request (missing phone & full_name)
- **401** — Not authorized
- **403** — Not a doctor

---

## ➕ Endpoint 2: Quick-Register Patient

```
POST /api/v1/patients/onsite/quick-register
```

### Visual Flow
```
┌──────────────────────────────┐
│  PATIENT NOT FOUND IN DB     │
│  "We need to register this!"  │
└──────────────┬───────────────┘
               │
       ┌───────┴──────────┐
       │ REQUIRED ONLY:   │
       │ - Full Name      │
       │ - Phone Number   │
       │                  │
       │ OPTIONAL:        │
       │ - Gender         │
       │ - Email          │
       │ - DOB            │
       │ - etc.           │
       └───────┬──────────┘
               │
        ┌──────┴────────┐
        │ AUTO-GENERATE │
        │ TEMP CNIC if  │
        │ not provided  │
        └───────┬───────┘
                │
         ┌──────┴──────┐
         │  SAVE TO DB │
         └──────┬──────┘
                │
         ✅ CREATED
         (201 status)
```

### Key Points
- **Speed**: ⚡ Fast registration (2 fields minimum)
- **CNIC**: Auto-generated as `TEMP-{UUID}` if not provided
- **Gender**: Defaults to "unknown"
- **Output**: New patient ID + all details

### Example API Call
```bash
# Minimal registration (only required fields)
curl -X POST "http://localhost:8000/api/v1/patients/onsite/quick-register" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ahmed Khan",
    "phone": "03109876543"
  }'

# Complete registration (with all optional fields)
curl -X POST "http://localhost:8000/api/v1/patients/onsite/quick-register" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ahmed Khan",
    "phone": "03109876543",
    "gender": "male",
    "date_of_birth": "1990-05-15",
    "email": "ahmed@example.com",
    "city": "Karachi",
    "cnic": "42101-1234567-1",
    "medical_history": "HTN for 5 years"
  }'
```

### Example Response (201 Created)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Ahmed Khan",
  "phone": "03109876543",
  "gender": "male",
  "cnic": "TEMP-A1B2C3D4E5",
  "is_temp_cnic": true,
  "date_of_birth": null,
  "email": null,
  "city": null,
  "created_date": "2026-03-05",
  "is_active": true
}
```

### Status Codes
- **201** — Created successfully
- **400** — Bad request (invalid data)
- **409** — Conflict (patient with this phone already exists)
- **401** — Not authorized
- **403** — Not a doctor

---

## 📋 Endpoint 3: Get Patient Details

```
GET /api/v1/patients/onsite/{patient_id}
```

### Visual Flow
```
┌───────────────────────────────┐
│  DOCTOR WANTS PATIENT INFO    │
│  "Show me all their details"  │
└──────────────┬────────────────┘
               │ (use patient_id)
        ┌──────┴──────┐
        │  FETCH FROM │
        │  DATABASE   │
        └──────┬──────┘
               │
          ┌────┴─────────────┐
          │ FOUND? OR NOT?   │
          ↓                  ↓
    ✅ FOUND            ❌ NOT FOUND
   Return all          Return 404
   patient info        error
```

### Key Points
- **Purpose**: Retrieve full patient record
- **When**: Doctor reviews patient before/after consultation
- **Output**: Complete patient profile
- **Security**: Only your own patients

### Example API Call
```bash
curl -X GET "http://localhost:8000/api/v1/patients/onsite/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer {token}"
```

### Example Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Ahmed Khan",
  "phone": "03109876543",
  "gender": "male",
  "cnic": "TEMP-A1B2C3D4E5",
  "is_temp_cnic": true,
  "date_of_birth": null,
  "email": "ahmed@example.com",
  "phone_secondary": null,
  "residential_address": "123 Main St",
  "city": "Karachi",
  "occupation": "Engineer",
  "referred_by": null,
  "medical_history": null,
  "drug_allergies": null,
  "family_history": null,
  "current_medications": null,
  "notes": null,
  "payment_status": false,
  "created_date": "2026-03-05",
  "is_active": true
}
```

### Status Codes
- **200** — OK
- **404** — Patient not found
- **403** — Not authorized (patient belongs to another doctor)
- **401** — Not authorized (no auth token)

---

## 🔄 Complete Workflow (All 3 Endpoints)

```
WALK-IN PATIENT ARRIVES
    │
    ↓
1️⃣  SEARCH: GET /search?phone=03001234567
    │
    ├─→ FOUND ─→ Use existing patient_id
    │
    └─→ NOT FOUND
        │
        ↓
2️⃣  REGISTER: POST /quick-register
    │
    ├─→ {"full_name": "Ahmed", "phone": "..."}
    │
    └─→ CREATED ─→ Get patient_id
        │
        ↓
3️⃣  REVIEW: GET /{patient_id}
    │
    ├─→ Doctor sees full patient profile
    │
    └─→ Can update patient info if needed
        │
        ↓
4️⃣  CREATE CONSULTATION: POST /consultations/onsite
    │
    ├─→ Use patient_id from step 2 or 3
    ├─→ Add appointment details
    ├─→ Add case details
    ├─→ (Optional) Add prescription
    ├─→ (Optional) Add follow-up
    │
    └─→ ✅ COMPLETE CONSULTATION CREATED!
```

---

## 📊 Comparison Table

| Aspect | Search | Register | Get Details |
|--------|--------|----------|------------|
| **HTTP Method** | GET | POST | GET |
| **URL** | `/search` | `/quick-register` | `/{id}` |
| **Purpose** | Find existing | Create new | Retrieve |
| **Query/Params** | phone OR name | Full form | patient_id |
| **Response** | List (0-10) | Single patient | Single patient |
| **Status Code** | 200 | 201 | 200 |
| **Speed** | ⚡ Instant | ⚡ Fast | ⚡ Instant |

---

## 🎯 When to Use Each

### Use Endpoint 1 (Search)
- ✅ Patient arrives
- ✅ Need to check if already registered
- ✅ Speed is critical
- ✅ Just type phone or first name

### Use Endpoint 2 (Register)
- ✅ Patient NOT found in search
- ✅ New patient to the clinic
- ✅ No time for full form
- ✅ Will fill details later

### Use Endpoint 3 (Get)
- ✅ Doctor wants to review patient
- ✅ Before creating consultation
- ✅ Need to update missing info
- ✅ Verify patient details

---

## 🔐 Authentication

All 3 endpoints require:
```
Authorization: Bearer {your_jwt_token}
```

Get token by:
1. Login to the system
2. Username: doctor email
3. Password: doctor password
4. Copy the returned JWT token
5. Use in Authorization header above

---

## ❌ Common Errors

### Search Endpoint
| Code | Error | Solution |
|------|-------|----------|
| 400 | Missing phone & full_name | Provide at least one |
| 401 | No auth token | Login first |
| 403 | Not a doctor | Use doctor account |

### Register Endpoint
| Code | Error | Solution |
|------|-------|----------|
| 409 | Phone already exists | Use different phone or search first |
| 400 | Missing full_name/phone | Provide both |
| 401 | No auth token | Login first |

### Get Details Endpoint
| Code | Error | Solution |
|------|-------|----------|
| 404 | Patient not found | Check patient_id is correct |
| 403 | Not your patient | Can only access own patients |
| 401 | No auth token | Login first |

---

## 📝 Field Guide

### Required for Search
- `phone` (e.g., "03001234567") — Exact match
- `full_name` (e.g., "Ali") — Fuzzy/partial match

### Required for Register
- `full_name` (e.g., "Ahmed Khan") — Patient's full name
- `phone` (e.g., "03109876543") — Phone number

### Auto-Filled if Not Provided
- `gender` → "unknown"
- `cnic` → "TEMP-{UUID}" (auto-generated)

### Optional for Register
- `date_of_birth`, `email`, `city`, `occupation`, `medical_history`, `drug_allergies`, `family_history`, `current_medications`, `notes`

---

## ✨ Pro Tips

1. **Always search first** to prevent duplicate patients
2. **Temp CNIC is fine** — Update it later if needed
3. **Minimal registration** speeds up desk work (just 2 fields)
4. **Doctor can update** patient details after consultation
5. **Use phone search** — More reliable than name matching

---

**Next**: Create full consultation → [POST /consultations/onsite](./ONSITE_CONSULTATION_GUIDE.md)
