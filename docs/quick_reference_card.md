# API Endpoint Quick Reference Card
## Spine Homeo API - Role-Based Access Control

---

## 🎯 Quick Role Identifier

```
┌─────────────────────────────────────────────────────────────┐
│  ENDPOINT PATH PATTERNS → ROLE ACCESS                       │
├─────────────────────────────────────────────────────────────┤
│  /login/*                    → PUBLIC                       │
│  /signup/*                   → PUBLIC                       │
│  /password-recovery*         → PUBLIC                       │
│  /verify-email/*             → PUBLIC                       │
│  /clinic-settings/public     → PUBLIC                       │
│  /medicines/search           → PUBLIC                       │
├─────────────────────────────────────────────────────────────┤
│  /patients/me                → PATIENT                      │
│  /appointments/patient/*     → PATIENT                      │
│  /prescriptions/patient/*    → PATIENT                      │
│  /cases/patient/*            → PATIENT                      │
├─────────────────────────────────────────────────────────────┤
│  /availability/*             → DOCTOR                       │
│  /doctor-preferences/*       → DOCTOR                       │
│  /prescriptions/doctor/*     → DOCTOR                       │
│  /cases/ (POST, PUT)         → DOCTOR                       │
├─────────────────────────────────────────────────────────────┤
│  /patients/* (NOT /me)       → DOCTOR, STAFF               │
│  /appointments/* (NOT /patient/*) → DOCTOR, STAFF          │
│  /medicines/*                → DOCTOR, STAFF               │
│  /follow-ups/*               → DOCTOR, STAFF               │
│  /cases/ (GET)               → DOCTOR, STAFF               │
├─────────────────────────────────────────────────────────────┤
│  /users/me                   → DOCTOR, STAFF, ADMIN        │
│  /session                    → DOCTOR, STAFF, ADMIN        │
│  /reports/*                  → DOCTOR, STAFF, ADMIN        │
│  /utils/*                    → DOCTOR, STAFF, ADMIN        │
├─────────────────────────────────────────────────────────────┤
│  /users/* (NOT /me)          → ADMIN                       │
│  /clinic-settings/ (PUT)     → ADMIN                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Authentication Headers

### For Patient Endpoints
```http
Authorization: Bearer <patient_jwt_token>
```
**Get token from:** `POST /login/patient-simple`

### For Doctor/Staff/Admin Endpoints
```http
Authorization: Bearer <user_jwt_token>
```
**Get token from:** `POST /login/access-token` or `POST /login`

---

## 📊 Endpoint Count by Role

```
PUBLIC              ████████████░░░░░░░░  15 endpoints
PATIENT             ████░░░░░░░░░░░░░░░░   8 endpoints
DOCTOR              █████████░░░░░░░░░░░  18 endpoints
DOCTOR + STAFF      ██████████████████░░  58 endpoints
ALL AUTHENTICATED   ████████████░░░░░░░░  18 endpoints
ADMIN ONLY          █████░░░░░░░░░░░░░░░  11 endpoints
                    ─────────────────────
                    Total: 110 endpoints
```

---

## 🎭 Role Capabilities Matrix

| Capability | PUBLIC | PATIENT | DOCTOR | STAFF | ADMIN |
|------------|:------:|:-------:|:------:|:-----:|:-----:|
| **View own profile** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Update own profile** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Book appointments** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **View all patients** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Update patients** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Write prescriptions** | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Manage inventory** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Schedule management** | ❌ | ❌ | ✅ | ❌ | ❌ |
| **View reports** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Manage users** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **System settings** | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 🚨 Common Permission Errors

### Error: 401 Unauthorized
```json
{ "detail": "Not authenticated" }
```
**Cause:** Missing or invalid token  
**Fix:** Login again and include token in Authorization header

### Error: 403 Forbidden
```json
{ "detail": "Access denied. Required roles: admin" }
```
**Cause:** Insufficient permissions for this endpoint  
**Fix:** Use an account with the required role

### Error: 403 Forbidden (Wrong Entity)
```json
{ "detail": "Access denied. This endpoint requires PatientBearer authentication." }
```
**Cause:** Using doctor token on patient endpoint (or vice versa)  
**Fix:** Use the correct authentication type for the endpoint

---

## 🗂️ Endpoint Categories

### 🔑 Authentication (10 endpoints)
- **Public Access:** Login, registration, password recovery
- **Authenticated:** Session info, token testing

### 👥 User Management (14 endpoints)
- **Own Profile:** 4 endpoints (all roles)
- **User Admin:** 10 endpoints (admin only)

### 🧍 Patient Records (21 endpoints)
- **Patient Self:** 4 endpoints (patient only)
- **Clinical Access:** 17 endpoints (doctor/staff)

### 📅 Appointments (13 endpoints)
- **Public:** 3 endpoints (booking, availability)
- **Patient:** 2 endpoints (view/cancel own)
- **Clinical:** 8 endpoints (management)

### 📝 Prescriptions (6 endpoints)
- **Patient View:** 1 endpoint
- **Doctor Manage:** 5 endpoints

### 📋 Cases (5 endpoints)
- **Patient View:** 1 endpoint
- **Clinical:** 4 endpoints

### 💊 Medicines (10 endpoints)
- **Public:** 1 endpoint (search)
- **Clinical:** 9 endpoints (inventory management)

### 🔔 Follow-ups (8 endpoints)
- **Clinical Only:** All 8 endpoints

### ⏰ Doctor Availability (11 endpoints)
- **Doctor Only:** All 11 endpoints

### ⚙️ Doctor Preferences (5 endpoints)
- **Doctor Only:** All 5 endpoints

### 📊 Reports (6 endpoints)
- **Public:** 1 endpoint
- **Authenticated:** 5 endpoints

### 🌍 Clinic Settings (2 endpoints)
- **Public:** 1 endpoint (read)
- **Admin:** 1 endpoint (write)

### 🛠️ Utilities (4 endpoints)
- **Authenticated:** All 4 endpoints

---

## 🎯 Common Workflows

### Patient Journey
```
1. POST /login/patient-simple          (Login)
2. GET  /patients/me                   (View profile)
3. GET  /appointments/patient/my-appointments
4. GET  /prescriptions/patient/my-prescriptions
5. PATCH /patients/me                  (Update profile)
```

### Doctor Daily Routine
```
1. POST /login/access-token            (Login)
{
  "email": "doctor@homoeomed.com",
  "password": "Doctor@123",
  "remember_me": false
}
2.Set schedule
3.http://localhost:8000/doctor_availability/bulk
{
  "availability_slots": [
    {
      "day_of_week": "monday",
      "start_time": "20:00:00Z",
      "end_time": "22:00:00Z",
      "is_available": true,
      "max_patients_per_slot": 1,
      "notes": "Evening availability"
    },
    {
      "day_of_week": "tuesday",
      "start_time": "20:00:00Z",
      "end_time": "22:00:00Z",
      "is_available": true,
      "max_patients_per_slot": 1,
      "notes": "Evening availability"
    },
    {
      "day_of_week": "wednesday",
      "start_time": "20:00:00Z",
      "end_time": "22:00:00Z",
      "is_available": true,
      "max_patients_per_slot": 1,
      "notes": "Evening availability"
    },
    {
      "day_of_week": "thursday",
      "start_time": "20:00:00Z",
      "end_time": "22:00:00Z",
      "is_available": true,
      "max_patients_per_slot": 1,
      "notes": "Evening availability"
    },
    {
      "day_of_week": "friday",
      "start_time": "20:00:00Z",
      "end_time": "22:00:00Z",
      "is_available": true,
      "max_patients_per_slot": 1,
      "notes": "Evening availability"
    },
    {
      "day_of_week": "saturday",
      "start_time": "20:00:00Z",
      "end_time": "22:00:00Z",
      "is_available": true,
      "max_patients_per_slot": 1,
      "notes": "Evening availability"
    },
    {
      "day_of_week": "sunday",
      "start_time": "20:00:00Z",
      "end_time": "22:00:00Z",
      "is_available": true,
      "max_patients_per_slot": 1,
      "notes": "Evening availability"
    }
  ]
}
2. GET  /availability/my-schedule      (Check schedule)

3. GET  /appointments/today            (Today's patients)

4. GET  /patients/{id}                 (Patient details)
5. POST /prescriptions/doctor/         (Write prescription)
6. POST /follow-ups/                   (Schedule follow-up)
```

### Front Desk Operations
```
1. POST /login/access-token            (Login)
2. GET  /patients/search?q=name        (Find patient)
3. POST /patients/                     (New patient registration)
4. GET  /appointments/available-slots/{doctor_id}
5. POST /appointments/book             (Book appointment)
6. POST /follow-ups/                   (Schedule follow-up)
```

### Admin Tasks
```
1. POST /login/access-token            (Login)
2. GET  /users/pending-verification    (Check new users)
3. PATCH /users/{id}/verify            (Verify doctor)
4. PUT  /users/{id}/role               (Assign role)
5. GET  /reports/custom                (Generate report)
6. PUT  /clinic-settings/              (Update settings)
```

---

## 💡 Quick Tips

### ✅ Do's
- Always include Authorization header for protected endpoints
- Use correct authentication type (Patient vs Doctor)
- Check role requirements before calling endpoints
- Handle 401/403 errors gracefully
- Test with different role accounts
- Validate tokens before making requests

### ❌ Don'ts
- Don't use patient token on doctor endpoints
- Don't use doctor token on patient endpoints
- Don't expose tokens in URLs or logs
- Don't store tokens in localStorage without encryption
- Don't ignore expiration (tokens expire in 1 hour)
- Don't hardcode role checks only in frontend

---

## 🔍 How to Find the Right Endpoint

### I want to...

**...as a Patient:**
- View my profile → `GET /patients/me`
- Update my info → `PATCH /patients/me`
- See my appointments → `GET /appointments/patient/my-appointments`
- Cancel appointment → `DELETE /appointments/patient/{id}`
- View prescriptions → `GET /prescriptions/patient/my-prescriptions`
- See my cases → `GET /cases/patient/my-cases`

**...as a Doctor:**
- Manage my schedule → `POST/GET/PUT/DELETE /availability/*`
- View today's patients → `GET /appointments/today`
- Write prescription → `POST /prescriptions/doctor/`
- Create case → `POST /cases/`
- Set preferences → `PUT /doctor-preferences/`
- View patient history → `GET /patients/{id}/history`

**...as Staff:**
- Find a patient → `GET /patients/search?q=name`
- Register patient → `POST /patients/`
- Book appointment → `POST /appointments/book`
- Check availability → `GET /appointments/available-slots/{doctor_id}`
- Add medicine → `POST /medicines/`
- Schedule follow-up → `POST /follow-ups/`

**...as Admin:**
- List all users → `GET /users/`
- Create user → `POST /users/`
- Verify doctor → `PATCH /users/{id}/verify`
- Change role → `PUT /users/{id}/role`
- Update settings → `PUT /clinic-settings/`
- Generate reports → `GET /reports/custom`

---

## 🎓 Role Hierarchy

```
        ┌──────────┐
        │  ADMIN   │  ← Full system access
        └────┬─────┘
             │
     ┌───────┴────────┐
     │                │
┌────▼────┐      ┌───▼────┐
│ DOCTOR  │      │ STAFF  │  ← Clinical operations
└────┬────┘      └────────┘
     │
     │  ← Can do everything staff can do
     │     PLUS prescriptions & schedule
     │
```

**Patient** - Separate domain, own data only

---

## 📱 Mobile/Web Integration

### Environment Setup
```javascript
// config.js
export const API_CONFIG = {
  baseURL: 'https://api.spinehomeo.com',
  patientLoginEndpoint: '/login/patient-simple',
  doctorLoginEndpoint: '/login/access-token',
  tokenExpiry: 3600, // 1 hour in seconds
};
```

### Auth Helper
```javascript
// auth.js
export const getAuthHeader = (userType) => {
  const token = userType === 'patient' 
    ? localStorage.getItem('patientToken')
    : localStorage.getItem('doctorToken');
  
  return { 'Authorization': `Bearer ${token}` };
};

export const isAuthorized = (endpoint, userRole) => {
  const roleMap = {
    '/patients/me': ['PATIENT'],
    '/users/': ['ADMIN'],
    '/prescriptions/doctor/': ['DOCTOR'],
    '/appointments/': ['DOCTOR', 'STAFF', 'ADMIN'],
    // ... add more as needed
  };
  
  for (const [path, roles] of Object.entries(roleMap)) {
    if (endpoint.startsWith(path)) {
      return roles.includes(userRole);
    }
  }
  return false;
};
```

---

## 📞 Support & Contact

For questions about endpoint access or permissions:
- Check this reference card first
- Review the full documentation: `endpoint_role_mapping.md`
- Check JSON mapping: `endpoint_role_mapping.json`
- Test in Swagger UI: Include appropriate authentication

---

**Quick Reference Version:** 1.0  
**Last Updated:** January 31, 2026  
**API Version:** 1.0.0
