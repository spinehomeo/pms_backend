# Onsite Consultation System - Quick Start Checklist

**Time to deploy**: ~5 minutes  
**Complexity**: Low (no code changes needed by user)

---

## ✅ Pre-Deployment Checklist

- [ ] Database connection working
- [ ] Alembic configured (or fallback script available)
- [ ] Doctor test accounts exist in system

---

## 📋 Deployment Steps

### Step 1: Create Database Migration (2 min)

**If using Alembic** (recommended):
```bash
# In project root
alembic revision --autogenerate -m "Add onsite consultation tables"

# Review the generated migration file - it should create:
# - sequence_counter table with indexes
# - onsite_consultation_audit table with indexes

alembic upgrade head
```

**If NOT using Alembic**:
```bash
# Run manual setup
python -m scripts.setup_onsite_consultation

# Output should show:
# ✓ SequenceCounter table created
# ✓ OnsiteConsultationAudit table created
```

### Step 2: Verify Database Setup (1 min)

Connect to your database and run:

**PostgreSQL**:
```sql
-- Check tables exist
\dt sequence_counter
\dt onsite_consultation_audit

-- Check indexes
\di idx_counter_type_prefix
\di idx_audit_doctor_date
\di idx_audit_patient_phone
\di idx_audit_idempotency

-- All should show valid indexes
```

**MySQL**:
```sql
SHOW TABLES LIKE 'sequence%';
SHOW TABLES LIKE 'onsite%';

SHOW INDEX FROM sequence_counter;
SHOW INDEX FROM onsite_consultation_audit;
```

### Step 3: Test API Endpoints (1 min)

Start the server and test each endpoint:

```bash
# Terminal 1: Start server
python main.py
# or
uvicorn main:app --reload
```

```bash
# Terminal 2: Run test requests

# 1. Test patient search (should return empty list)
curl -X GET "http://localhost:8000/api/v1/patients/onsite/search?phone=03001234567" \
  -H "Authorization: Bearer {YOUR_DOCTOR_TOKEN}"

# Example response:
# []

# 2. Test quick-register
curl -X POST "http://localhost:8000/api/v1/patients/onsite/quick-register" \
  -H "Authorization: Bearer {YOUR_DOCTOR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Patient",
    "phone": "03001234567"
  }'

# Example response: 201 Created
# {
#   "id": "uuid...",
#   "full_name": "Test Patient",
#   "phone": "03001234567",
#   "cnic": "TEMP-ABC123DE45",
#   "is_temp_cnic": true
# }

# 3. Test consultation creation
curl -X POST "http://localhost:8000/api/v1/consultations/onsite" \
  -H "Authorization: Bearer {YOUR_DOCTOR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "patient": {
      "full_name": "Test Patient",
      "phone": "03001234567"
    },
    "appointment": {
      "consultation_type": "first"
    },
    "case": {
      "chief_complaint_patient": "Headache",
      "chief_complaint_duration": "2 days"
    }
  }'

# Example response: 201 Created
# {
#   "patient_id": "uuid...",
#   "appointment_id": "uuid...",
#   "case_id": "uuid...",
#   "case_number": "C-MAR26-001",
#   "appointment_status": "in_progress",
#   "is_new_patient": true
# }
```

### Step 4: Verify in Database (1 min)

Check that data was created:

```sql
-- Check consultation audit trail
SELECT * FROM onsite_consultation_audit LIMIT 1;

-- Check sequence counter was created
SELECT * FROM sequence_counter;

-- Should show:
-- counter_type | prefix  | current_sequence
-- case         | C-MAR26 | 1
```

### Step 5: Documentation (Optional, 2 min)

Share with team:
1. **Primary**: `docs/ONSITE_CONSULTATION_GUIDE.md`
2. **Summary**: `docs/ONSITE_IMPLEMENTATION_SUMMARY.md`
3. **API Paths**:
   - `GET /api/v1/patients/onsite/search`
   - `POST /api/v1/patients/onsite/quick-register`
   - `GET /api/v1/patients/onsite/{patient_id}`
   - `POST /api/v1/consultations/onsite`

---

## 🧪 Manual Testing (Reception Desk Workflow)

Simulate a real walk-in scenario:

```bash
# 1. Patient walks in, desk staff searches by phone (not found)
curl -X GET "http://localhost:8000/api/v1/patients/onsite/search?phone=03129876543" \
  -H "Authorization: Bearer {DOCTOR_TOKEN}"
# Response: []

# 2. Desk quick-registers patient
curl -X POST "http://localhost:8000/api/v1/patients/onsite/quick-register" \
  -H "Authorization: Bearer {DOCTOR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ahmed Khan",
    "phone": "03129876543",
    "city": "Karachi"
  }'
# Response: patient_id = "ABC123..."

# 3. Doctor creates consultation
curl -X POST "http://localhost:8000/api/v1/consultations/onsite" \
  -H "Authorization: Bearer {DOCTOR_TOKEN}" \
  -H "X-Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "patient": {
      "full_name": "Ahmed Khan",
      "phone": "03129876543"
    },
    "appointment": {
      "consultation_type": "first",
      "reason": "General checkup"
    },
    "case": {
      "chief_complaint_patient": "General checkup",
      "chief_complaint_duration": "first time"
    }
  }'
# Response: Full consultation with all IDs

# 4. Simulate retry (same idempotency key)
# The exact same request gets same response (no duplicate created)
```

---

## 🔍 Troubleshooting

### "Table sequence_counter does not exist"
```bash
# Solution 1: Run migration
alembic upgrade head

# Solution 2: Run manual setup
python -m scripts.setup_onsite_consultation
```

### "403 Forbidden - Only doctors can perform onsite consultations"
```bash
# Ensure token is from a doctor account
# Check: user.is_doctor = True or user.role = "doctor"
```

### "409 Conflict - Patient with phone already exists"
When calling `/quick-register`:
```bash
# Solution: Use existing patient in /consultations/onsite instead
# First search to find existing patient, then create consultation with their phone
```

### "400 Bad Request - medicine_id not found"
When including existing medicine in prescription:
```bash
# Verify medicine exists in system
# Check medicine was not deleted
# Or use quick-add (new_medicine) instead of medicine_id
```

### Duplicate case numbers appearing
```bash
# Verify sequence_counter table exists
SELECT * FROM sequence_counter;

# If empty/missing:
alembic upgrade head
# Then restart server
```

---

## 📊 Validation Queries

Run these to confirm everything is working:

```sql
-- 1. Tables exist and have correct structure
DESC sequence_counter;
DESC onsite_consultation_audit;

-- 2. Indexes created
SHOW INDEX FROM sequence_counter;
SHOW INDEX FROM onsite_consultation_audit;

-- 3. Sample data from first consultation
SELECT 
    patient_id,
    appointment_id,
    case_id,
    doctor_id,
    created_at,
    is_new_patient
FROM onsite_consultation_audit
LIMIT 1;

-- 4. Counter state
SELECT * FROM sequence_counter;
-- Should show: counter_type='case', prefix='C-MAR26', current_sequence=X
```

---

## 🚀 Rollback Plan (If Needed)

To revert the changes:

```bash
# Option 1: Downgrade migration (if using Alembic)
alembic downgrade -1

# Option 2: Manual rollback
DROP TABLE IF EXISTS onsite_consultation_audit CASCADE;
DROP TABLE IF EXISTS sequence_counter CASCADE;

# Option 3: Restore from backup
# Use your database backup from before deployment
```

**Note**: Old `onsite_consultation.py` is still in the repo as fallback.

---

## ✅ Post-Deployment Verification

After deployment, verify:

- [ ] Can search patients by phone
- [ ] Can quick-register new patient
- [ ] Can create full consultation (patient + appointment + case)
- [ ] Case numbers are sequential (C-MAR26-001, C-MAR26-002)
- [ ] Prescription numbers are sequential (RX-2026-03-001)
- [ ] Audit trail records every consultation
- [ ] Idempotency works (same key returns same response)
- [ ] Doctor can only see their own patients
- [ ] Error messages are clear

---

## 📞 Quick Reference Links

| Resource | Location |
|----------|----------|
| **Full Guide** | `docs/ONSITE_CONSULTATION_GUIDE.md` |
| **Implementation Summary** | `docs/ONSITE_IMPLEMENTATION_SUMMARY.md` |
| **Migration Template** | `docs/ONSITE_MIGRATION_TEMPLATE.py` |
| **Setup Script** | `scripts/setup_onsite_consultation.py` |
| **Route Code** | `routes/onsite_consultation.py` |
| **Patient Routes** | `routes/onsite_patient.py` |
| **Models** | `models/onsite_consultation_model.py` |

---

## 🎯 Success Criteria

System is ready for production when:

✅ All 4 endpoints respond with correct status codes  
✅ Database contains SequenceCounter and OnsiteConsultationAudit tables  
✅ Case/prescription numbers increment correctly  
✅ Audit trail records consultations  
✅ Idempotency prevents duplicates  
✅ Error messages are user-friendly  

---

## Questions?

1. Check **"Troubleshooting"** section above
2. Read **"Workflow Examples"** in `ONSITE_CONSULTATION_GUIDE.md`
3. Review **"Error Handling"** in `ONSITE_CONSULTATION_GUIDE.md`

**Deployment done!** ✅
