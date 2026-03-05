# Documentation Index - Onsite Consultation System

**Last Updated**: March 5, 2026

---

## 📚 Read These First

### For Quick Understanding (5 min read)
1. **[ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md)** ⭐ START HERE
   - 3 patient management endpoints
   - Quick briefs with examples
   - Complete workflow example
   - Common errors & solutions

2. **[ONSITE_QUICK_START.md](./ONSITE_QUICK_START.md)**
   - 5-minute deployment checklist
   - Copy/paste test commands
   - Troubleshooting guide

---

## 📖 Complete References

### Main Documentation
1. **[ONSITE_CONSULTATION_GUIDE.md](./ONSITE_CONSULTATION_GUIDE.md)**
   - Complete API reference
   - Architecture diagrams
   - Key features explained (thread-safety, atomicity, idempotency, etc.)
   - Database models
   - Workflow examples (3 realistic scenarios)
   - Performance considerations
   - Security notes

2. **[ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md)**
   - Detailed endpoint briefs
   - Request/response examples for each endpoint
   - Field descriptions
   - Authentication & errors
   - Test commands (curl)

---

## 🔍 Looking for Something Specific?

| What I Need | Document | Notes |
|-------------|----------|-------|
| **How to setup the system** | ONSITE_QUICK_START.md | Deployment steps + verification |
| **Patient search endpoint** | ONSITE_PATIENT_ENDPOINTS.md | Section 1️⃣ |
| **Patient registration endpoint** | ONSITE_PATIENT_ENDPOINTS.md | Section 2️⃣ |
| **Get patient details endpoint** | ONSITE_PATIENT_ENDPOINTS.md | Section 3️⃣ |
| **Create consultation endpoint** | ONSITE_CONSULTATION_GUIDE.md | Main Consultation Endpoint |
| **Complete walk-in workflow** | ONSITE_PATIENT_ENDPOINTS.md | Complete Workflow Example |
| **Error codes & solutions** | ONSITE_PATIENT_ENDPOINTS.md | Common Errors & Solutions |
| **Before/after comparison** | ONSITE_BEFORE_AFTER.md | Technical improvements made |
| **Implementation summary** | ONSITE_IMPLEMENTATION_SUMMARY.md | What was built & why |
| **Migration template** | ONSITE_MIGRATION_TEMPLATE.py | Database migration code |
| **Setup script** | scripts/setup_onsite_consultation.py | Manual DB initialization |

---

## 🎯 By Role

### 👨‍💼 Project Manager / Business Owner
→ Start with: [ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md)
- Understand the 3 patient endpoints
- See workflow example
- Check successful response examples

### 👨‍💻 Backend Developer
→ Start with: [ONSITE_IMPLEMENTATION_SUMMARY.md](./ONSITE_IMPLEMENTATION_SUMMARY.md)
- Understand code improvements made
- Review before/after comparisons
- Check database changes: [ONSITE_MIGRATION_TEMPLATE.py](./ONSITE_MIGRATION_TEMPLATE.py)

### 👩‍🔧 DevOps / Infrastructure
→ Start with: [ONSITE_QUICK_START.md](./ONSITE_QUICK_START.md)
- Follow deployment steps
- Run setup script or migration
- Test endpoints with provided curl commands

### 👨‍⚕️ Doctor / Clinical Staff
→ Start with: [ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md)
- See complete workflow example
- Understand each endpoint's purpose
- Review error scenarios

### 📞 Receptionist / Desk Staff
→ Share: [ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md) Sections 1 & 2
- Patient search workflow
- Quick-register workflow
- Common errors

---

## 📊 API Endpoints Summary

### Patient Management (3 endpoints)
| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/patients/onsite/search` | GET | Find existing patients | ✅ Active |
| `/patients/onsite/quick-register` | POST | Register new walk-in | ✅ Active |
| `/patients/onsite/{patient_id}` | GET | Get patient details | ✅ Active |

### Consultation (1 endpoint)
| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/consultations/onsite` | POST | Create full consultation | ✅ Active |

---

## 🚀 Quick Start (TL;DR)

### Step 1: Deploy
```bash
# Apply database migration
alembic upgrade head
```

### Step 2: Verify
```bash
# Test patient search (should return empty)
curl -X GET "http://localhost:8000/api/v1/patients/onsite/search?phone=03001234567" \
  -H "Authorization: Bearer {token}"
```

### Step 3: Read Docs
- [ ] ONSITE_PATIENT_ENDPOINTS.md (10 min read)
- [ ] ONSITE_QUICK_START.md (5 min read)

---

## 📂 File Structure

```
docs/
├── ONSITE_PATIENT_ENDPOINTS.md           ← PATIENT MGMT ENDPOINTS
├── ONSITE_CONSULTATION_GUIDE.md          ← MAIN CONSULTATION ENDPOINT
├── ONSITE_QUICK_START.md                 ← DEPLOYMENT CHECKLIST
├── ONSITE_IMPLEMENTATION_SUMMARY.md      ← WHAT WAS BUILT
├── ONSITE_BEFORE_AFTER.md               ← CODE IMPROVEMENTS
├── ONSITE_MIGRATION_TEMPLATE.py          ← DB MIGRATION
└── DOCUMENTATION_INDEX.md                ← YOU ARE HERE

models/
└── onsite_consultation_model.py          ← DB MODELS

routes/
├── onsite_patient.py                     ← PATIENT ENDPOINTS
└── onsite_consultation.py                ← CONSULTATION ENDPOINT

scripts/
└── setup_onsite_consultation.py          ← MANUAL DB SETUP
```

---

## 🔐 Authentication

All endpoints require:
```
Authorization: Bearer {jwt_token}
```

Get token by:
1. Login endpoint (email + password)
2. Token has user info including `is_doctor` flag
3. Pass in Authorization header above

---

## ❓ FAQ

**Q: Where is the endpoint documentation?**
A: In [ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md) (patient endpoints) and [ONSITE_CONSULTATION_GUIDE.md](./ONSITE_CONSULTATION_GUIDE.md) (consultation endpoint)

**Q: How do I deploy this?**
A: See [ONSITE_QUICK_START.md](./ONSITE_QUICK_START.md) - 5 minute checklist

**Q: What changed from the original code?**
A: See [ONSITE_BEFORE_AFTER.md](./ONSITE_BEFORE_AFTER.md) - detailed comparisons

**Q: How do I test the endpoints?**
A: [ONSITE_QUICK_START.md](./ONSITE_QUICK_START.md) has curl commands for each endpoint

**Q: What database tables were added?**
A: See [ONSITE_MIGRATION_TEMPLATE.py](./ONSITE_MIGRATION_TEMPLATE.py) or [ONSITE_IMPLEMENTATION_SUMMARY.md](./ONSITE_IMPLEMENTATION_SUMMARY.md)

**Q: Can I run this without Alembic migrations?**
A: Yes, use `scripts/setup_onsite_consultation.py` for manual setup

**Q: What's the complete workflow?**
A: See "Complete Workflow Example" in [ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md)

---

## 🆘 Need Help?

1. **Endpoint questions** → [ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md)
2. **Deployment issues** → [ONSITE_QUICK_START.md](./ONSITE_QUICK_START.md) Troubleshooting
3. **Code changes** → [ONSITE_BEFORE_AFTER.md](./ONSITE_BEFORE_AFTER.md)
4. **Database setup** → [ONSITE_MIGRATION_TEMPLATE.py](./ONSITE_MIGRATION_TEMPLATE.py)
5. **Complete reference** → [ONSITE_CONSULTATION_GUIDE.md](./ONSITE_CONSULTATION_GUIDE.md)

---

## ✅ Recommended Reading Order

### For First-Time Readers
1. This page (2 min)
2. [ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md) (10 min)
3. [ONSITE_QUICK_START.md](./ONSITE_QUICK_START.md) (5 min)

### For Implementation
1. [ONSITE_QUICK_START.md](./ONSITE_QUICK_START.md)
2. [ONSITE_MIGRATION_TEMPLATE.py](./ONSITE_MIGRATION_TEMPLATE.py)
3. Test endpoints with curl commands

### For Understanding Changes
1. [ONSITE_BEFORE_AFTER.md](./ONSITE_BEFORE_AFTER.md)
2. [ONSITE_IMPLEMENTATION_SUMMARY.md](./ONSITE_IMPLEMENTATION_SUMMARY.md)

### For Deep Dive
1. [ONSITE_CONSULTATION_GUIDE.md](./ONSITE_CONSULTATION_GUIDE.md)
2. [models/onsite_consultation_model.py](../models/onsite_consultation_model.py)
3. [routes/onsite_patient.py](../routes/onsite_patient.py)
4. [routes/onsite_consultation.py](../routes/onsite_consultation.py)

---

## 📞 Support

For issues or questions:
- Check **Troubleshooting** in [ONSITE_QUICK_START.md](./ONSITE_QUICK_START.md)
- Review **Common Errors & Solutions** in [ONSITE_PATIENT_ENDPOINTS.md](./ONSITE_PATIENT_ENDPOINTS.md)
- Check application logs for detailed error messages

---

**Last Updated**: March 5, 2026
**Version**: 1.0
**Status**: ✅ Production Ready
